"""App settings read/update."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.export_service import CSV_COLUMNS


class SettingsService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_settings(self) -> dict:
        settings = get_settings()
        return {
            "routing_provider": settings.routing_provider,
            "export_columns": list(CSV_COLUMNS),
        }

    def update_settings(self) -> dict:
        return self.get_settings()
