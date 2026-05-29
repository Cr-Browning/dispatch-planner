"""Pre-solve checks for dispatch planner selections."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Employee, Job, JobRequiredSkill
from app.services.exceptions import NotFoundError
from app.utils.display_dates import format_display_date


class DispatchValidationService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def validate_selection(self, *, run_date: date, job_ids: list[int]) -> dict:
        issues: list[dict[str, str]] = []

        if not job_ids:
            issues.append(
                {
                    "level": "error",
                    "message": "Select at least one job before solving.",
                }
            )
            return {"ready": False, "issues": issues}

        if len(job_ids) < 2:
            issues.append(
                {
                    "level": "warning",
                    "message": "Only one job selected — multi-job routing will not apply.",
                }
            )

        jobs = list(
            self._db.scalars(
                select(Job)
                .where(Job.id.in_(job_ids))
                .options(selectinload(Job.required_skills))
            ).all()
        )
        found_ids = {job.id for job in jobs}
        missing = [jid for jid in job_ids if jid not in found_ids]
        if missing:
            raise NotFoundError("Job", missing[0])

        driver_count = self._db.scalar(
            select(func.count())
            .select_from(Employee)
            .where(Employee.active.is_(True), Employee.is_driver.is_(True))
        )
        if not driver_count:
            issues.append(
                {
                    "level": "error",
                    "message": "No active drivers — add or activate a driver employee.",
                }
            )

        active_workers = self._db.scalar(
            select(func.count()).select_from(Employee).where(Employee.active.is_(True))
        )
        if not active_workers:
            issues.append(
                {
                    "level": "error",
                    "message": "No active employees available for assignment.",
                }
            )

        total_headcount = 0
        for job in jobs:
            total_headcount += job.required_headcount
            label = job.job_name or f"Job {job.id}"
            if not job.required_skills:
                issues.append(
                    {
                        "level": "error",
                        "message": f"{label} has no required roles.",
                    }
                )
            if job.latitude is None or job.longitude is None:
                issues.append(
                    {
                        "level": "warning",
                        "message": f"{label} is missing map coordinates (geocode may have failed).",
                    }
                )
            arrival_day = (
                job.required_arrival_time.date()
                if hasattr(job.required_arrival_time, "date")
                else run_date
            )
            if arrival_day != run_date:
                issues.append(
                    {
                        "level": "warning",
                        "message": (
                            f"{label} is scheduled for {format_display_date(arrival_day)}, "
                            "not this run date."
                        ),
                    }
                )

        if active_workers and total_headcount > int(active_workers):
            issues.append(
                {
                    "level": "warning",
                    "message": (
                        f"Selected jobs need {total_headcount} workers but only "
                        f"{active_workers} active employees exist."
                    ),
                }
            )

        ready = not any(issue["level"] == "error" for issue in issues)
        return {"ready": ready, "issues": issues}
