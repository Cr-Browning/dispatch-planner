"""CSV export schemas."""

from datetime import datetime

from pydantic import BaseModel


class ExportCsvResponse(BaseModel):
    dispatch_run_id: int
    export_record_id: int
    file_path: str
    row_count: int
    created_at: datetime
