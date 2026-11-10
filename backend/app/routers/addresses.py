from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, Address
from app.schemas import AddressCreate, AddressResp
from app.utils.response import ok

router = APIRouter(prefix="/api/v1/addresses", tags=["addresses"])


@router.get("")
def list_addresses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Address).filter(Address.user_id == user.id).order_by(Address.is_default.desc()).all()
    return ok([AddressResp.model_validate(r).model_dump(mode="json") for r in rows])


@router.post("")
def create_address(req: AddressCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if req.is_default == 1:
        for a in db.query(Address).filter(Address.user_id == user.id).all():
            a.is_default = 0
    addr = Address(user_id=user.id, **req.model_dump().items())
    db.add(addr)
    db.commit()
    db.refresh(addr)
    return ok(AddressResp.model_validate(addr).model_dump(mode="json"))
