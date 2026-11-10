from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import CartAdd, CartUpdate, CartItemResp
from app.services import cart_service
from app.utils.response import ok

router = APIRouter(prefix="/api/v1/cart", tags=["cart"])


@router.get("")
def list_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok([it.model_dump(mode="json") for it in cart_service.list_cart(db, user.id)])


@router.post("")
def add_cart(req: CartAdd, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = cart_service.add_cart(db, user.id, req.sku_id, req.quantity)
    return ok(CartItemResp.model_validate(item).model_dump(mode="json"))


@router.patch("/{item_id}")
def update_cart(item_id: int, req: CartUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = cart_service.update_cart(db, user.id, item_id, req.quantity)
    return ok(CartItemResp.model_validate(item).model_dump(mode="json"))


@router.delete("/{item_id}")
def remove_cart(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(cart_service.remove_cart(db, user.id, item_id))
