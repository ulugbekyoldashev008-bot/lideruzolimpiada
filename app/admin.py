from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy import delete, func, select

from .db import AdminLog, Answer, Attempt, Level, OlympiadConfig, Participant, Question, Subject
from .exporter import create_excel
from .keyboards import admin_menu, home, inline_items
from .states import AddLevel, AddQuestion, AddSubject, Review, Schedule
from .utils import fmt_dt

router = Router(name="admin")


def allowed(user_id, settings):
    return user_id in settings.admin_ids


async def deny(message_or_call, settings):
    user_id = message_or_call.from_user.id
    if allowed(user_id, settings): return False
    if isinstance(message_or_call, CallbackQuery): await message_or_call.answer("Siz admin emassiz", show_alert=True)
    else: await message_or_call.answer("⛔ Bu bo‘limga faqat admin kira oladi.")
    return True


async def log(session, admin_id, action):
    session.add(AdminLog(admin_id=admin_id, action=action))


def utc_value(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def attempt_minutes(attempt):
    if not attempt or not attempt.started_at or not attempt.submitted_at:
        return 0
    started = utc_value(attempt.started_at)
    submitted = utc_value(attempt.submitted_at)
    return max(0, int((submitted - started).total_seconds() // 60))


async def reset_exam_progress(session):
    await session.execute(delete(Answer))
    await session.execute(delete(Attempt))


async def clear_reminders(session):
    from .db import Reminder
    await session.execute(delete(Reminder))


async def auto_finish_attempt(session, attempt):
    participant = await session.get(Participant, attempt.participant_id)
    questions = (await session.execute(
        select(Question).where(
            Question.subject_id == participant.subject_id,
            Question.level_id == participant.level_id,
            Question.active.is_(True),
        )
    )).scalars().all()
    answers = (await session.execute(select(Answer).where(Answer.attempt_id == attempt.id))).scalars().all()
    attempt.submitted_at = datetime.now(timezone.utc)
    attempt.total_score = float(sum(answer.score or 0 for answer in answers))
    attempt.admin_comment = "Admin testni to‘xtatdi."
    attempt.status = "reviewed"
    maximum = float(sum(question.max_score for question in questions))
    correct = sum(1 for answer in answers if answer.score is not None and answer.score > 0)
    percent = (attempt.total_score or 0) / maximum * 100 if maximum else 0
    return participant, correct, len(questions), maximum, percent


@router.message(F.text == "🔐 Admin")
async def admin_open(message: Message, state: FSMContext, settings):
    if await deny(message, settings): return
    await state.clear(); await message.answer("Admin panel ochildi.", reply_markup=admin_menu())


@router.message(F.text == "➕ Fan")
async def add_subject_start(message: Message, state: FSMContext, settings):
    if await deny(message, settings): return
    await state.set_state(AddSubject.name); await message.answer("Yangi fan nomini yozing:")


@router.message(AddSubject.name)
async def add_subject_save(message: Message, state: FSMContext, sessions, settings):
    if await deny(message, settings): return
    name = (message.text or "").strip()
    if len(name) < 2: await message.answer("Fan nomini to‘liq yozing."); return
    async with sessions() as session:
        if await session.scalar(select(Subject).where(func.lower(Subject.name) == name.lower())):
            await message.answer("Bu fan avval qo‘shilgan."); return
        session.add(Subject(name=name)); await log(session, message.from_user.id, f"Fan qo‘shildi: {name}"); await session.commit()
    await state.clear(); await message.answer(f"✅ {name} fani qo‘shildi.", reply_markup=admin_menu())


@router.message(F.text == "➕ Daraja")
async def add_level_start(message: Message, state: FSMContext, sessions, settings):
    if await deny(message, settings): return
    async with sessions() as session: subjects = (await session.execute(select(Subject).where(Subject.active.is_(True)).order_by(Subject.name))).scalars().all()
    if not subjects: await message.answer("Avval fan qo‘shing."); return
    await state.set_state(AddLevel.subject); await message.answer("Fanni tanlang:", reply_markup=inline_items([(x.id, x.name) for x in subjects], "addlevelsubject", 2))


@router.callback_query(AddLevel.subject, F.data.startswith("addlevelsubject:"))
async def add_level_subject(call: CallbackQuery, state: FSMContext, settings):
    if await deny(call, settings): return
    await state.update_data(subject_id=int(call.data.split(":")[1])); await state.set_state(AddLevel.name)
    await call.message.edit_text("Daraja nomini yozing (masalan: Beginner yoki 5-sinf):"); await call.answer()


@router.message(AddLevel.name)
async def add_level_save(message: Message, state: FSMContext, sessions, settings):
    if await deny(message, settings): return
    data = await state.get_data(); name = (message.text or "").strip()
    async with sessions() as session:
        exists = await session.scalar(select(Level).where(Level.subject_id == data["subject_id"], func.lower(Level.name) == name.lower()))
        if exists: await message.answer("Bu daraja avval qo‘shilgan."); return
        session.add(Level(subject_id=data["subject_id"], name=name)); await log(session, message.from_user.id, f"Daraja qo‘shildi: {name}"); await session.commit()
    await state.clear(); await message.answer("✅ Daraja qo‘shildi.", reply_markup=admin_menu())


@router.message(F.text == "❓ Savol qo‘shish")
async def question_start(message: Message, state: FSMContext, sessions, settings):
    if await deny(message, settings): return
    async with sessions() as session: subjects = (await session.execute(select(Subject).where(Subject.active.is_(True)).order_by(Subject.name))).scalars().all()
    if not subjects: await message.answer("Avval fan va darajalarni qo‘shing."); return
    await state.set_state(AddQuestion.subject); await message.answer("Savol qaysi fan uchun?", reply_markup=inline_items([(x.id, x.name) for x in subjects], "qsubject", 2))


@router.callback_query(AddQuestion.subject, F.data.startswith("qsubject:"))
async def question_subject(call: CallbackQuery, state: FSMContext, sessions, settings):
    if await deny(call, settings): return
    sid = int(call.data.split(":")[1])
    async with sessions() as session: levels = (await session.execute(select(Level).where(Level.subject_id == sid, Level.active.is_(True)).order_by(Level.name))).scalars().all()
    if not levels: await call.answer("Bu fanda daraja yo‘q", show_alert=True); return
    await state.update_data(subject_id=sid); await state.set_state(AddQuestion.level)
    await call.message.edit_text("Darajani tanlang:", reply_markup=inline_items([(x.id, x.name) for x in levels], "qlevel", 2)); await call.answer()


@router.callback_query(AddQuestion.level, F.data.startswith("qlevel:"))
async def question_level(call: CallbackQuery, state: FSMContext, settings):
    if await deny(call, settings): return
    await state.update_data(level_id=int(call.data.split(":")[1])); await state.set_state(AddQuestion.text)
    await call.message.edit_text("Savol matnini yuboring:"); await call.answer()


@router.message(AddQuestion.text)
async def question_text(message: Message, state: FSMContext, settings):
    if await deny(message, settings): return
    if not message.text: await message.answer("Savolni matn ko‘rinishida yuboring."); return
    await state.update_data(text=message.text.strip()); await state.set_state(AddQuestion.answer_type)
    await message.answer("Javob turini tanlang:", reply_markup=inline_items([("choice", "A/B/C/D tugma"), ("text", "Matn"), ("photo", "Rasm")], "qtype", 1))


@router.callback_query(AddQuestion.answer_type, F.data.startswith("qtype:"))
async def question_type(call: CallbackQuery, state: FSMContext, sessions, settings):
    if await deny(call, settings): return
    kind = call.data.split(":")[1]; await state.update_data(answer_type=kind)
    if kind == "choice":
        await state.set_state(AddQuestion.options); await call.message.edit_text("Variantlarni | belgisi bilan yozing:\nMasalan: Toshkent|Samarqand|Buxoro|Xiva")
    elif kind == "text":
        data = await state.get_data()
        async with sessions() as session:
            subject = await session.get(Subject, data["subject_id"])
        if subject and subject.name.casefold() == "mental arifmetika":
            await state.set_state(AddQuestion.correct_text)
            await call.message.edit_text("Mental misolining to‘g‘ri javobini faqat son bilan yozing. Masalan: 125 yoki -4,5")
        else:
            await state.set_state(AddQuestion.max_score); await call.message.edit_text("Bu savol uchun maksimal ballni yozing. Masalan: 5")
    else:
        await state.set_state(AddQuestion.max_score); await call.message.edit_text("Bu savol uchun maksimal ballni yozing. Masalan: 5")
    await call.answer()


@router.message(AddQuestion.options)
async def question_options(message: Message, state: FSMContext):
    options = [x.strip() for x in (message.text or "").split("|") if x.strip()]
    if not 2 <= len(options) <= 6: await message.answer("2 tadan 6 tagacha variant kiriting va | bilan ajrating."); return
    await state.update_data(options="|".join(options)); await state.set_state(AddQuestion.correct_option)
    await message.answer("To‘g‘ri javobni tanlang:", reply_markup=inline_items([(i, f"{chr(65+i)}) {option}") for i, option in enumerate(options)], "qcorrect", 1))


@router.callback_query(AddQuestion.correct_option, F.data.startswith("qcorrect:"))
async def question_correct_option(call: CallbackQuery, state: FSMContext, settings):
    if await deny(call, settings): return
    await state.update_data(correct_option=int(call.data.split(":")[1]))
    await state.set_state(AddQuestion.max_score)
    await call.message.edit_text("Maksimal ballni yozing. Masalan: 1")
    await call.answer()


@router.message(AddQuestion.correct_text)
async def question_correct_text(message: Message, state: FSMContext, settings):
    if await deny(message, settings): return
    raw = (message.text or "").strip().replace(" ", "").replace(",", ".")
    try:
        value = Decimal(raw)
        if not value.is_finite(): raise InvalidOperation
    except InvalidOperation:
        await message.answer("To‘g‘ri javobni faqat son bilan yozing. Masalan: 125 yoki -4,5"); return
    normalized = format(value.normalize(), "f")
    await state.update_data(correct_text=normalized)
    await state.set_state(AddQuestion.max_score)
    await message.answer("Maksimal ballni yozing. Mental uchun odatda: 1")


@router.message(AddQuestion.max_score)
async def question_score(message: Message, state: FSMContext, sessions, settings):
    if await deny(message, settings): return
    try:
        score = float((message.text or "").replace(",", ".")); assert 0 < score <= 1000
    except (ValueError, AssertionError): await message.answer("Ballni musbat raqamda yozing."); return
    data = await state.get_data()
    async with sessions() as session:
        pos = (await session.scalar(select(func.max(Question.position)).where(Question.subject_id == data["subject_id"], Question.level_id == data["level_id"]))) or 0
        session.add(Question(subject_id=data["subject_id"], level_id=data["level_id"], text=data["text"], answer_type=data["answer_type"], options=data.get("options"), correct_option=data.get("correct_option"), correct_text=data.get("correct_text"), max_score=score, position=pos + 1))
        await log(session, message.from_user.id, f"Savol qo‘shildi, fan={data['subject_id']}, daraja={data['level_id']}"); await session.commit()
    await state.clear(); await message.answer("✅ Savol qo‘shildi.", reply_markup=admin_menu())


@router.message(F.text == "🗓 Vaqt belgilash")
async def schedule_start(message: Message, state: FSMContext, settings):
    if await deny(message, settings): return
    await state.set_state(Schedule.start_at); await message.answer("Boshlanish vaqtini Toshkent vaqti bilan yozing:\n<b>kun.oy.yil soat:daqiqa</b>\nMasalan: 05.10.2026 10:00", parse_mode=ParseMode.HTML)


@router.message(Schedule.start_at)
async def schedule_date(message: Message, state: FSMContext, settings):
    if await deny(message, settings): return
    try:
        local = datetime.strptime((message.text or "").strip(), "%d.%m.%Y %H:%M").replace(tzinfo=ZoneInfo(settings.timezone))
        if local <= datetime.now(ZoneInfo(settings.timezone)): raise ValueError
    except ValueError: await message.answer("Kelajakdagi vaqtni shu formatda yozing: 05.10.2026 10:00"); return
    await state.update_data(start_at=local.astimezone(timezone.utc).isoformat()); await state.set_state(Schedule.duration); await message.answer("Olimpiada necha daqiqa davom etadi? Masalan: 60")


@router.message(Schedule.duration)
async def schedule_duration(message: Message, state: FSMContext, sessions, settings):
    if await deny(message, settings): return
    try:
        minutes = int(message.text); assert 5 <= minutes <= 1440
    except (ValueError, TypeError, AssertionError): await message.answer("5 dan 1440 gacha daqiqa yozing."); return
    data = await state.get_data()
    async with sessions() as session:
        cfg = await session.get(OlympiadConfig, 1)
        await reset_exam_progress(session)
        await clear_reminders(session)
        cfg.start_at = datetime.fromisoformat(data["start_at"])
        cfg.duration_minutes = minutes
        cfg.test_stopped = False
        cfg.results_published = False
        await log(session, message.from_user.id, f"Olimpiada vaqti: {data['start_at']}, {minutes} daqiqa")
        await session.commit()
    await state.clear(); await message.answer(f"✅ Vaqt belgilandi: {fmt_dt(cfg.start_at, settings.timezone)}, {minutes} daqiqa.", reply_markup=admin_menu())


@router.message(F.text == "🧹 Vaqtni bekor qilish")
async def clear_schedule(message: Message, sessions, settings):
    if await deny(message, settings): return
    async with sessions() as session:
        cfg = await session.get(OlympiadConfig, 1)
        await reset_exam_progress(session)
        await clear_reminders(session)
        cfg.start_at = None
        cfg.test_stopped = True
        cfg.results_published = False
        await log(session, message.from_user.id, "Olimpiada vaqti bekor qilindi va urinishlar tozalandi")
        await session.commit()
    await message.answer("✅ Vaqt bekor qilindi. Endi vaqt qayta belgilanmaguncha hech kim test yecha olmaydi.", reply_markup=admin_menu())


@router.message(F.text == "⛔ Testni to‘xtatish")
async def stop_exam(message: Message, sessions, settings):
    if await deny(message, settings): return
    async with sessions() as session:
        cfg = await session.get(OlympiadConfig, 1)
        cfg.test_stopped = True
        working = (await session.execute(
            select(Attempt).where(Attempt.status == "working", Attempt.submitted_at.is_(None))
        )).scalars().all()
        results = []
        for attempt in working:
            results.append(await auto_finish_attempt(session, attempt))
        await log(session, message.from_user.id, f"Test to‘xtatildi. Yakunlangan urinishlar: {len(results)}")
        await session.commit()
    for participant, correct, total_questions, maximum, percent in results:
        try:
            await message.bot.send_message(
                participant.telegram_id,
                f"⛔ Test admin tomonidan to‘xtatildi.\n"
                f"✅ To‘g‘ri: {correct}/{total_questions}\n"
                f"📈 Siz {percent:.1f}% topdingiz.",
            )
        except Exception:
            pass
    await message.answer(f"⛔ Test to‘xtatildi. {len(results)} ta ishlayotgan o‘quvchi yakunlandi.", reply_markup=admin_menu())


@router.message(F.text == "🔓 Ro‘yxatni yoqish/o‘chirish")
async def toggle_registration(message: Message, sessions, settings):
    if await deny(message, settings): return
    async with sessions() as session:
        cfg = await session.get(OlympiadConfig, 1); cfg.registration_open = not cfg.registration_open
        await log(session, message.from_user.id, f"Ro‘yxat holati: {cfg.registration_open}"); await session.commit(); status = cfg.registration_open
    await message.answer("✅ Ro‘yxatdan o‘tish YOQILDI." if status else "🔒 Ro‘yxatdan o‘tish O‘CHIRILDI.")


@router.message(F.text == "📣 Natijani e’lon qilish")
async def toggle_results(message: Message, sessions, settings):
    if await deny(message, settings): return
    async with sessions() as session:
        cfg = await session.get(OlympiadConfig, 1); cfg.results_published = not cfg.results_published
        await log(session, message.from_user.id, f"Natija e'loni: {cfg.results_published}"); await session.commit(); status = cfg.results_published
        reviewed = (await session.execute(select(Attempt, Participant).join(Participant, Attempt.participant_id == Participant.id).where(Attempt.status == "reviewed"))).all() if status else []
    await message.answer("📣 Natijalar o‘quvchilarga e’lon qilindi." if status else "🔕 Natijalar yana yashirildi.")
    if status:
        for attempt, participant in reviewed:
            try: await message.bot.send_message(participant.telegram_id, f"🎉 Olimpiada natijalari e’lon qilindi!\nSizning natijangiz: {attempt.total_score:g} ball.\nBatafsil ma’lumot uchun 📊 Natijam tugmasini bosing.")
            except Exception: pass


@router.message(F.text == "👥 Qatnashchilar")
async def participants(message: Message, sessions, settings):
    if await deny(message, settings): return
    async with sessions() as session:
        total = await session.scalar(select(func.count()).select_from(Participant))
        latest = (await session.execute(select(Participant).order_by(Participant.id.desc()).limit(20))).scalars().all()
    text = f"👥 Jami qatnashchilar: <b>{total}</b>\n\n" + ("\n".join(f"{p.participant_code} — {escape(p.full_name)} — {'🚫' if p.blocked else '✅'}" for p in latest) or "Hali qatnashchi yo‘q.")
    buttons = [(p.id, ("Ochish: " if p.blocked else "Bloklash: ") + p.full_name[:20]) for p in latest]
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=inline_items(buttons, "block", 1) if buttons else None)


@router.callback_query(F.data.startswith("block:"))
async def block_participant(call: CallbackQuery, sessions, settings):
    if await deny(call, settings): return
    pid = int(call.data.split(":")[1])
    async with sessions() as session:
        p = await session.get(Participant, pid)
        if not p: await call.answer("Topilmadi", show_alert=True); return
        p.blocked = not p.blocked; await log(session, call.from_user.id, f"Qatnashchi blok holati {p.id}: {p.blocked}"); await session.commit()
    await call.answer("Holat o‘zgartirildi", show_alert=True); await call.message.edit_reply_markup(reply_markup=None)


@router.message(F.text == "📥 Excel yuklash")
async def export_excel(message: Message, sessions, settings):
    if await deny(message, settings): return
    async with sessions() as session: path = await create_excel(session)
    try: await message.answer_document(FSInputFile(path, filename="olimpiada_hisoboti.xlsx"), caption="Qatnashchilar, javoblar va natijalar hisoboti")
    finally: Path(path).unlink(missing_ok=True)


@router.message(F.text == "📝 Javoblarni tekshirish")
async def review_list(message: Message, state: FSMContext, sessions, settings):
    if await deny(message, settings): return
    async with sessions() as session:
        rows = (await session.execute(select(Attempt, Participant).join(Participant, Attempt.participant_id == Participant.id).where(Attempt.status == "submitted").order_by(Attempt.submitted_at).limit(50))).all()
    if not rows: await message.answer("Tekshirilmagan javoblar yo‘q."); return
    await state.set_state(Review.selecting); await message.answer("Tekshirish uchun o‘quvchini tanlang:", reply_markup=inline_items([(a.id, p.full_name) for a, p in rows], "review", 1))


async def show_review_item(message: Message, state: FSMContext, sessions):
    data = await state.get_data(); answer_ids = data["answer_ids"]; idx = data["review_index"]
    if idx >= len(answer_ids):
        await state.set_state(Review.comment); await message.answer("Barcha javoblarga ball berildi. Umumiy admin izohini yozing yoki - yuboring:"); return
    async with sessions() as session:
        answer = await session.get(Answer, answer_ids[idx]); q = await session.get(Question, answer.question_id)
    text = f"📝 <b>{idx+1}/{len(answer_ids)}-javob</b>\n\n<b>Savol:</b> {escape(q.text)}\n<b>Javob:</b> {escape(answer.text_answer or '[rasm]')}\n<b>Maksimal ball:</b> {q.max_score:g}\n\nQo‘yiladigan ballni yozing:"
    if answer.file_id: await message.answer_photo(answer.file_id, caption=text, parse_mode=ParseMode.HTML)
    else: await message.answer(text, parse_mode=ParseMode.HTML)


@router.callback_query(Review.selecting, F.data.startswith("review:"))
async def review_select(call: CallbackQuery, state: FSMContext, sessions, settings):
    if await deny(call, settings): return
    attempt_id = int(call.data.split(":")[1])
    async with sessions() as session:
        attempt = await session.get(Attempt, attempt_id)
        ids = list((await session.execute(select(Answer.id).where(Answer.attempt_id == attempt_id, Answer.score.is_(None)).order_by(Answer.id))).scalars().all())
    if not attempt or not ids: await call.answer("Javoblar topilmadi", show_alert=True); return
    await state.update_data(attempt_id=attempt_id, answer_ids=ids, review_index=0); await state.set_state(Review.scoring)
    await call.message.edit_reply_markup(reply_markup=None); await call.answer(); await show_review_item(call.message, state, sessions)


@router.message(Review.scoring)
async def review_score(message: Message, state: FSMContext, sessions, settings):
    if await deny(message, settings): return
    data = await state.get_data(); answer_id = data["answer_ids"][data["review_index"]]
    async with sessions() as session:
        answer = await session.get(Answer, answer_id); q = await session.get(Question, answer.question_id)
        try:
            score = float((message.text or "").replace(",", ".")); assert 0 <= score <= q.max_score
        except (ValueError, AssertionError): await message.answer(f"0 dan {q.max_score:g} gacha ball kiriting."); return
        answer.score = score; await session.commit()
    await state.update_data(review_index=data["review_index"] + 1); await show_review_item(message, state, sessions)


@router.message(Review.comment)
async def review_finish(message: Message, state: FSMContext, sessions, settings):
    if await deny(message, settings): return
    data = await state.get_data()
    async with sessions() as session:
        attempt = await session.get(Attempt, data["attempt_id"])
        total = await session.scalar(select(func.coalesce(func.sum(Answer.score), 0)).where(Answer.attempt_id == attempt.id))
        attempt.total_score = float(total); attempt.admin_comment = None if message.text == "-" else message.text; attempt.status = "reviewed"
        await log(session, message.from_user.id, f"Natija tekshirildi attempt={attempt.id}, ball={total}"); await session.commit()
        participant = await session.get(Participant, attempt.participant_id)
    await state.clear(); await message.answer(f"✅ {participant.full_name} tekshirildi. Jami: {float(total):g} ball", reply_markup=admin_menu())
