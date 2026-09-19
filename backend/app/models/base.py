import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
