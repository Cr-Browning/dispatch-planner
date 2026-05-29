"""Settings API schemas."""

from pydantic import BaseModel


class AppSettingsResponse(BaseModel):
    routing_provider: str
    export_columns: list[str]


class AppSettingsUpdate(BaseModel):
    pass
