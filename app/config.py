import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: frozenset[int]
    database_url: str
    timezone: str
    telegram_channel: str
    telegram_channel_url: str
    instagram_url: str


def get_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN .env faylida ko'rsatilmagan")
    raw_ids = os.getenv("ADMIN_IDS", "")
    try:
        admin_ids = frozenset(int(x.strip()) for x in raw_ids.split(",") if x.strip())
    except ValueError as exc:
        raise RuntimeError("ADMIN_IDS faqat raqamlardan iborat bo'lishi kerak") from exc
    if not admin_ids:
        raise RuntimeError("ADMIN_IDS da kamida bitta Telegram ID bo'lishi kerak")
    url = (
        os.getenv("DATABASE_URL")
        or os.getenv("DATABASE_PRIVATE_URL")
        or os.getenv("DATABASE_PUBLIC_URL")
        or "sqlite+aiosqlite:///olympiad.db"
    ).strip()
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url.removeprefix("postgres://")
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    return Settings(
        token, admin_ids, url, os.getenv("TIMEZONE", "Asia/Tashkent"),
        os.getenv("TELEGRAM_CHANNEL", "").strip(),
        os.getenv("TELEGRAM_CHANNEL_URL", "").strip(),
        os.getenv("INSTAGRAM_URL", "").strip(),
    )
