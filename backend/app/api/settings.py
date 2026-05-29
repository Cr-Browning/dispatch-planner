"""Settings endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, get_settings_service
from app.schemas.settings import AppSettingsResponse, AppSettingsUpdate
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AppSettingsResponse)
def get_settings(
    _user: CurrentUser,
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> AppSettingsResponse:
    data = service.get_settings()
    return AppSettingsResponse(**data)


@router.put("", response_model=AppSettingsResponse)
def update_settings(
    body: AppSettingsUpdate,
    _user: CurrentUser,
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> AppSettingsResponse:
    data = service.update_settings()
    return AppSettingsResponse(**data)
