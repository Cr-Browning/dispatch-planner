"""Database backup endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse

from app.api.errors import raise_http_for_domain
from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.schemas.backup import BackupRecordResponse
from app.services.backup_service import BackupService

router = APIRouter(prefix="/backups", tags=["backups"])


def get_backup_service(db: DbSession) -> BackupService:
    return BackupService(db, settings=get_settings())


@router.get("", response_model=list[BackupRecordResponse])
def list_backups(
    _user: CurrentUser,
    service: Annotated[BackupService, Depends(get_backup_service)],
) -> list[BackupRecordResponse]:
    return [BackupRecordResponse.model_validate(r) for r in service.list_backups()]


@router.post("", response_model=BackupRecordResponse, status_code=status.HTTP_201_CREATED)
def create_backup(
    _user: CurrentUser,
    service: Annotated[BackupService, Depends(get_backup_service)],
    notes: str | None = Query(default=None),
) -> BackupRecordResponse:
    try:
        record = service.create_backup(notes=notes or "manual")
    except Exception as exc:
        raise_http_for_domain(exc)
    return BackupRecordResponse.model_validate(record)


@router.post("/{backup_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
def restore_backup(
    backup_id: int,
    _user: CurrentUser,
    service: Annotated[BackupService, Depends(get_backup_service)],
) -> None:
    try:
        service.restore_backup(backup_id)
    except Exception as exc:
        raise_http_for_domain(exc)


@router.get("/{backup_id}/download")
def download_backup(
    backup_id: int,
    _user: CurrentUser,
    service: Annotated[BackupService, Depends(get_backup_service)],
) -> FileResponse:
    try:
        record = service.get_backup(backup_id)
    except Exception as exc:
        raise_http_for_domain(exc)
    from pathlib import Path

    path = Path(record.file_path)
    return FileResponse(path=path, filename=path.name, media_type="application/octet-stream")
