"""Employee API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmployeeLocationBase(BaseModel):
    label: str = Field(min_length=1, max_length=50)
    address: str = Field(min_length=1, max_length=500)
    latitude: float | None = None
    longitude: float | None = None
    is_primary: bool = False
    notes: str | None = None


class EmployeeLocationCreate(EmployeeLocationBase):
    pass


class EmployeeLocationUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=50)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    latitude: float | None = None
    longitude: float | None = None
    is_primary: bool | None = None
    notes: str | None = None


class EmployeeLocationResponse(EmployeeLocationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    created_at: datetime
    updated_at: datetime


class EmployeeSkillBase(BaseModel):
    skill_id: int
    proficiency: int = Field(ge=1, le=5)


class EmployeeSkillCreate(EmployeeSkillBase):
    pass


class EmployeeSkillUpdate(BaseModel):
    proficiency: int = Field(ge=1, le=5)


class EmployeeSkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    skill_id: int
    proficiency: int
    skill_name: str | None = None
    created_at: datetime
    updated_at: datetime


class EmployeeBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    display_name: str | None = Field(default=None, max_length=200)
    active: bool = True
    is_driver: bool = False
    is_supervisor: bool = False
    default_vehicle_capacity: int = Field(default=4, ge=1, le=20)
    phone: str | None = Field(default=None, max_length=30)
    notes: str | None = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    display_name: str | None = Field(default=None, max_length=200)
    active: bool | None = None
    is_driver: bool | None = None
    is_supervisor: bool | None = None
    default_vehicle_capacity: int | None = Field(default=None, ge=1, le=20)
    phone: str | None = Field(default=None, max_length=30)
    notes: str | None = None


class EmployeeResponse(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    locations: list[EmployeeLocationResponse] = []
    skills: list[EmployeeSkillResponse] = []


class EmployeeListItem(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
