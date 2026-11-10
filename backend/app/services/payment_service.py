"""支付服务：生成支付单、幂等回调、超时关单、积分发放。"""
import random
from datetime import datetime
from decimal import ROUND_FLOOR
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Payment, Order, Sku, OrderItem, UserCoupon, PointsLog, User
from app.config import config
from app.utils.money import money


def _gen_payment_no():
    return "P" + datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))


def create_payment(db: Session, user_id: int, order: Order, channel: str) -> Payment:
    if order.pay_status != 0:
        raise HTTPException(400, "订单已支付或已关闭")
    pay = Payment(
        payment_no=_gen_payment_no(), order_id=order.id, user_id=user_id,
        channel=channel, amount=order.pay_amount, status=0, expire_at=order.expire_at,
    )
    db.add(pay)
    db.commit()
    db.refresh(pay)
    return pay


def _award_points(db: Session, user: User, order: Order):
    earned = int((order.pay_amount * config.POINTS_PER_YUAN).to_integral_value(rounding=ROUND_FLOOR))
    if earned > 0:
        user.points = (user.points or 0) + earned
        db.add(PointsLog(user_id=user.id, point_delta=earned, type="EARN",
                          ref_order_no=order.order_no, remark="消费获赠积分"))


def _mark_paid(db: Session, payment: Payment):
    """幂等：已成功直接返回；否则置成功并发货前置。"""
    if payment.status == 1:
        return payment  # 幂等：重复通知不重复处理
    if payment.status == 2:
        raise HTTPException(400, "支付单已关闭")
    now = datetime.now()
    payment.status = 1
    payment.paid_at = now
    order = db.get(Order, payment.order_id)
    order.pay_status = 1
    order.paid_at = now
    order.order_status = 1  # 待发货
    user = db.get(User, payment.user_id)
    _award_points(db, user, order)
    db.commit()
    db.refresh(payment)
    return payment


def pay(db: Session, payment_no: str, channel: str) -> Payment:
    """模拟收银台付款（直接成功）。"""
    pay = db.query(Payment).filter(Payment.payment_no == payment_no).first()
    if not pay:
        raise HTTPException(404, "支付单不存在")
    pay.channel = channel
    return _mark_paid(db, pay)


def callback(db: Session, payment_no: str, status: str, trade_no: str = None) -> Payment:
    """异步回调：幂等键 = payment_no + 目标状态。

    - 重复 SUCCESS：直接返回成功，不重复加积分/不重复发货
    - 已 SUCCESS 再收 FAIL：忽略（状态不可回退）
    """
    pay = db.query(Payment).filter(Payment.payment_no == payment_no).first()
    if not pay:
        raise HTTPException(404, "支付单不存在")
    if trade_no:
        pay.callback_data = f"trade_no={trade_no}"
    if status == "SUCCESS":
        return _mark_paid(db, pay)
    if status == "FAIL":
        if pay.status == 1:
            return pay  # 已支付，忽略失败回调
        _close_payment(db, pay)
        return pay
    raise HTTPException(400, "未知回调状态")


def _close_payment(db: Session, payment: Payment):
    """关单：支付单置关闭，订单取消，回补库存，退还券，回补金币。"""
    payment.status = 2
    order = db.get(Order, payment.order_id)
    if order and order.pay_status == 0:
        order.pay_status = 2
        order.order_status = 5
        _release_stock(db, order)
        _revert_coupons(db, order)
        _revert_points(db, order)
    db.commit()


def _release_stock(db: Session, order: Order):
    for oi in db.query(OrderItem).filter(OrderItem.order_id == order.id).all():
        sku = db.get(Sku, oi.sku_id)
        if sku:
            sku.stock += oi.quantity


def _revert_coupons(db: Session, order: Order):
    for uc in db.query(UserCoupon).filter(UserCoupon.order_id == order.id).all():
        uc.status = 0
        uc.order_id = None
        uc.used_at = None


def _revert_points(db: Session, order: Order):
    """关单/取消时回补下单扣减的淘金币。"""
    if not order.points_used or order.points_used <= 0:
        return
    user = db.get(User, order.user_id)
    if user:
        user.points = (user.points or 0) + order.points_used
        db.add(PointsLog(user_id=user.id, point_delta=order.points_used, type="REFUND",
                         ref_order_no=order.order_no, remark="订单取消/关闭回补淘金币"))


def close_expired(db: Session):
    """惰性关单：扫描未付且已过期的订单。返回关闭数量。"""
    now = datetime.now()
    expired = db.query(Order).filter(
        Order.pay_status == 0, Order.expire_at < now
    ).all()
    cnt = 0
    for order in expired:
        pay = db.query(Payment).filter(Payment.order_id == order.id).first()
        if pay:
            pay.status = 2
        order.pay_status = 2
        order.order_status = 5
        _release_stock(db, order)
        _revert_coupons(db, order)
        _revert_points(db, order)
        cnt += 1
    if cnt:
        db.commit()
    return cnt
