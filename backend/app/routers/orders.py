from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import OrderPreviewReq, OrderCreateReq
from app.services import order_service, payment_service
from app.utils.response import ok

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("/preview")
def preview(req: OrderPreviewReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(order_service.preview_order(db, user.id, req).model_dump(mode="json"))


@router.post("")
def create(req: OrderCreateReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = order_service.create_order(db, user.id, req)
    return ok(order_service.to_resp(db, order).model_dump(mode="json"))


@router.get("")
def list_orders(status: int = None, page: int = 1, page_size: int = 20,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    page = max(int(page), 1)
    page_size = min(max(int(page_size), 1), 100)
    total, orders = order_service.list_orders_paged(db, user.id, status, page, page_size)
    return ok({
        "items": [order_service.to_resp(db, o).model_dump(mode="json") for o in orders],
        "total": total, "page": page, "page_size": page_size,
    })


@router.get("/{order_id}")
def detail(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = order_service.get_order(db, user.id, order_id)
    return ok(order_service.to_resp(db, order).model_dump(mode="json"))


@router.post("/{order_id}/confirm")
def confirm(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services import shipment_service
    order = order_service.get_order(db, user.id, order_id)
    shipment_service.confirm_receive(db, order)
    return ok(order_service.to_resp(db, order).model_dump(mode="json"))


@router.post("/{order_id}/cancel")
def cancel(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = order_service.get_order(db, user.id, order_id)
    if order.pay_status != 0:
        return ok(None, "仅未支付订单可取消")
    order.pay_status = 2
    order.order_status = 5
    payment_service._release_stock(db, order)
    payment_service._revert_coupons(db, order)
    payment_service._revert_points(db, order)
    db.commit()
    return ok(order_service.to_resp(db, order).model_dump(mode="json"))
