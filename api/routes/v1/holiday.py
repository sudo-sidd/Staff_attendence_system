from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.core.logs import audit
from api.deps import CurrentUser, Permission, require
from api.routes.models.holiday import AttendanceSettingsIn, AttendanceSettingsOut, HolidayIn, HolidayOut
from api.services import holidays as svc
from database.models import Holiday, User
from database.session import get_db

router = APIRouter(prefix="/holidays", tags=["holidays"])

DB = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require(Permission.holidays_manage))]


@router.get("", response_model=list[HolidayOut])
def list_holidays(db: DB, user: CurrentUser, year: int | None = None) -> list[Holiday]:
    """Any signed-in user: the staff portal shows the calendar too."""
    stmt = select(Holiday).order_by(Holiday.date)
    if year is not None:
        stmt = stmt.where(Holiday.date.between(f"{year}-01-01", f"{year}-12-31"))
    return list(db.scalars(stmt))


@router.post("", response_model=HolidayOut, status_code=status.HTTP_201_CREATED)
def create_holiday(body: HolidayIn, db: DB, actor: Admin) -> Holiday:
    holiday = Holiday(date=body.date, name=body.name)
    db.add(holiday)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A holiday is already set for this date")
    audit("holiday_created", actor_id=actor.id, date=str(body.date), holiday_name=body.name)
    return holiday


@router.get("/settings", response_model=AttendanceSettingsOut)
def get_holiday_settings(db: DB, user: CurrentUser) -> AttendanceSettingsOut:
    return AttendanceSettingsOut.model_validate(svc.get_settings_row(db))


@router.put("/settings", response_model=AttendanceSettingsOut)
def set_holiday_settings(body: AttendanceSettingsIn, db: DB, actor: Admin) -> AttendanceSettingsOut:
    row = svc.get_settings_row(db)
    row.sunday_holiday = body.sunday_holiday
    row.saturday_holiday = body.saturday_holiday
    db.commit()
    audit("holiday_settings_updated", actor_id=actor.id, sunday_holiday=body.sunday_holiday, saturday_holiday=body.saturday_holiday)
    return AttendanceSettingsOut.model_validate(row)


@router.put("/{holiday_id}", response_model=HolidayOut)
def update_holiday(holiday_id: int, body: HolidayIn, db: DB, actor: Admin) -> Holiday:
    holiday = db.get(Holiday, holiday_id)
    if holiday is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Holiday not found")
    holiday.date, holiday.name = body.date, body.name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A holiday is already set for this date")
    audit("holiday_updated", actor_id=actor.id, target_id=holiday_id, date=str(body.date), holiday_name=body.name)
    return holiday


@router.delete("/{holiday_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holiday(holiday_id: int, db: DB, actor: Admin) -> Response:
    holiday = db.get(Holiday, holiday_id)
    if holiday is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Holiday not found")
    db.delete(holiday)
    db.commit()
    audit("holiday_deleted", actor_id=actor.id, target_id=holiday_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
