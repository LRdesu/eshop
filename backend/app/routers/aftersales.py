from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, AfterSale
from app.schemas import AfterSaleCreate, ReturnShipReq
from app.services import aftersale_service
from app.utils.response import ok

router = APIRouter(prefix="/api/v1/aftersales", tags=["aftersales"])


@router.post("")
def create(req: AfterSaleCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    as_obj = aftersale_service.create_aftersale(db, user.id, req)
    return ok(aftersale_service.as_to_dict(db, as_obj))


@router.get("")
def list_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = aftersale_service.list_aftersales(db, user.id)
    return ok([aftersale_service.as_to_dict(db, r) for r in rows])


@router.post("/{after_sale_id}/return-ship")
def return_ship(after_sale_id: int, req: ReturnShipReq,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """买家寄回退货：填写承运商与退货运单号，生成退货逆向物流。"""
    rs = aftersale_service.create_return_shipment(db, after_sale_id, req.carrier, req.tracking_no)
    return ok({
        "id": rs.id, "carrier": rs.carrier, "tracking_no": rs.tracking_no,
        "return_status": rs.return_status, "from_city": rs.from_city, "to_city": rs.to_city,
    })


@router.post("/return/{return_shipment_id}/advance")
def advance_return(return_shipment_id: int, db: Session = Depends(get_db)):
    """推进退货物流（买家或卖家均可演示推进），签收后自动退款/换货。"""
    rs = aftersale_service.advance_return(db, return_shipment_id)
    a = db.get(AfterSale, rs.after_sale_id)
    return ok(aftersale_service.as_to_dict(db, a))
