"""SQLAlchemy engine, session factory, and schema initialization."""

from collections.abc import Generator
from pathlib import Path
import shutil

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.models import Base

settings = get_settings()

connect_args: dict = {}
engine_kwargs: dict = {"pool_pre_ping": True}

if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    if ":memory:" in settings.database_url:
        engine_kwargs["poolclass"] = StaticPool
        engine_kwargs["connect_args"] = connect_args
    else:
        engine_kwargs["connect_args"] = connect_args
else:
    engine_kwargs["connect_args"] = connect_args

engine = create_engine(settings.database_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db() -> None:
    """Create tables and stamp schema version if missing."""
    settings.ensure_directories()
    Base.metadata.create_all(bind=engine)
    _apply_sqlite_migrations()
    _ensure_schema_version()


def _apply_sqlite_migrations() -> None:
    """Lightweight column adds for existing SQLite databases."""
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(employees)").fetchall()
        columns = {row[1] for row in rows}
        if "phone" not in columns:
            conn.exec_driver_sql("ALTER TABLE employees ADD COLUMN phone VARCHAR(30)")
            conn.commit()


def _ensure_schema_version() -> None:
    from app.models import AppSetting

    with SessionLocal() as session:
        existing = session.execute(
            select(AppSetting).where(AppSetting.key == "schema_version")
        ).scalar_one_or_none()
        if existing is None:
            session.add(
                AppSetting(key="schema_version", value_json=f'"{settings.schema_version}"')
            )
            session.commit()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_db_for_tests() -> None:
    """Drop and recreate all tables (tests only)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def restore_sqlite_database_from(
    backup_path: Path, *, target_db_path: Path | None = None
) -> None:
    """Replace the live SQLite database file from a backup."""
    url = settings.database_url
    if not url.startswith("sqlite:///"):
        raise ValueError("Restore is only supported for SQLite databases")

    configured_path: Path | None = None
    if ":memory:" not in url:
        configured_path = Path(url.removeprefix("sqlite:///"))

    if target_db_path is not None:
        db_path = target_db_path
    elif configured_path is not None:
        db_path = configured_path
    else:
        raise ValueError("Cannot restore into an in-memory database")

    shutil.copy2(backup_path, db_path)
    for suffix in ("-wal", "-shm"):
        sidecar_backup = Path(f"{backup_path}{suffix}")
        sidecar_db = Path(f"{db_path}{suffix}")
        if sidecar_backup.is_file():
            shutil.copy2(sidecar_backup, sidecar_db)
        elif sidecar_db.is_file():
            sidecar_db.unlink(missing_ok=True)

    if configured_path is not None and db_path.resolve() == configured_path.resolve():
        engine.dispose()
        init_db()
