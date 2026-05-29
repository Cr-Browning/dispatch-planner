"""Dispatch run CRUD and job attachment."""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import DispatchRun, DispatchRunJob, DispatchVehicleRoute, Job
from app.services.exceptions import NotFoundError, ValidationError
from app.utils.display_dates import format_display_date


class DispatchRunService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_run(
        self,
        *,
        run_date: date,
        name: str,
        job_ids: list[int],
        optimization_profile_id: int | None = None,
        employee_ids: list[int] | None = None,
    ) -> DispatchRun:
        settings: dict = {}
        if employee_ids:
            settings["employee_ids"] = employee_ids
        run = DispatchRun(
            run_date=run_date,
            name=name,
            optimization_profile_id=optimization_profile_id,
            status="draft",
            settings_json=json.dumps(settings) if settings else None,
        )
        self._db.add(run)
        self._db.flush()
        for job_id in job_ids:
            self._db.add(DispatchRunJob(dispatch_run_id=run.id, job_id=job_id))
        self._db.commit()
        return self.get_run(run.id)

    def get_run(self, dispatch_run_id: int) -> DispatchRun:
        run = self._db.scalars(
            select(DispatchRun)
            .where(DispatchRun.id == dispatch_run_id)
            .options(
                selectinload(DispatchRun.jobs),
                selectinload(DispatchRun.assignments),
                selectinload(DispatchRun.vehicle_routes).selectinload(
                    DispatchVehicleRoute.stops
                ),
            )
        ).first()
        if run is None:
            raise NotFoundError("DispatchRun", dispatch_run_id)
        return run

    def list_runs(self) -> list[DispatchRun]:
        return list(
            self._db.scalars(select(DispatchRun).order_by(DispatchRun.run_date.desc())).all()
        )

    def get_copy_template(
        self, *, target_run_date: date | None = None
    ) -> dict:
        """Job IDs and metadata from the most recent dispatch run (for duplicating a day)."""
        source = self._db.scalars(
            select(DispatchRun)
            .order_by(DispatchRun.run_date.desc(), DispatchRun.id.desc())
            .options(selectinload(DispatchRun.jobs))
            .limit(1)
        ).first()
        if source is None:
            raise ValidationError("No previous dispatch run to copy from")
        job_ids = [link.job_id for link in source.jobs]
        if not job_ids:
            raise ValidationError("Previous dispatch run has no jobs")
        suggested_date = target_run_date or date.today()
        jobs = list(
            self._db.scalars(select(Job).where(Job.id.in_(job_ids))).all()
        )
        on_date: list[int] = []
        off_date: list[int] = []
        for job in jobs:
            arrival = job.required_arrival_time
            arrival_day = arrival.date() if hasattr(arrival, "date") else suggested_date
            if arrival_day == suggested_date:
                on_date.append(job.id)
            else:
                off_date.append(job.id)
        return {
            "source_run_id": source.id,
            "source_run_name": source.name,
            "source_run_date": source.run_date,
            "job_ids": job_ids,
            "job_ids_on_run_date": on_date,
            "job_ids_off_run_date": off_date,
            "jobs_on_run_date_count": len(on_date),
            "suggested_run_date": suggested_date,
            "suggested_name": f"Dispatch — {format_display_date(suggested_date)}",
        }

