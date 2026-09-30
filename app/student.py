from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from html import escape

from aiogram import BaseMiddleware, Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardMarkup
from sqlalchemy import select

from .db import Answer, Attempt, Level, OlympiadConfig, Participant, Question, SocialVerification, Subject
from .keyboards import cabinet, confirm_kb, home, inline_items, subscription_kb
from .regions import REGIONS
from .states import Exam, Registration
from .utils import age_from_birth, as_aware, credentials, fmt_dt, hash_password, local_now

router = Router(name="student")
MENTAL_SUBJECT = "mental arifmetika"
MENTAL_DURATION_MINUTES = 10
MENTAL_QUESTION_LIMIT = 100


def utc_value(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


async def get_participant(session, telegram_id):
    return await session.scalar(select(Participant).where(Participant.telegram_id == telegram_id))


def is_mental_subject(subject):
    return bool(subject and subject.name.casefold() == MENTAL_SUBJECT)


def normalize_number(value):
    raw = (value or "").strip().replace(" ", "").replace(",", ".")
    try:
        number = Decimal(raw)
        return number if number.is_finite() else None
    except InvalidOperation:
        return None


async def participant_questions(session, participant, mental=False):
    query = select(Question).where(
        Question.subject_id == participant.subject_id,
        Question.level_id == participant.level_id,
        Question.active.is_(True),
    ).order_by(Question.position, Question.id)
    if mental:
        query = query.limit(MENTAL_QUESTION_LIMIT)
    return (await session.execute(query)).scalars().all()


def attempt_deadline(attempt, cfg, mental=False):
    if mental:
        return utc_value(attempt.started_at) + timedelta(minutes=MENTAL_DURATION_MINUTES)
    return utc_value(cfg.start_at) + timedelta(minutes=cfg.duration_minutes)


async def telegram_subscribed(bot: Bot, user_id: int, channel: str) -> bool:
    if not channel:
        return True
    try:
        member = await bot.get_chat_member(channel, user_id)
        return member.status in {"member", "administrator", "creator"}
    except Exception:
        return False


async def subscription_passed(bot: Bot, session, user_id: int, settings) -> tuple[bool, bool, bool]:
    tg_ok = await telegram_subscribed(bot, user_id, settings.telegram_channel)
    # Instagram havolasi ko‘rsatiladi, lekin rasmiy Telegram Bot API orqali tekshirilmaydi.
    instagram_ok = True
    return tg_ok, tg_ok, instagram_ok


async def show_subscription(message: Message, session, settings, instagram_confirmed=False):
    await message.answer(
        "Botdan foydalanish uchun quyidagi Instagram sahifa va Telegram kanalga obuna bo‘ling. So‘ng <b>✅ Obuna bo‘ldim</b> tugmasini bosing. Bot Telegram kanal obunasini avtomatik tekshiradi.",
        parse_mode=ParseMode.HTML,
        reply_markup=subscription_kb(settings.telegram_channel_url, settings.instagram_url, instagram_confirmed),
    )


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        settings = data["settings"]
        if not settings.telegram_channel and not settings.instagram_url:
            return await handler(event, data)
        if isinstance(event, Message) and event.text and event.text.startswith("/start"):
            return await handler(event, data)
        if isinstance(event, CallbackQuery) and (event.data or "").startswith("social:"):
            return await handler(event, data)
        user = event.from_user
        async with data["sessions"]() as session:
            passed, _, instagram_ok = await subscription_passed(data["bot"], session, user.id, settings)
            if not passed:
                target = event.message if isinstance(event, CallbackQuery) else event
                await show_subscription(target, session, settings, instagram_ok)
                if isinstance(event, CallbackQuery): await event.answer("Avval obunani tasdiqlang", show_alert=True)
                return
        return await handler(event, data)


router.message.outer_middleware(SubscriptionMiddleware())
router.callback_query.outer_middleware(SubscriptionMiddleware())


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, sessions, settings):
    await state.clear()
    async with sessions() as session:
        p = await get_participant(session, message.from_user.id)
        passed, _, instagram_ok = await subscription_passed(message.bot, session, message.from_user.id, settings)
        if not passed:
            await show_subscription(message, session, settings, instagram_ok)
            return
    await message.answer(
        "Assalomu alaykum! Olimpiada botiga xush kelibsiz.\nKerakli bo‘limni tanlang:",
        reply_markup=home(bool(p)),
    )


@router.message(F.text == "🏠 Bosh menyu")
async def back_home(message: Message, state: FSMContext, sessions, settings):
    await start(message, state, sessions, settings)


@router.callback_query(F.data == "social:check")
async def check_social(call: CallbackQuery, sessions, settings):
    async with sessions() as session:
        passed, tg_ok, instagram_ok = await subscription_passed(call.bot, session, call.from_user.id, settings)
        if passed:
            record = await session.scalar(select(SocialVerification).where(SocialVerification.telegram_id == call.from_user.id))
            if not record:
                record = SocialVerification(telegram_id=call.from_user.id, instagram_confirmed=instagram_ok); session.add(record)
            record.verified_at = datetime.now(timezone.utc); await session.commit()
            p = await get_participant(session, call.from_user.id)
        else:
            missing = []
            if not tg_ok: missing.append("Telegram kanal")
            await call.answer("Obuna topilmadi: " + ", ".join(missing), show_alert=True)
            return
    await call.answer("Obuna tasdiqlandi!")
    await call.message.edit_text("✅ Obuna tasdiqlandi. Endi botdan foydalanishingiz mumkin.")
    await call.message.answer("Kerakli bo‘limni tanlang:", reply_markup=home(bool(p)))


@router.message(F.text == "🏆 Olimpiadaga qatnashish")
async def registration_start(message: Message, state: FSMContext, sessions):
    async with sessions() as session:
        p = await get_participant(session, message.from_user.id)
        cfg = await session.get(OlympiadConfig, 1)
    if p:
        await message.answer("Siz avval ro‘yxatdan o‘tgansiz.", reply_markup=cabinet())
        return
    if not cfg.registration_open:
        await message.answer("Hozir ro‘yxatdan o‘tish yopilgan.")
        return
    await state.set_state(Registration.full_name)
    await message.answer("Ism va familiyangizni to‘liq yozing:")


@router.message(Registration.full_name)
async def reg_name(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if len(value.split()) < 2 or len(value) > 255:
        await message.answer("Ism va familiyani to‘liq kiriting. Masalan: Yuldashev Ulug‘bek")
        return
    await state.update_data(full_name=value)
    await state.set_state(Registration.region)
    await message.answer("Viloyatingizni tanlang:", reply_markup=inline_items(list(enumerate(REGIONS.keys())), "regregion", 2))


@router.callback_query(Registration.region, F.data.startswith("regregion:"))
async def reg_region(call: CallbackQuery, state: FSMContext):
    idx = int(call.data.split(":")[1]); region = list(REGIONS.keys())[idx]
    await state.update_data(region=region)
    await state.set_state(Registration.district)
    await call.message.edit_text("Tuman yoki shahringizni tanlang:", reply_markup=inline_items(list(enumerate(REGIONS[region])), "regdistrict", 2))
    await call.answer()


@router.callback_query(Registration.district, F.data.startswith("regdistrict:"))
async def reg_district(call: CallbackQuery, state: FSMContext):
    data = await state.get_data(); district = REGIONS[data["region"]][int(call.data.split(":")[1])]
    await state.update_data(district=district)
    await state.set_state(Registration.birth_date)
    await call.message.edit_text("Tug‘ilgan sanangizni kiriting: <b>kun.oy.yil</b>\nMasalan: 25.08.2010", parse_mode=ParseMode.HTML)
    await call.answer()


@router.message(Registration.birth_date)
async def reg_birth(message: Message, state: FSMContext):
    try:
        birth = datetime.strptime((message.text or "").strip(), "%d.%m.%Y").date()
        age = age_from_birth(birth)
        if age < 5 or age > 100:
            raise ValueError
    except ValueError:
        await message.answer("Sanani to‘g‘ri kiriting. Masalan: 25.08.2010")
        return
    await state.update_data(birth_date=birth.isoformat(), age=age)
    await state.set_state(Registration.phone)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("Telefon raqamingizni yuboring yoki +998901234567 ko‘rinishida yozing:", reply_markup=kb)


@router.message(Registration.phone)
async def reg_phone(message: Message, state: FSMContext, sessions):
    phone = message.contact.phone_number if message.contact else (message.text or "").strip().replace(" ", "")
    if len(phone) < 9:
        await message.answer("Telefon raqamni to‘g‘ri yuboring.")
        return
    await state.update_data(phone=phone)
    async with sessions() as session:
        subjects = (await session.execute(select(Subject).where(Subject.active.is_(True)).order_by(Subject.name))).scalars().all()
    if not subjects:
        await message.answer("Admin hali fanlarni qo‘shmagan. Keyinroq qayta urinib ko‘ring.", reply_markup=home())
        await state.clear(); return
    await state.set_state(Registration.subject)
    await message.answer("Qaysi fandan qatnashasiz?", reply_markup=inline_items([(x.id, x.name) for x in subjects], "regsubject", 2))


@router.callback_query(Registration.subject, F.data.startswith("regsubject:"))
async def reg_subject(call: CallbackQuery, state: FSMContext, sessions):
    subject_id = int(call.data.split(":")[1])
    async with sessions() as session:
        subject = await session.get(Subject, subject_id)
        levels = (await session.execute(select(Level).where(Level.subject_id == subject_id, Level.active.is_(True)).order_by(Level.name))).scalars().all()
    if not levels:
        await call.answer("Bu fan uchun daraja hali qo‘shilmagan", show_alert=True); return
    await state.update_data(subject_id=subject_id, subject_name=subject.name)
    await state.set_state(Registration.level)
    await call.message.edit_text("Darajani tanlang:", reply_markup=inline_items([(x.id, x.name) for x in levels], "reglevel", 2)); await call.answer()


@router.callback_query(Registration.level, F.data.startswith("reglevel:"))
async def reg_level(call: CallbackQuery, state: FSMContext, sessions):
    level_id = int(call.data.split(":")[1])
    async with sessions() as session: level = await session.get(Level, level_id)
    await state.update_data(level_id=level_id, level_name=level.name)
    data = await state.get_data()
    text = (f"Ma’lumotlarni tekshiring:\n\n👤 {data['full_name']}\n📍 {data['region']}, {data['district']}\n"
            f"🎂 {datetime.fromisoformat(data['birth_date']).strftime('%d.%m.%Y')} ({data['age']} yosh)\n📱 {data['phone']}\n"
            f"📚 {data['subject_name']} — {data['level_name']}")
    await state.set_state(Registration.confirm)
    await call.message.edit_text(text, reply_markup=confirm_kb()); await call.answer()


@router.callback_query(Registration.confirm, F.data == "reg:cancel")
async def reg_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear(); await call.message.edit_text("Ro‘yxatdan o‘tish bekor qilindi."); await call.message.answer("Bosh menyu", reply_markup=home()); await call.answer()


@router.callback_query(Registration.confirm, F.data == "reg:confirm")
async def reg_confirm(call: CallbackQuery, state: FSMContext, sessions, settings):
    data = await state.get_data(); login, password, code = credentials()
    async with sessions() as session:
        if await get_participant(session, call.from_user.id):
            await call.answer("Siz ro‘yxatdan o‘tgansiz", show_alert=True); return
        p = Participant(telegram_id=call.from_user.id, username=call.from_user.username, full_name=data["full_name"], phone=data["phone"],
            region=data["region"], district=data["district"], birth_date=date.fromisoformat(data["birth_date"]), age=data["age"],
            subject_id=data["subject_id"], level_id=data["level_id"], login=login, password_hash=hash_password(password), participant_code=code)
        session.add(p); await session.commit()
    await state.clear(); await call.message.edit_text("✅ Ro‘yxatdan muvaffaqiyatli o‘tdingiz!")
    await call.message.answer(f"Sizning ma’lumotlaringiz:\n🆔 Qatnashchi ID: <b>{code}</b>\nLogin: <code>{login}</code>\nParol: <code>{password}</code>\n\nBu ma’lumotlarni saqlab qo‘ying.", parse_mode=ParseMode.HTML, reply_markup=cabinet()); await call.answer()
    admin_text = (f"🆕 Yangi qatnashchi\n\n👤 {data['full_name']}\n🆔 {code}\n📍 {data['region']}, {data['district']}\n"
                  f"🎂 {data['age']} yosh\n📱 {data['phone']}\n📚 {data['subject_name']} — {data['level_name']}")
    for admin_id in settings.admin_ids:
        try: await call.bot.send_message(admin_id, admin_text)
        except Exception: pass


@router.message(F.text == "👤 Mening kabinetim")
async def my_cabinet(message: Message, sessions):
    async with sessions() as session: p = await get_participant(session, message.from_user.id)
    if not p: await message.answer("Avval ro‘yxatdan o‘ting.", reply_markup=home()); return
    if p.blocked: await message.answer("Sizning akkauntingiz admin tomonidan bloklangan."); return
    await message.answer(f"Xush kelibsiz, {p.full_name}!", reply_markup=cabinet())


@router.message(F.text == "👤 Ma’lumotlarim")
async def profile(message: Message, sessions):
    async with sessions() as session:
        p = await get_participant(session, message.from_user.id)
        if not p: await message.answer("Ma’lumot topilmadi."); return
        subject = await session.get(Subject, p.subject_id); level = await session.get(Level, p.level_id)
    await message.answer(f"👤 {p.full_name}\n🆔 {p.participant_code}\n📍 {p.region}, {p.district}\n🎂 {p.birth_date.strftime('%d.%m.%Y')} ({p.age} yosh)\n📱 {p.phone}\n📚 {subject.name} — {level.name}")


@router.message(F.text == "📅 Boshlanish vaqti")
async def schedule_info(message: Message, sessions, settings):
    async with sessions() as session:
        cfg = await session.get(OlympiadConfig, 1)
        p = await get_participant(session, message.from_user.id)
        subject = await session.get(Subject, p.subject_id) if p else None
    duration = MENTAL_DURATION_MINUTES if is_mental_subject(subject) else cfg.duration_minutes
    await message.answer(f"🏆 {cfg.title}\n📅 Boshlanish: {fmt_dt(cfg.start_at, settings.timezone)}\n⏳ Davomiyligi: {duration} daqiqa")


async def complete_attempt(session, attempt, questions):
    attempt.submitted_at = datetime.now(timezone.utc)
    auto_graded = bool(questions) and all(
        (question.answer_type == "choice" and question.correct_option is not None)
        or (question.answer_type == "text" and question.correct_text is not None)
        for question in questions
    )
    if auto_graded:
        answers = (await session.execute(select(Answer).where(Answer.attempt_id == attempt.id))).scalars().all()
        attempt.total_score = float(sum(answer.score or 0 for answer in answers))
        attempt.admin_comment = "Avtomatik baholandi."
        attempt.status = "reviewed"
    else:
        attempt.status = "submitted"
    return auto_graded


async def send_current_question(message: Message, state: FSMContext, sessions, settings):
    async with sessions() as session:
        p = await get_participant(session, message.chat.id)
        attempt = await session.scalar(select(Attempt).where(Attempt.participant_id == p.id))
        cfg = await session.get(OlympiadConfig, 1)
        subject = await session.get(Subject, p.subject_id)
        mental = is_mental_subject(subject)
        questions = await participant_questions(session, p, mental)
        if not attempt or attempt.submitted_at: return
        deadline = attempt_deadline(attempt, cfg, mental)
        if datetime.now(timezone.utc) >= deadline or attempt.current_index >= len(questions):
            auto_graded = await complete_attempt(session, attempt, questions)
            max_score = float(sum(question.max_score for question in questions))
            await session.commit(); await state.clear()
            if auto_graded:
                await message.answer("✅ Test yakunlandi va javoblaringiz avtomatik tekshirildi. Natija admin e’lon qilgandan keyin ko‘rinadi.", reply_markup=cabinet())
            else:
                await message.answer("✅ Javoblaringiz adminga yuborildi. Natija tekshirilgach e’lon qilinadi.", reply_markup=cabinet())
            for admin_id in settings.admin_ids:
                if auto_graded:
                    percent = (attempt.total_score or 0) / max_score * 100 if max_score else 0
                    answers = (await session.execute(select(Answer).where(Answer.attempt_id == attempt.id))).scalars().all()
                    correct = sum(1 for answer in answers if answer.score is not None and answer.score > 0)
                    answered = len(answers)
                    notice = (f"🤖 {'Mental arifmetika' if mental else 'Test'} avtomatik tekshirildi\n👤 {p.full_name}\n🆔 {p.participant_code}\n"
                              f"✅ To‘g‘ri: {correct}\n❌ Noto‘g‘ri: {answered - correct}\n⭕ Ishlanmagan: {len(questions) - answered}\n"
                              f"Natija: {attempt.total_score:g}/{max_score:g} — {percent:.1f}%")
                else:
                    notice = f"📨 Olimpiada yakunlandi\n👤 {p.full_name}\n🆔 {p.participant_code}\nJavoblarni admin panelda tekshirishingiz mumkin."
                try: await message.bot.send_message(admin_id, notice)
                except Exception: pass
            return
        q = questions[attempt.current_index]
        remaining_seconds = max(0, int((deadline - datetime.now(timezone.utc)).total_seconds()))
        remain = f"{remaining_seconds // 60:02d}:{remaining_seconds % 60:02d}" if mental else f"{remaining_seconds // 60} daqiqa"
    text = f"❓ <b>{attempt.current_index + 1}/{len(questions)}-savol</b>  |  ⏱ {remain}\n\n{escape(q.text)}\n\nMaksimal ball: {q.max_score:g}"
    markup = None
    if q.answer_type == "choice":
        rows = []
        for idx, option in enumerate((q.options or "").split("|")):
            rows.append([InlineKeyboardButton(text=f"{chr(65+idx)}) {option}", callback_data=f"answer:{q.id}:{idx}")])
        markup = InlineKeyboardMarkup(inline_keyboard=rows)
    elif q.answer_type == "photo": text += "\n\n📷 Javobingizni rasm qilib yuboring."
    else: text += "\n\n🔢 Javobni faqat son bilan yozing." if mental else "\n\n✍️ Javobingizni matn ko‘rinishida yuboring."
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=markup)


@router.message(F.text == "🏆 Olimpiadani boshlash")
async def begin_exam(message: Message, state: FSMContext, sessions, settings):
    async with sessions() as session:
        p = await get_participant(session, message.from_user.id); cfg = await session.get(OlympiadConfig, 1)
        if not p: await message.answer("Avval ro‘yxatdan o‘ting."); return
        if p.blocked: await message.answer("Siz bloklangansiz."); return
        if not cfg.start_at: await message.answer("Admin hali olimpiada vaqtini belgilamagan."); return
        now = local_now(settings.timezone); start_at = as_aware(cfg.start_at, settings.timezone)
        if now < start_at: await message.answer(f"Olimpiada {fmt_dt(cfg.start_at, settings.timezone)} da boshlanadi."); return
        if now >= start_at + timedelta(minutes=cfg.duration_minutes):
            await message.answer("Olimpiada vaqti tugagan."); return
        subject = await session.get(Subject, p.subject_id)
        mental = is_mental_subject(subject)
        questions_count = len(await participant_questions(session, p, mental))
        if not questions_count: await message.answer("Sizning fan va darajangiz uchun savollar hali kiritilmagan."); return
        if mental and questions_count < MENTAL_QUESTION_LIMIT:
            await message.answer(f"Mental arifmetika uchun hozir {questions_count} ta misol kiritilgan. Boshlash uchun {MENTAL_QUESTION_LIMIT} ta misol to‘liq bo‘lishi kerak."); return
        attempt = await session.scalar(select(Attempt).where(Attempt.participant_id == p.id))
        if attempt and attempt.submitted_at: await message.answer("Siz olimpiadani yakunlagansiz. Qayta ishlash mumkin emas."); return
        if not attempt:
            attempt = Attempt(participant_id=p.id, started_at=datetime.now(timezone.utc)); session.add(attempt); await session.commit()
    await state.set_state(Exam.answering)
    if mental:
        await message.answer(f"🧠 Mental arifmetika boshlandi. Sizga {questions_count} ta misol uchun {MENTAL_DURATION_MINUTES} daqiqa berildi. Javobni faqat son bilan yozing.")
    else:
        await message.answer("Olimpiada boshlandi. Har bir javob darhol saqlanadi.")
    await send_current_question(message, state, sessions, settings)


async def save_answer(message: Message, state: FSMContext, sessions, settings, text_answer=None, file_id=None, selected_option=None, expected_type=None, expected_question_id=None):
    async with sessions() as session:
        p = await get_participant(session, message.chat.id); attempt = await session.scalar(select(Attempt).where(Attempt.participant_id == p.id))
        subject = await session.get(Subject, p.subject_id)
        mental = is_mental_subject(subject)
        questions = await participant_questions(session, p, mental)
        if not attempt or attempt.submitted_at or attempt.current_index >= len(questions): return
        cfg = await session.get(OlympiadConfig, 1)
        if datetime.now(timezone.utc) >= attempt_deadline(attempt, cfg, mental):
            await session.rollback()
            expired = True
        else:
            expired = False
        if expired:
            await send_current_question(message, state, sessions, settings); return
        q = questions[attempt.current_index]
        if expected_type and q.answer_type != expected_type: return
        if expected_question_id and q.id != expected_question_id: return
        if mental and q.correct_text is not None and normalize_number(text_answer) is None:
            await message.answer("Javobni faqat son bilan yozing. Masalan: 125 yoki -4,5")
            return
        old = await session.scalar(select(Answer).where(Answer.attempt_id == attempt.id, Answer.question_id == q.id))
        if selected_option is not None and q.correct_option is not None:
            auto_score = q.max_score if q.correct_option == selected_option else 0
        elif text_answer is not None and q.correct_text is not None:
            submitted_number = normalize_number(text_answer)
            correct_number = normalize_number(q.correct_text)
            auto_score = q.max_score if submitted_number is not None and submitted_number == correct_number else 0
        else:
            auto_score = None
        if old:
            old.text_answer, old.file_id, old.selected_option, old.score = text_answer, file_id, selected_option, auto_score
        else:
            session.add(Answer(attempt_id=attempt.id, question_id=q.id, text_answer=text_answer, file_id=file_id, selected_option=selected_option, score=auto_score))
        attempt.current_index += 1; await session.commit()
    if not mental:
        await message.answer("✅ Javob saqlandi.")
    await send_current_question(message, state, sessions, settings)


@router.callback_query(Exam.answering, F.data.startswith("answer:"))
async def choice_answer(call: CallbackQuery, state: FSMContext, sessions, settings):
    _, qid, idx = call.data.split(":")
    option_index = int(idx)
    async with sessions() as session: q = await session.get(Question, int(qid))
    options = (q.options or "").split("|"); value = f"{chr(65+option_index)}) {options[option_index]}"
    await call.answer("Javob saqlandi"); await call.message.edit_reply_markup(reply_markup=None)
    await save_answer(call.message, state, sessions, settings, text_answer=value, selected_option=option_index, expected_type="choice", expected_question_id=int(qid))


@router.message(Exam.answering, F.photo)
async def photo_answer(message: Message, state: FSMContext, sessions, settings):
    await save_answer(message, state, sessions, settings, file_id=message.photo[-1].file_id, text_answer=message.caption, expected_type="photo")


@router.message(Exam.answering, F.text)
async def text_answer(message: Message, state: FSMContext, sessions, settings):
    await save_answer(message, state, sessions, settings, text_answer=message.text, expected_type="text")


@router.message(F.text == "📊 Natijam")
async def result(message: Message, sessions):
    async with sessions() as session:
        p = await get_participant(session, message.from_user.id); cfg = await session.get(OlympiadConfig, 1)
        attempt = await session.scalar(select(Attempt).where(Attempt.participant_id == p.id)) if p else None
        questions = (await session.execute(select(Question).where(Question.subject_id == p.subject_id, Question.level_id == p.level_id, Question.active.is_(True)))).scalars().all() if p else []
        answers = (await session.execute(select(Answer).where(Answer.attempt_id == attempt.id))).scalars().all() if attempt else []
    if not attempt or not attempt.submitted_at: await message.answer("Sizda yakunlangan natija yo‘q."); return
    if not cfg.results_published or attempt.status != "reviewed": await message.answer("Javoblaringiz tekshirilmoqda. Natija hali e’lon qilinmagan."); return
    max_score = float(sum(question.max_score for question in questions))
    total_score = float(attempt.total_score or 0)
    percent = total_score / max_score * 100 if max_score else 0
    answer_by_question = {answer.question_id: answer for answer in answers}
    auto_questions = [question for question in questions if question.correct_option is not None or question.correct_text is not None]
    details = ""
    if len(auto_questions) == len(questions):
        correct = sum(1 for question in questions if answer_by_question.get(question.id) and (answer_by_question[question.id].score or 0) > 0)
        details = f"\n✅ To‘g‘ri: <b>{correct}</b>\n❌ Noto‘g‘ri yoki javobsiz: <b>{len(questions) - correct}</b>"
    await message.answer(
        f"🎉 <b>Natijangiz</b>{details}\n🏆 Ball: <b>{total_score:g}/{max_score:g}</b>\n📈 Foiz: <b>{percent:.1f}%</b>\nAdmin izohi: {escape(attempt.admin_comment or '—')}",
        parse_mode=ParseMode.HTML,
    )


@router.message(F.text == "🏅 Reyting")
async def ranking(message: Message, sessions):
    async with sessions() as session:
        cfg = await session.get(OlympiadConfig, 1)
        if not cfg.results_published or not cfg.show_ranking: await message.answer("Reyting hali e’lon qilinmagan."); return
        rows = (await session.execute(select(Attempt, Participant).join(Participant, Attempt.participant_id == Participant.id).where(Attempt.status == "reviewed").order_by(Attempt.total_score.desc()).limit(20))).all()
        questions = (await session.execute(select(Question).where(Question.active.is_(True)))).scalars().all()
    if not rows: await message.answer("Reytingda natijalar yo‘q."); return
    maximum_by_level = {}
    for question in questions:
        key = (question.subject_id, question.level_id)
        maximum_by_level[key] = maximum_by_level.get(key, 0) + question.max_score
    lines = []
    for i, (attempt, participant) in enumerate(rows, 1):
        maximum = maximum_by_level.get((participant.subject_id, participant.level_id), 0)
        percent = float(attempt.total_score or 0) / maximum * 100 if maximum else 0
        lines.append(f"{i}. {escape(participant.full_name)} — {attempt.total_score:g}/{maximum:g} ({percent:.1f}%)")
    await message.answer("🏅 <b>TOP-20 reyting</b>\n\n" + "\n".join(lines), parse_mode=ParseMode.HTML)


@router.message(StateFilter(None))
async def unknown(message: Message):
    await message.answer("Kerakli tugmani menyudan tanlang yoki /start bosing.")
