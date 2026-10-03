import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from .db import Answer, Attempt, OlympiadConfig, Participant, Question, Reminder, Subject
from .keyboards import cabinet
from .utils import fmt_dt

MENTAL_SUBJECT = "mental arifmetika"
MENTAL_DURATION_MINUTES = 10
MENTAL_QUESTION_LIMIT = 100


def utc_value(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


async def reminder_loop(bot, sessions, settings, dispatcher):
    while True:
        try:
            async with sessions() as session:
                cfg = await session.get(OlympiadConfig, 1)
                if cfg.start_at and not cfg.test_stopped:
                    start = utc_value(cfg.start_at)
                    now = datetime.now(timezone.utc)
                    seconds = (start - now).total_seconds()
                    rows = (await session.execute(
                        select(Attempt, Participant, Subject)
                        .join(Participant, Attempt.participant_id == Participant.id)
                        .join(Subject, Participant.subject_id == Subject.id)
                        .where(Attempt.status == "working")
                    )).all()
                    for attempt, participant, subject in rows:
                        mental = subject.name.casefold() == MENTAL_SUBJECT
                        deadline = utc_value(attempt.started_at) + timedelta(minutes=MENTAL_DURATION_MINUTES) if mental else start + timedelta(minutes=cfg.duration_minutes)
                        if now < deadline:
                            continue
                        question_query = select(Question).where(
                            Question.subject_id == participant.subject_id,
                            Question.level_id == participant.level_id,
                            Question.active.is_(True),
                        ).order_by(Question.position, Question.id)
                        if mental:
                            question_query = question_query.limit(MENTAL_QUESTION_LIMIT)
                        questions = (await session.execute(question_query)).scalars().all()
                        answers = (await session.execute(select(Answer).where(Answer.attempt_id == attempt.id))).scalars().all()
                        all_auto = bool(questions) and all(
                            (q.answer_type == "choice" and q.correct_option is not None)
                            or (q.answer_type == "text" and q.correct_text is not None)
                            for q in questions
                        )
                        attempt.submitted_at = deadline
                        if all_auto:
                            attempt.total_score = float(sum(answer.score or 0 for answer in answers))
                            attempt.admin_comment = "Avtomatik baholandi."
                            attempt.status = "reviewed"
                        else:
                            attempt.status = "submitted"
                        await session.commit()

                        try:
                            state = dispatcher.fsm.get_context(bot=bot, chat_id=participant.telegram_id, user_id=participant.telegram_id)
                            await state.clear()
                        except Exception:
                            pass
                        if all_auto:
                            correct = sum(1 for answer in answers if answer.score is not None and answer.score > 0)
                            answered = len(answers)
                            incorrect = answered - correct
                            unanswered = len(questions) - answered
                            maximum = float(sum(q.max_score for q in questions))
                            percent = float(attempt.total_score or 0) / maximum * 100 if maximum else 0
                            title = "Mental arifmetika" if mental else "Test"
                            try:
                                await bot.send_message(
                                    participant.telegram_id,
                                    "⏰ Vaqt tugadi. Javoblaringiz avtomatik tekshirildi. Natija admin e’lon qilgandan keyin ko‘rinadi.",
                                    reply_markup=cabinet(),
                                )
                            except Exception:
                                pass
                            notice = (
                                f"🧠 {title} yakunlandi\n👤 {participant.full_name}\n🆔 {participant.participant_code}\n"
                                f"✅ To‘g‘ri: {correct}\n❌ Noto‘g‘ri: {incorrect}\n⭕ Ishlanmagan: {unanswered}\n"
                                f"Natija: {attempt.total_score:g}/{maximum:g} — {percent:.1f}%"
                            )
                        else:
                            try:
                                await bot.send_message(participant.telegram_id, "⏰ Vaqt tugadi. Javoblaringiz adminga yuborildi.", reply_markup=cabinet())
                            except Exception:
                                pass
                            notice = f"📨 Olimpiada yakunlandi\n👤 {participant.full_name}\n🆔 {participant.participant_code}\nJavoblarni admin panelda tekshiring."
                        for admin_id in settings.admin_ids:
                            try:
                                await bot.send_message(admin_id, notice)
                            except Exception:
                                pass
                    kind = "1h" if 0 < seconds <= 3600 else ("24h" if 23 * 3600 <= seconds <= 24 * 3600 else None)
                    if kind:
                        participants = (await session.execute(select(Participant).where(Participant.blocked.is_(False)))).scalars().all()
                        for p in participants:
                            exists = await session.scalar(select(Reminder).where(Reminder.participant_id == p.id, Reminder.kind == kind))
                            if exists: continue
                            try:
                                await bot.send_message(p.telegram_id, f"⏰ Eslatma! Olimpiada {fmt_dt(cfg.start_at, settings.timezone)} da boshlanadi.")
                                session.add(Reminder(participant_id=p.id, kind=kind)); await session.commit()
                            except Exception: await session.rollback()
        except Exception as exc:
            print(f"Reminder error: {exc}")
        await asyncio.sleep(10)
