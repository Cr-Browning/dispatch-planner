"""Skill endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.errors import raise_http_for_domain
from app.core.deps import CurrentUser, get_skill_service
from app.schemas.skill import SkillCreate, SkillResponse, SkillUpdate, SkillWithUsageResponse
from app.services.skill_service import SkillService

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillResponse] | list[SkillWithUsageResponse])
def list_skills(
    _user: CurrentUser,
    service: Annotated[SkillService, Depends(get_skill_service)],
    active_only: bool = Query(default=False),
    with_usage: bool = Query(default=False),
) -> list[SkillResponse] | list[SkillWithUsageResponse]:
    if with_usage:
        return [
            SkillWithUsageResponse(
                **SkillResponse.model_validate(row["skill"]).model_dump(),
                job_usage_count=row["job_usage_count"],
                employee_usage_count=row["employee_usage_count"],
            )
            for row in service.list_skills_with_usage(active_only=active_only)
        ]
    return [SkillResponse.model_validate(s) for s in service.list_skills(active_only=active_only)]


@router.post("", response_model=SkillResponse, status_code=201)
def create_skill(
    body: SkillCreate,
    _user: CurrentUser,
    service: Annotated[SkillService, Depends(get_skill_service)],
) -> SkillResponse:
    try:
        skill = service.create_skill(body)
    except Exception as exc:
        raise_http_for_domain(exc)
    return SkillResponse.model_validate(skill)


@router.put("/{skill_id}", response_model=SkillResponse)
def update_skill(
    skill_id: int,
    body: SkillUpdate,
    _user: CurrentUser,
    service: Annotated[SkillService, Depends(get_skill_service)],
) -> SkillResponse:
    try:
        skill = service.update_skill(skill_id, body)
    except Exception as exc:
        raise_http_for_domain(exc)
    return SkillResponse.model_validate(skill)
