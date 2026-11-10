from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import ReviewCreate, ReviewResp
from app.services import catalog_service
from app.utils.response import ok

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


@router.get("")
def list_reviews(sku_id: int = Query(None), product_id: int = Query(None), db: Session = Depends(get_db)):
    return ok([r.model_dump(mode="json") for r in catalog_service.list_reviews(db, sku_id, product_id)])


@router.post("")
def add_review(req: ReviewCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rev = catalog_service.add_review(db, user.id, req)
    return ok(ReviewResp.model_validate(rev).model_dump(mode="json"))
