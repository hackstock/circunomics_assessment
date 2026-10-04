import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _ping_db() -> None:
    with engine.connect() as conn:
        if not settings.database_url.startswith("sqlite"):
            # Transaction-local, so it does not leak onto the pooled connection.
            # Shorter than the Compose healthcheck timeout (5s).
            conn.execute(text("SET LOCAL statement_timeout = '2s'"))
        conn.execute(text("SELECT 1"))


def database_ready() -> bool:
    try:
        _ping_db()
    except Exception:  # noqa: BLE001 — readiness is a boolean, not an error page
        return False
    return True


def wait_for_db(attempts: int = 30) -> None:
    if settings.database_url.startswith("sqlite"):
        attempts = 3
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            _ping_db()
            return
        except Exception as exc:  # noqa: BLE001 — retry until Postgres is ready
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"Database was not ready: {last_error}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
