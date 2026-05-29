"""Eligibility and scarcity DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

MatchType = Literal["direct", "substitution"]


@dataclass
class SkillMatchInfo:
    skill_id: int
    skill_name: str
    required_skill_id: int
    required_skill_name: str
    match_type: MatchType
    proficiency: int
    is_preferred: bool = False


@dataclass
class EligibilityResult:
    employee_id: int
    job_id: int
    eligible: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skill_matches: list[SkillMatchInfo] = field(default_factory=list)
    is_must_include: bool = False


@dataclass
class ScarceSkillInfo:
    skill_id: int
    skill_name: str
    available_count: int
    demanded_count: int
    employee_ids: list[int] = field(default_factory=list)

    @property
    def is_scarce(self) -> bool:
        return self.available_count < self.demanded_count
