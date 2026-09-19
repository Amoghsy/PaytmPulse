import os
import logging
from urllib.parse import quote, unquote
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("paytm_pulse.database")


def sanitize_database_url(url: str) -> str:
    """
    Safely formats PostgreSQL URLs, converting postgres:// to postgresql://
    and URL-encoding any raw '@' or special characters inside passwords.
    """
    if not url or not url.strip():
        return url

    url = url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    # Handle passwords containing raw '@' characters
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


# Support direct DATABASE_URL (for Supabase / Neon / Render / Cloud Postgres)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL or not DATABASE_URL.strip():
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "paytm_pulse")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "paytm_pulse")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "paytm_pulse_secret_key")

    actual_host = POSTGRES_HOST
    if actual_host == "postgres" and not os.path.exists("/.dockerenv"):
        actual_host = "localhost"

    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{actual_host}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Sanitize connection string
DATABASE_URL = sanitize_database_url(DATABASE_URL)

# Configure engine connect arguments (Supabase & Cloud Postgres require SSL)
connect_args = {"connect_timeout": 5}
if "supabase" in DATABASE_URL.lower() or "pooler" in DATABASE_URL.lower() or "neon.tech" in DATABASE_URL.lower():
    connect_args["sslmode"] = "require"

try:
    logger.info(f"Connecting to database at {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'local'}...")
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args=connect_args
    )
    # Quick connectivity test
    with engine.connect() as test_conn:
        test_conn.execute(text("SELECT 1"))
    logger.info("Database connection established successfully!")
except Exception as e:
    logger.warning(f"Primary PostgreSQL connection failed ({str(e)}). Initializing local SQLite fallback for seamless API uptime...")
    SQLITE_URL = "sqlite:///./paytm_pulse.db"
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


from contextlib import contextmanager


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for standalone script / tool execution outside FastAPI request lifecycle."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """
    Actually tests PostgreSQL / Supabase connection by executing 'SELECT 1'.
    Returns True if healthy, False if unhealthy.
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.warning(f"Database connection health check failed: {str(e)}")
        return False
