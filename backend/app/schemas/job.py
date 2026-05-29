"""Job API schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class JobRequiredSkillBase(BaseModel):
    skill_id: int
    required_quantity: int = Field(default=1, ge=1)
    minimum_proficiency: int = Field(default=1, ge=1, le=5)
    is_preferred: bool = False


class JobRequiredSkillCreate(JobRequiredSkillBase):
    pass


class JobRequiredSkillResponse(JobRequiredSkillBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    skill_name: str | None = None
    created_at: datetime
    updated_at: datetime


class JobManualSubstitutionCreate(BaseModel):
    required_skill_id: int
    substitute_skill_id: int
    allowed: bool = True
    notes: str | None = None


class JobManualSubstitutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    required_skill_id: int
    substitute_skill_id: int
    required_skill_name: str | None = None
    substitute_skill_name: str | None = None
    allowed: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


class JobEmployeeRef(BaseModel):
    employee_id: int


class JobEmployeeLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    employee_id: int
    created_at: datetime


class JobBase(BaseModel):
    job_name: str | None = Field(default=None, max_length=200)
    client_name: str | None = Field(default=None, max_length=200)
    address: str = Field(min_length=1, max_length=500)
    latitude: float | None = None
    longitude: float | None = None
    required_arrival_time: datetime
    required_headcount: int = Field(default=1, ge=1)
    tolls_allowed: bool = True
    return_trip_enabled: bool = False
    dropoff_return_enabled: bool = False
    notes: str | None = None


class JobCreate(JobBase):
    pass


class JobDuplicateRequest(BaseModel):
    run_date: date | None = None
    job_name_suffix: str = " (copy)"


class JobUpdate(BaseModel):
    job_name: str | None = Field(default=None, max_length=200)
    client_name: str | None = Field(default=None, max_length=200)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    latitude: float | None = None
    longitude: float | None = None
    required_arrival_time: datetime | None = None
    required_headcount: int | None = Field(default=None, ge=1)
    tolls_allowed: bool | None = None
    return_trip_enabled: bool | None = None
    dropoff_return_enabled: bool | None = None
    notes: str | None = None


class JobResponse(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    required_skills: list[JobRequiredSkillResponse] = []
    manual_substitutions: list[JobManualSubstitutionResponse] = []
    included_employees: list[JobEmployeeLinkResponse] = []
    excluded_employees: list[JobEmployeeLinkResponse] = []


class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_name: str | None
    client_name: str | None
    address: str
    required_arrival_time: datetime
    required_headcount: int
    roles_summary: str = ""
    created_at: datetime
    updated_at: datetime
