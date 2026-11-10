from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.services import member_service
from app.utils.response import ok, fail

router = APIRouter(prefix="/api/v1/members", tags=["members"])


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(member_service.get_member(db, user.id).model_dump(mode="json"))


@router.get("/checkin/status")
def checkin_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(member_service.checkin_status(db, user.id))


@router.post("/checkin")
def checkin(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return ok(member_service.do_checkin(db, user.id))
    except HTTPException as e:
        return fail(e.detail)


@router.post("/rfm/refresh")
def refresh_rfm(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tag = member_service.refresh_rfm(db, user.id)
    return ok({
        "rfm_level": tag.rfm_level, "rfm_score": tag.rfm_score,
        "recency": tag.recency, "frequency": tag.frequency, "monetary": str(tag.monetary),
    })
