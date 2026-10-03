from datetime import date, datetime
from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .seed_questions import SEEDED_TESTS


class Base(AsyncAttrs, DeclarativeBase):
    pass


DEFAULT_CATALOG = {
    "Ingliz tili": ["Starter", "Beginner", "Elementary", "Pre-Intermediate", "Intermediate", "Upper-Intermediate", "Advanced", "IELTS"],
    "Rus tili": ["A1", "A2", "B1"],
    "Koreys tili": ["Boshlang‘ich", "O‘rta"],
    "Arab tili": ["A1", "A2", "B1"],
    "Matematika": ["4-sinf", "5-sinf", "6-sinf", "7-sinf", "8-sinf", "9-sinf", "10-sinf", "11-sinf"],
    "Mental arifmetika": ["1-xonali A", "2-xonali B", "2-xonali C"],
    "IT": ["HTML", "HTML CSS", "HTML CSS JS", "JavaScript", "Vue", "React", "Python"],
    "Kompyuter": ["Word", "Excel", "PowerPoint"],
}


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    levels: Mapped[list["Level"]] = relationship(back_populates="subject", cascade="all, delete-orphan")


class Level(Base):
    __tablename__ = "levels"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    subject: Mapped[Subject] = relationship(back_populates="levels")
    __table_args__ = (UniqueConstraint("subject_id", "name"),)


class Participant(Base):
    __tablename__ = "participants"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    owner_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(40))
    region: Mapped[str] = mapped_column(String(120))
    district: Mapped[str] = mapped_column(String(120))
    birth_date: Mapped[date] = mapped_column(Date)
    age: Mapped[int] = mapped_column(Integer)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"))
    login: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    participant_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    active_profile: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    subject: Mapped[Subject] = relationship()
    level: Mapped[Level] = relationship()


class OlympiadConfig(Base):
    __tablename__ = "olympiad_config"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    title: Mapped[str] = mapped_column(String(255), default="Olimpiada")
    registration_open: Mapped[bool] = mapped_column(Boolean, default=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    results_published: Mapped[bool] = mapped_column(Boolean, default=False)
    show_ranking: Mapped[bool] = mapped_column(Boolean, default=True)
    test_stopped: Mapped[bool] = mapped_column(Boolean, default=False)


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    answer_type: Mapped[str] = mapped_column(String(20), default="text")  # text, photo, choice
    options: Mapped[str | None] = mapped_column(Text, nullable=True)  # A|B|C|D matnlari
    correct_option: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0=A, 1=B, 2=C, 3=D
    correct_text: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Mental arifmetika javobi
    seed_key: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True, index=True)
    max_score: Mapped[float] = mapped_column(Float, default=1)
    position: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"), unique=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_index: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    admin_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="working")
    participant: Mapped[Participant] = relationship()


class Answer(Base):
    __tablename__ = "answers"
    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    text_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    selected_option: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    admin_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    question: Mapped[Question] = relationship()
    __table_args__ = (UniqueConstraint("attempt_id", "question_id"),)


class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("participant_id", "kind"),)


class AdminLog(Base):
    __tablename__ = "admin_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SocialVerification(Base):
    __tablename__ = "social_verifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    instagram_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def make_db(url: str):
    engine = create_async_engine(url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    return engine, sessions


async def init_db(engine, sessions):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(ensure_schema)
    async with sessions() as session:
        config = await session.get(OlympiadConfig, 1)
        if not config:
            session.add(OlympiadConfig(id=1))
        existing_subjects = (await session.execute(select(Subject))).scalars().all()
        subject_by_name = {item.name.casefold(): item for item in existing_subjects}
        for subject_name, level_names in DEFAULT_CATALOG.items():
            subject = subject_by_name.get(subject_name.casefold())
            if not subject:
                subject = Subject(name=subject_name, active=True)
                session.add(subject)
                await session.flush()
                subject_by_name[subject_name.casefold()] = subject
            existing_levels = (await session.execute(select(Level).where(Level.subject_id == subject.id))).scalars().all()
            level_keys = {item.name.casefold() for item in existing_levels}
            for level_name in level_names:
                if level_name.casefold() not in level_keys:
                    session.add(Level(subject_id=subject.id, name=level_name, active=True))
                    level_keys.add(level_name.casefold())
            if subject_name == "Matematika":
                legacy_math_levels = {"boshlang‘ich", "b", "b+", "c+"}
                for existing_level in existing_levels:
                    if existing_level.name.casefold() in legacy_math_levels:
                        existing_level.active = False
            if subject_name == "Mental arifmetika":
                active_mental_levels = {name.casefold() for name in level_names}
                for existing_level in existing_levels:
                    if existing_level.name.casefold() not in active_mental_levels:
                        existing_level.active = False
        await session.flush()
        for subject_name, tests_by_level in SEEDED_TESTS.items():
            subject = await session.scalar(select(Subject).where(func.lower(Subject.name) == subject_name.lower()))
            if not subject:
                continue
            for level_name, tests in tests_by_level.items():
                level = await session.scalar(
                    select(Level).where(Level.subject_id == subject.id, func.lower(Level.name) == level_name.lower())
                )
                if not level:
                    continue
                seed_prefix = f"{subject_name}:{level_name}:"
                already_seeded = await session.scalar(
                    select(Question.id).where(Question.seed_key.like(f"{seed_prefix}%")).limit(1)
                )
                if not already_seeded:
                    previous_questions = (await session.execute(
                        select(Question).where(
                            Question.subject_id == subject.id,
                            Question.level_id == level.id,
                            Question.seed_key.is_(None),
                        )
                    )).scalars().all()
                    for previous_question in previous_questions:
                        previous_question.active = False
                for position, test in enumerate(tests, 1):
                    seed_key = f"{seed_prefix}{position:02d}"
                    question = await session.scalar(select(Question).where(Question.seed_key == seed_key))
                    if not question:
                        question = Question(seed_key=seed_key, subject_id=subject.id, level_id=level.id)
                        session.add(question)
                    if len(test) == 2:
                        question_text, correct_text = test
                        question.answer_type = "text"
                        question.options = None
                        question.correct_option = None
                        question.correct_text = str(correct_text)
                    else:
                        question_text, options, correct_option = test
                        question.answer_type = "choice"
                        question.options = "|".join(options)
                        question.correct_option = correct_option
                        question.correct_text = None
                    question.text = question_text
                    question.max_score = 1
                    question.position = position
                    question.active = True
        await session.commit()


def ensure_schema(sync_conn):
    """Add new auto-grading columns without deleting existing Railway/SQLite data."""
    schema = inspect(sync_conn)
    config_columns = {column["name"] for column in schema.get_columns("olympiad_config")}
    participant_columns = {column["name"] for column in schema.get_columns("participants")}
    question_columns = {column["name"] for column in schema.get_columns("questions")}
    answer_columns = {column["name"] for column in schema.get_columns("answers")}
    if "test_stopped" not in config_columns:
        sync_conn.execute(text("ALTER TABLE olympiad_config ADD COLUMN test_stopped BOOLEAN DEFAULT FALSE"))
    if "owner_telegram_id" not in participant_columns:
        sync_conn.execute(text("ALTER TABLE participants ADD COLUMN owner_telegram_id BIGINT"))
        sync_conn.execute(text("UPDATE participants SET owner_telegram_id = telegram_id WHERE owner_telegram_id IS NULL"))
    if "active_profile" not in participant_columns:
        sync_conn.execute(text("ALTER TABLE participants ADD COLUMN active_profile BOOLEAN DEFAULT TRUE"))
        sync_conn.execute(text("UPDATE participants SET active_profile = TRUE WHERE active_profile IS NULL"))
    sync_conn.execute(text("CREATE INDEX IF NOT EXISTS ix_participants_owner_telegram_id ON participants (owner_telegram_id)"))
    if "correct_option" not in question_columns:
        sync_conn.execute(text("ALTER TABLE questions ADD COLUMN correct_option INTEGER"))
    if "seed_key" not in question_columns:
        sync_conn.execute(text("ALTER TABLE questions ADD COLUMN seed_key VARCHAR(160)"))
    if "correct_text" not in question_columns:
        sync_conn.execute(text("ALTER TABLE questions ADD COLUMN correct_text VARCHAR(255)"))
    if "selected_option" not in answer_columns:
        sync_conn.execute(text("ALTER TABLE answers ADD COLUMN selected_option INTEGER"))
    sync_conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_questions_seed_key ON questions (seed_key)"))
