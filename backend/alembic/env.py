import os
import sys
from urllib.parse import quote, unquote
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()

from app.models import Base

config = context.config

if config.config_file_name:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        pass

target_metadata = Base.metadata


def sanitize_database_url(url: str) -> str:
    if not url or not url.strip():
        return url
    url = url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if "://" in url and url.count("@") > 1:
        scheme, rest = url.split("://", 1)
        last_at = rest.rfind("@")
        if last_at != -1:
            creds = rest[:last_at]
            host_db = rest[last_at + 1:]
            if ":" in creds:
                user, password = creds.split(":", 1)
                encoded_password = quote(unquote(password), safe="")
                url = f"{scheme}://{user}:{encoded_password}@{host_db}"
    return url


def get_url():
    db_url = os.getenv("DATABASE_URL")
    if db_url and db_url.strip():
        return sanitize_database_url(db_url)

    user = os.getenv("POSTGRES_USER", "paytm_pulse")
    password = os.getenv("POSTGRES_PASSWORD", "paytm_pulse_secret_key")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "paytm_pulse")
    if host == "postgres":
        host = "localhost"

    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_url()
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
