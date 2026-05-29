"""CSV export for dispatch runs."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models import (
    DispatchAssignment,
    DispatchRun,
    DispatchRunJob,
    DispatchRouteStop,
    DispatchVehicleRoute,
    Employee,
    ExportRecord,
    Job,
)
from app.services.exceptions import NotFoundError, ValidationError
from app.utils.display_dates import format_display_date, format_display_datetime

CSV_COLUMNS: list[str] = [
    "Date",
    "Job Name",
    "Client",
    "Address",
    "Arrival Time",
    "Driver",
    "Driver Phone",
    "Employee Name",
    "Google Maps Link",
    "Notes",
]


@dataclass
class ExportResult:
    export_record_id: int
    file_path: str
    row_count: int
    created_at: datetime


class ExportService:
    def __init__(self, db: Session, *, export_dir: Path | None = None) -> None:
        self._db = db
        self._export_dir = export_dir or get_settings().export_dir

    def export_dispatch_run_csv(self, dispatch_run_id: int) -> ExportResult:
        run = self._load_run(dispatch_run_id)
        if not run.vehicle_routes:
            raise ValidationError(
                "Dispatch run has no vehicle routes to export. Solve the run first."
            )

        rows = self._build_rows(run)
        if not rows:
            raise ValidationError("No export rows generated for this dispatch run.")

        file_path = self._write_csv(run, rows)
        record = ExportRecord(
            dispatch_run_id=run.id,
            export_type="csv",
            file_path=str(file_path),
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)

        return ExportResult(
            export_record_id=record.id,
            file_path=str(file_path),
            row_count=len(rows),
            created_at=record.created_at,
        )

    def _load_run(self, dispatch_run_id: int) -> DispatchRun:
        run = self._db.scalars(
            select(DispatchRun)
            .where(DispatchRun.id == dispatch_run_id)
            .options(
                selectinload(DispatchRun.jobs).selectinload(DispatchRunJob.job),
                selectinload(DispatchRun.assignments).selectinload(
                    DispatchAssignment.employee
                ),
                selectinload(DispatchRun.assignments).selectinload(DispatchAssignment.job),
                selectinload(DispatchRun.vehicle_routes).selectinload(
                    DispatchVehicleRoute.driver
                ),
                selectinload(DispatchRun.vehicle_routes).selectinload(
                    DispatchVehicleRoute.job
                ),
                selectinload(DispatchRun.vehicle_routes).selectinload(
                    DispatchVehicleRoute.stops
                ).selectinload(DispatchRouteStop.employee),
            )
        ).first()
        if run is None:
            raise NotFoundError("DispatchRun", dispatch_run_id)
        return run

    def _build_rows(self, run: DispatchRun) -> list[dict[str, str]]:
        assignments_by_employee = {a.employee_id: a for a in run.assignments}
        covered_employees: set[int] = set()
        rows: list[dict[str, str]] = []

        routes = sorted(run.vehicle_routes, key=lambda r: (r.job_id, r.route_order))
        for route in routes:
            job = route.job
            if job is None:
                continue
            driver = route.driver
            driver_name = _employee_name(driver) if driver else ""
            driver_phone = _driver_phone(driver)
            maps_link = route.google_maps_url or ""

            for stop in sorted(route.stops, key=lambda s: s.stop_order):
                if stop.stop_type not in ("driver_start", "pickup"):
                    continue
                employee_id = stop.employee_id or route.driver_employee_id
                assignment = assignments_by_employee.get(employee_id)
                employee = stop.employee or (assignment.employee if assignment else None)
                covered_employees.add(employee_id)
                rows.append(
                    _export_row(
                        run=run,
                        job=job,
                        driver_name=driver_name,
                        driver_phone=driver_phone,
                        employee_name=_employee_name(employee),
                        maps_link=maps_link,
                        notes=_notes_for_row(job, employee),
                    )
                )

        for assignment in run.assignments:
            if assignment.employee_id in covered_employees:
                continue
            job = assignment.job
            if job is None:
                continue
            rows.append(
                _export_row(
                    run=run,
                    job=job,
                    driver_name="",
                    driver_phone="",
                    employee_name=_employee_name(assignment.employee),
                    maps_link="",
                    notes=_notes_for_row(job, assignment.employee),
                )
            )

        return rows

    def _write_csv(self, run: DispatchRun, rows: list[dict[str, str]]) -> Path:
        self._export_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", run.name).strip("_").lower() or "run"
        filename = f"dispatch_run_{run.id}_{run.run_date.isoformat()}_{slug}.csv"
        file_path = self._export_dir / filename
        with file_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        return file_path


def _export_row(
    *,
    run: DispatchRun,
    job: Job,
    driver_name: str,
    driver_phone: str,
    employee_name: str,
    maps_link: str,
    notes: str,
) -> dict[str, str]:
    return {
        "Date": format_display_date(run.run_date),
        "Job Name": job.job_name or "",
        "Client": job.client_name or "",
        "Address": job.address,
        "Arrival Time": format_display_datetime(job.required_arrival_time),
        "Driver": driver_name,
        "Driver Phone": driver_phone,
        "Employee Name": employee_name,
        "Google Maps Link": maps_link,
        "Notes": notes,
    }


def _notes_for_row(job: Job, employee: Employee | None) -> str:
    parts: list[str] = []
    if job.notes and job.notes.strip():
        parts.append(job.notes.strip())
    if employee and employee.notes and employee.notes.strip():
        parts.append(employee.notes.strip())
    return " | ".join(parts)


def _employee_name(employee: Employee | None) -> str:
    if employee is None:
        return ""
    if employee.display_name:
        return employee.display_name
    return f"{employee.first_name} {employee.last_name}".strip()


def _driver_phone(driver: Employee | None) -> str:
    if driver is None or not driver.phone:
        return ""
    return driver.phone.strip()

