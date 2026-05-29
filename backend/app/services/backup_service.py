"""Database backup creation and listing."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import restore_sqlite_database_from
from app.models import BackupRecord
from app.services.exceptions import NotFoundError, ValidationError


class BackupService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self._db = db
        self._settings = settings or get_settings()

    def _database_path(self) -> Path:
        url = self._settings.database_url
        if not url.startswith("sqlite:///"):
            raise ValidationError("Backups are only supported for SQLite databases")
        db_path = Path(url.removeprefix("sqlite:///"))
        if not db_path.is_file():
            raise ValidationError(f"Database file not found: {db_path}")
        return db_path

    def create_backup(self, notes: str | None = None) -> BackupRecord:
        db_path = self._database_path()
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        dest = self._settings.backup_dir / f"dispatch_{stamp}.db"
        shutil.copy2(db_path, dest)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(f"{db_path}{suffix}")
            if sidecar.is_file():
                shutil.copy2(sidecar, Path(f"{dest}{suffix}"))
        record = BackupRecord(
            file_path=str(dest),
            notes=notes,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record

    def list_backups(self) -> list[BackupRecord]:
        return list(
            self._db.scalars(
                select(BackupRecord).order_by(BackupRecord.created_at.desc())
            ).all()
        )

    def get_backup(self, backup_id: int) -> BackupRecord:
        record = self._db.get(BackupRecord, backup_id)
        if record is None:
            raise NotFoundError("BackupRecord", backup_id)
        return record

    def restore_backup(self, backup_id: int) -> None:
        record = self.get_backup(backup_id)
        backup_path = Path(record.file_path)
        if not backup_path.is_file():
            raise ValidationError(f"Backup file not found: {backup_path}")
        restore_sqlite_database_from(backup_path, target_db_path=self._database_path())
