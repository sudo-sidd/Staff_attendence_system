from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

HolidayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class HolidayIn(BaseModel):
    date: date
    name: HolidayName


class HolidayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    name: str


class AttendanceSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sunday_holiday: bool
    saturday_holiday: bool


class AttendanceSettingsIn(BaseModel):
    sunday_holiday: bool
    saturday_holiday: bool
