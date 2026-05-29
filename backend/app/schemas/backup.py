"""Backup API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BackupRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    notes: str | None
    created_at: datetime
