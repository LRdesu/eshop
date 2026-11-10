from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_user
from app.models import User, Order
from app.services import payment_service, order_service
from app.schemas import PayReq, CallbackReq, PaymentCreateResp
from app.utils.response import ok, fail

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


class CreatePayReq(BaseModel):
    order_id: int
    channel: str = "BALANCE"


@router.post("")
def create_payment(req: CreatePayReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = order_service.get_order(db, user.id, req.order_id)
    pay = payment_service.create_payment(db, user.id, order, req.channel)
    return ok(PaymentCreateResp(payment_no=pay.payment_no, order_no=order.order_no,
                                amount=pay.amount, channel=pay.channel,
                                expire_at=pay.expire_at).model_dump(mode="json"))


@router.post("/{payment_no}/pay")
def pay(payment_no: str, req: PayReq, db: Session = Depends(get_db)):
    pay = payment_service.pay(db, payment_no, req.channel)
    return ok({"payment_no": pay.payment_no, "status": pay.status})


@router.post("/callback")
def callback(req: CallbackReq, db: Session = Depends(get_db)):
    # 异步回调：幂等（重复 SUCCESS 直接返回，不重复处理）
    pay = payment_service.callback(db, req.payment_no, req.status, req.trade_no)
    return ok({"payment_no": pay.payment_no, "status": pay.status})


@router.post("/cleanup")
def cleanup(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cnt = payment_service.close_expired(db)
    return ok({"closed": cnt})
