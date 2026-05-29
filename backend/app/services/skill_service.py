"""Skill catalog CRUD."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import EmployeeSkill, JobRequiredSkill, Skill
from app.schemas.skill import SkillCreate, SkillUpdate
from app.services.exceptions import ConflictError, NotFoundError


class SkillService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_skills(self, *, active_only: bool = False) -> list[Skill]:
        stmt = select(Skill).order_by(Skill.name)
        if active_only:
            stmt = stmt.where(Skill.active.is_(True))
        return list(self._db.scalars(stmt).all())

    def list_skills_with_usage(self, *, active_only: bool = False) -> list[dict]:
        skills = self.list_skills(active_only=active_only)
        job_counts = dict(
            self._db.execute(
                select(JobRequiredSkill.skill_id, func.count())
                .group_by(JobRequiredSkill.skill_id)
            ).all()
        )
        employee_counts = dict(
            self._db.execute(
                select(EmployeeSkill.skill_id, func.count()).group_by(EmployeeSkill.skill_id)
            ).all()
        )
        return [
            {
                "skill": skill,
                "job_usage_count": int(job_counts.get(skill.id, 0)),
                "employee_usage_count": int(employee_counts.get(skill.id, 0)),
            }
            for skill in skills
        ]

    def get_skill(self, skill_id: int) -> Skill:
        skill = self._db.get(Skill, skill_id)
        if skill is None:
            raise NotFoundError("Skill", skill_id)
        return skill

    def get_skill_by_name(self, name: str) -> Skill | None:
        return self._db.scalars(select(Skill).where(Skill.name == name)).first()

    def create_skill(self, data: SkillCreate) -> Skill:
        skill = Skill(name=data.name.strip(), active=data.active)
        self._db.add(skill)
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise ConflictError(f"Skill '{data.name}' already exists") from exc
        self._db.refresh(skill)
        return skill

    def update_skill(self, skill_id: int, data: SkillUpdate) -> Skill:
        skill = self.get_skill(skill_id)
        if data.name is not None:
            skill.name = data.name.strip()
        if data.active is not None:
            skill.active = data.active
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise ConflictError(f"Skill name '{data.name}' already exists") from exc
        self._db.refresh(skill)
        return skill
