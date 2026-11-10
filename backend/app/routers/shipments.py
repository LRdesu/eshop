from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, Order, Shipment
from app.services import shipment_service, order_service
from app.schemas import ShipReq
from app.utils.response import ok

router = APIRouter(prefix="/api/v1/shipments", tags=["shipments"])


@router.post("/{order_id}/ship")
def ship(order_id: int, req: ShipReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = order_service.get_order(db, user.id, order_id)
    ship = shipment_service.ship(db, order, req.carrier, req.tracking_no)
    return ok(shipment_service.to_resp(db, ship).model_dump(mode="json"))


@router.post("/{shipment_id}/advance")
def advance(shipment_id: int, db: Session = Depends(get_db)):
    ship = shipment_service.advance(db, shipment_id)
    return ok(shipment_service.to_resp(db, ship).model_dump(mode="json"))


@router.get("/order/{order_id}")
def by_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = order_service.get_order(db, user.id, order_id)
    ship = db.query(Shipment).filter(Shipment.order_id == order.id).first()
    if not ship:
        return ok(None)
    return ok(shipment_service.to_resp(db, ship).model_dump(mode="json"))


@router.get("/{shipment_id}/traces")
def traces(shipment_id: int, db: Session = Depends(get_db)):
    ship = db.get(Shipment, shipment_id)
    if not ship:
        return ok(None)
    return ok(shipment_service.to_resp(db, ship).model_dump(mode="json"))
