"""售后服务：售后单、退货逆向物流、按分摊比例退款、逆向回补库存、积分回退。

退款口径（用户重点要求）：
  退款金额 = 该行实付 / 数量 * 退款数量（按实付分摊比例退，绝不以原价退）。

售后状态（AfterSale.status）：
  0 申请中 → 1 商家同意(待买家退货，仅 RETURN/EXCHANGE) → 2 买家已寄回(退货运输中)
            → 3 已完成(退款成功 / 换货重发) → 4 已拒绝
  REFUND(仅退款)：商家同意即直接退款 → 状态 0→3。

退货逆向物流（return_shipments.return_status，南京买家→上海仓库）：
  0 待寄回 → 1 已揽收 → 2 运输中 → 3 已签收(入库)
  —— 签收后 RETURN 自动退款、EXCHANGE 自动重发替换件。
"""
import random
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import (
    AfterSale, Order, OrderItem, Sku, Refund, PointsLog, User, Payment,
    ReturnShipment, ReturnTrace, Shipment,
)
from app.config import config
from app.utils.money import money
from app.schemas import AfterSaleResp

# 退货地址（仓库所在，统一上海）
RETURN_WAREHOUSE = "上海中心仓"
RETURN_TO_CITY = "上海"
RETURN_FROM_CITY = "南京"  # 买家寄出城市
RETURN_STATUS_TEXT = ["待寄回", "已揽收", "运输中", "已签收(入库)"]


def _gen_as_no():
    return "AS" + datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))


def _gen_tracking_no():
    return "SF" + "".join(random.choice("0123456789") for _ in range(12))


# ---------------------------------------------------------------
# 序列化为前端友好的 dict（含退货物流）
# ---------------------------------------------------------------
def as_to_dict(db: Session, a: AfterSale) -> dict:
    d = AfterSaleResp.model_validate(a).model_dump(mode="json")
    rs = db.query(ReturnShipment).filter(ReturnShipment.after_sale_id == a.id).first()
    if rs:
        traces = db.query(ReturnTrace).filter(
            ReturnTrace.return_shipment_id == rs.id
        ).order_by(ReturnTrace.id.asc()).all()
        d["return_shipment"] = {
            "id": rs.id, "carrier": rs.carrier, "tracking_no": rs.tracking_no,
            "return_status": rs.return_status,
            "return_status_text": RETURN_STATUS_TEXT[rs.return_status] if 0 <= rs.return_status < len(RETURN_STATUS_TEXT) else "未知",
            "from_city": rs.from_city, "to_city": rs.to_city,
            "traces": [{"node": t.node, "city": t.city, "description": t.description,
                        "occurred_at": t.occurred_at.isoformat() if t.occurred_at else None}
                       for t in traces],
        }
    else:
        d["return_shipment"] = None
    d["return_address"] = f"{RETURN_WAREHOUSE}（{RETURN_TO_CITY}）" if a.status in (1, 2) else None
    return d


# ---------------------------------------------------------------
# 创建售后申请
# ---------------------------------------------------------------
def create_aftersale(db: Session, user_id: int, req) -> AfterSale:
    order = db.get(Order, req.order_id)
    if not order or order.user_id != user_id:
        raise HTTPException(404, "订单不存在")
    if order.order_status < 3:
        raise HTTPException(400, "订单未完成，无法售后")
    oi = db.query(OrderItem).filter(
        OrderItem.order_id == req.order_id, OrderItem.sku_id == req.sku_id
    ).first()
    if not oi:
        raise HTTPException(400, "订单不含该商品")
    if req.quantity > oi.quantity:
        raise HTTPException(400, "售后数量超过购买数量")
    refund_amount = Decimal("0") if req.type == "EXCHANGE" else money(oi.pay_amount / oi.quantity * req.quantity)
    as_obj = AfterSale(
        as_no=_gen_as_no(), order_id=req.order_id, user_id=user_id, type=req.type,
        sku_id=req.sku_id, quantity=req.quantity, reason=req.reason,
        refund_amount=refund_amount, status=0,
    )
    db.add(as_obj)
    db.commit()
    db.refresh(as_obj)
    return as_obj


# ---------------------------------------------------------------
# 商家同意 / 拒绝
# ---------------------------------------------------------------
def approve(db: Session, after_sale_id: int) -> AfterSale:
    a = db.get(AfterSale, after_sale_id)
    if not a:
        raise HTTPException(404, "售后单不存在")
    if a.status != 0:
        raise HTTPException(400, "仅「申请中」的售后单可审核")
    if a.type == "REFUND":
        # 仅退款：同意即退款完成
        _do_refund(db, a)
    else:
        a.status = 1  # 待买家退货
    a.handled_at = datetime.now()
    db.commit()
    db.refresh(a)
    return a


def reject(db: Session, after_sale_id: int) -> AfterSale:
    a = db.get(AfterSale, after_sale_id)
    if not a:
        raise HTTPException(404, "售后单不存在")
    if a.status not in (0, 1):
        raise HTTPException(400, "该售后单状态不可拒绝")
    a.status = 4
    a.handled_at = datetime.now()
    db.commit()
    db.refresh(a)
    return a


# ---------------------------------------------------------------
# 买家寄回退货（生成退货逆向物流）
# ---------------------------------------------------------------
def create_return_shipment(db: Session, after_sale_id: int, carrier: str, tracking_no: str = None) -> ReturnShipment:
    a = db.get(AfterSale, after_sale_id)
    if not a:
        raise HTTPException(404, "售后单不存在")
    if a.status != 1:
        raise HTTPException(400, "当前状态不可寄回退货")
    if a.type == "REFUND":
        raise HTTPException(400, "仅退款无需寄回")
    existing = db.query(ReturnShipment).filter(ReturnShipment.after_sale_id == a.id).first()
    if existing:
        raise HTTPException(400, "已生成退货运单")
    now = datetime.now()
    rs = ReturnShipment(
        after_sale_id=a.id, carrier=carrier or "顺丰",
        tracking_no=tracking_no or _gen_tracking_no(),
        return_status=0, from_city=RETURN_FROM_CITY, to_city=RETURN_TO_CITY,
        shipped_at=now,
    )
    db.add(rs)
    db.flush()
    _add_return_trace(db, rs, 0, now)
    a.status = 2  # 买家已寄回
    db.commit()
    db.refresh(rs)
    return rs


def advance_return(db: Session, return_shipment_id: int) -> ReturnShipment:
    rs = db.get(ReturnShipment, return_shipment_id)
    if not rs:
        raise HTTPException(404, "退货运单不存在")
    if rs.return_status >= 3:
        return rs
    next_status = rs.return_status + 1
    now = datetime.now()
    rs.return_status = next_status
    _add_return_trace(db, rs, next_status, now)
    if next_status == 3:  # 已签收入库 → 结束退货，触发退款/换货
        rs.received_at = now
        a = db.get(AfterSale, rs.after_sale_id)
        if a.type == "RETURN":
            _do_refund(db, a)
        elif a.type == "EXCHANGE":
            _do_exchange(db, a)
        a.status = 3
        db.commit()
    else:
        db.commit()
    db.refresh(rs)
    return rs


# ---------------------------------------------------------------
# 退款 / 换货重发（内部）
# ---------------------------------------------------------------
def _do_refund(db: Session, a: AfterSale):
    """退款处理（内部）。
    - 退货(RETURN)/换货(EXCHANGE)：实物退回仓库，必须回补库存（与退款金额无关）。
    - 仅退款(REFUND)：无实物退回，不回补库存。
    - 退款金额 > 0 才生成退款流水并回退积分；EXCHANGE 退款额为 0 仅闭环不退款。
    """
    # 逆向回补库存：实物退回（RETURN/EXCHANGE）
    if a.type in ("RETURN", "EXCHANGE"):
        sku = db.get(Sku, a.sku_id)
        if sku:
            sku.stock += a.quantity  # 退回一件，库存 +quantity
    # 生成退款流水（仅退款金额为正）
    if a.refund_amount > 0:
        p = db.query(Payment).filter(Payment.order_id == a.order_id).first()
        refund = Refund(
            refund_no="RF" + datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999)),
            after_sale_id=a.id, payment_no=p.payment_no if p else None,
            user_id=a.user_id, amount=a.refund_amount,
            channel=p.channel if p else "BALANCE", status=1, reason=a.reason,
            finished_at=datetime.now(),
        )
        db.add(refund)
        revert = int((a.refund_amount * config.POINTS_PER_YUAN).to_integral_value(rounding=ROUND_FLOOR))
        if revert > 0:
            user = db.get(User, a.user_id)
            user.points = max(0, (user.points or 0) - revert)
            db.add(PointsLog(user_id=user.id, point_delta=-revert, type="REFUND",
                             ref_order_no=db.get(Order, a.order_id).order_no, remark="退款回退积分"))
        # 回补下单时消耗的淘金币（按退款占实付比例）
        order = db.get(Order, a.order_id)
        if order and order.points_used and order.points_used > 0 and order.pay_amount and order.pay_amount > 0:
            ratio = Decimal(a.refund_amount) / Decimal(order.pay_amount)
            back = int((Decimal(order.points_used) * ratio).to_integral_value(rounding=ROUND_FLOOR))
            if back > 0:
                user = db.get(User, a.user_id)
                user.points = (user.points or 0) + back
                db.add(PointsLog(user_id=user.id, point_delta=back, type="REFUND",
                                 ref_order_no=order.order_no, remark="退款回补淘金币抵扣"))
    a.status = 3


def _do_exchange(db: Session, a: AfterSale):
    """换货：买家退回后，商家重发替换件（新建一条正向物流）。
    库存口径：退回件先回库(+quantity)，替换件再发出(-quantity)，净零；无退款(refund_amount=0)。"""
    order = db.get(Order, a.order_id)
    sku = db.get(Sku, a.sku_id)
    # 退回件先回库
    if sku:
        sku.stock += a.quantity
    # 重发替换件，扣减库存（与退回件净零）
    ship = Shipment(
        order_id=order.id, kind="exchange", carrier="顺丰", tracking_no=_gen_tracking_no(),
        ship_status=1, from_city=RETURN_TO_CITY, to_city=RETURN_FROM_CITY, shipped_at=datetime.now(),
    )
    db.add(ship)
    if sku:
        sku.stock = max(0, sku.stock - a.quantity)


# ---------------------------------------------------------------
# 列表
# ---------------------------------------------------------------
def list_aftersales(db: Session, user_id: int):
    return db.query(AfterSale).filter(AfterSale.user_id == user_id).order_by(AfterSale.id.desc()).all()


def _add_return_trace(db: Session, rs: ReturnShipment, status: int, when: datetime):
    nodes = {
        0: ("待寄回", rs.from_city, f"买家已在【{rs.from_city}】发起退货，等待快递揽收"),
        1: ("已揽收", rs.from_city, f"【{rs.from_city}】{rs.carrier}已揽收退货包裹"),
        2: ("运输中", rs.to_city, f"退货包裹运输中，发往【{rs.to_city} {RETURN_WAREHOUSE}】"),
        3: ("已签收", rs.to_city, f"【{rs.to_city} {RETURN_WAREHOUSE}】已签收退货，退款/换货处理中"),
    }
    node, city, desc = nodes.get(status, ("未知", "", ""))
    db.add(ReturnTrace(return_shipment_id=rs.id, node=node, city=city, description=desc, occurred_at=when))
