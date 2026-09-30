import hashlib
import secrets
import string
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


def hash_password(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def credentials():
    login = "OL" + "".join(secrets.choice(string.digits) for _ in range(6))
    password = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    code = "P-" + "".join(secrets.choice(string.digits) for _ in range(7))
    return login, password, code


def age_from_birth(birth: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def local_now(tz_name: str) -> datetime:
    return datetime.now(ZoneInfo(tz_name))


def as_aware(value: datetime | None, tz_name: str):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(tz_name))
    return value.astimezone(ZoneInfo(tz_name))


def fmt_dt(value: datetime | None, tz_name: str) -> str:
    return as_aware(value, tz_name).strftime("%d.%m.%Y %H:%M") if value else "Belgilanmagan"

