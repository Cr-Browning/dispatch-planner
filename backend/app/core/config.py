"""Application configuration from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# dispatch-planner/ (repo root for data/, backups/, exports/)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _resolve_project_path(value: str | Path) -> Path:
    """Resolve relative paths against PROJECT_ROOT, not the shell cwd."""
    path = Path(value)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def _normalize_sqlite_url(url: str) -> str:
    """Turn sqlite relative paths into absolute paths under PROJECT_ROOT."""
    if not url.startswith("sqlite:///"):
        return url
    db_path = url.removeprefix("sqlite:///")
    if db_path in (":memory:", ":memory:"):
        return url
    if db_path.startswith("/"):
        return url
    resolved = _resolve_project_path(db_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{resolved}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_secret_key: str = "dev-secret-change-me"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'dispatch.db'}"
    backup_dir: Path = PROJECT_ROOT / "backups"
    export_dir: Path = PROJECT_ROOT / "exports"
    google_maps_api_key: str | None = None
    routing_provider: str = "mock"
    dispatcher_password: str = "changeme"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    access_token_expire_minutes: int = 60 * 12
    schema_version: str = "1"
    backup_on_startup: bool = False

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        return _normalize_sqlite_url(value)

    @field_validator("backup_dir", "export_dir", mode="before")
    @classmethod
    def normalize_path_settings(cls, value: str | Path) -> Path:
        return _resolve_project_path(value)

    def ensure_directories(self) -> None:
        db_path = Path(self.database_url.removeprefix("sqlite:///"))
        if ":memory:" not in self.database_url:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
