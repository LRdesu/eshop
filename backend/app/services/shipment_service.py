"""履约服务：发货、物流轨迹推进、确认收货。

物流链路（演示约定）：
    仓库统一从【上海】发货，收货地址统一为【南京】。
    0 待发货 → 1 已发货 → 2 仓库拣货 → 3 已揽收 → 4 运输中(上海→南京) → 5 派送中 → 6 已签收
签收后订单进入「已签收(order_status=3)」，此时可申请售后。
"""
import random
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Shipment, ShipmentTrace, Order, Address
from app.schemas import ShipmentResp, TraceResp

# ---- 地理约定 ----
WAREHOUSE_CITY = "上海"      # 发货城市（仓库所在，统一上海）
WAREHOUSE_NAME = "上海中心仓"
DEFAULT_TO_CITY = "南京"     # 收货城市缺省值（收货地址统一南京）

# 0待发货 1已发货 2仓库拣货 3已揽收 4运输中 5派送中 6已签收
SHIP_STATUS_TEXT = ["待发货", "已发货", "仓库拣货", "已揽收", "运输中", "派送中", "已签收"]


def _gen_tracking_no():
    return "SF" + "".join(random.choice("0123456789") for _ in range(12))


def _stage_traces(status: int, carrier: str, from_city: str, to_city: str):
    """某个状态对应的轨迹节点（可多节点，用于表现跨城运输过程）。"""
    if status == 1:
        return [("已发货", from_city, f"商家已发货，{carrier}运单已生成，等待仓库处理")]
    if status == 2:
        return [("仓库拣货", from_city, f"【{WAREHOUSE_NAME}】已完成拣货打包，等待快递揽收")]
    if status == 3:
        return [("已揽收", from_city, f"【{from_city}】{carrier}已揽收")]
    if status == 4:
        return [
            ("运输中", from_city, f"快件已离开【{from_city}转运中心】，发往【{to_city}】"),
            ("运输中", to_city, f"快件已抵达【{to_city}转运中心】"),
        ]
    if status == 5:
        return [("派送中", to_city, f"【{to_city}】快递员正在派送，请保持电话畅通")]
    if status == 6:
        return [("已签收", to_city, f"【{to_city}】快件已签收，感谢使用")]
    return []


def _add_traces(db: Session, ship: Shipment, status: int, from_city: str, to_city: str, when: datetime):
    for node, city, desc in _stage_traces(status, ship.carrier or "", from_city, to_city):
        db.add(ShipmentTrace(
            shipment_id=ship.id, node=node, city=city, description=desc, occurred_at=when,
        ))


def ship(db: Session, order: Order, carrier: str, tracking_no: str = None) -> Shipment:
    """商家发货：生成运单，进入「已发货」，订单转为「已发货」。"""
    if order.pay_status != 1 or order.order_status != 1:
        raise HTTPException(400, "订单未支付或不可发货")
    existing = db.query(Shipment).filter(Shipment.order_id == order.id).first()
    if existing:
        raise HTTPException(400, "已发货")

    addr = db.get(Address, order.address_id)
    from_city = WAREHOUSE_CITY
    to_city = (addr.city if addr and addr.city else DEFAULT_TO_CITY)

    now = datetime.now()
    ship_obj = Shipment(
        order_id=order.id, carrier=carrier, tracking_no=tracking_no or _gen_tracking_no(),
        ship_status=1, from_city=from_city, to_city=to_city, shipped_at=now,
    )
    db.add(ship_obj)
    db.flush()
    _add_traces(db, ship_obj, 1, from_city, to_city, now)
    order.order_status = 2  # 已发货
    db.commit()
    db.refresh(ship_obj)
    return ship_obj


def advance(db: Session, shipment_id: int) -> Shipment:
    """推进一格物流：已发货→仓库拣货→已揽收→运输中→派送中→已签收。"""
    ship_obj = db.get(Shipment, shipment_id)
    if not ship_obj:
        raise HTTPException(404, "运单不存在")
    if ship_obj.ship_status >= 6:
        return ship_obj

    next_status = ship_obj.ship_status + 1
    from_city = ship_obj.from_city or WAREHOUSE_CITY
    to_city = ship_obj.to_city or DEFAULT_TO_CITY
    now = datetime.now()

    ship_obj.ship_status = next_status
    _add_traces(db, ship_obj, next_status, from_city, to_city, now)

    if next_status == 6:  # 已签收
        order = db.get(Order, ship_obj.order_id)
        if order:
            order.order_status = 3  # 已签收（可申请售后）
    db.commit()
    db.refresh(ship_obj)
    return ship_obj


def confirm_receive(db: Session, order: Order):
    if order.order_status < 3:
        raise HTTPException(400, "订单尚未签收")
    if order.order_status == 4:
        return order
    order.order_status = 4  # 已完成
    order.confirmed_at = datetime.now()
    db.commit()
    db.refresh(order)
    return order


def to_resp(db: Session, ship: Shipment) -> ShipmentResp:
    resp = ShipmentResp.model_validate(ship)
    resp.ship_status_text = SHIP_STATUS_TEXT[ship.ship_status] if 0 <= ship.ship_status < len(SHIP_STATUS_TEXT) else "未知"
    traces = db.query(ShipmentTrace).filter(
        ShipmentTrace.shipment_id == ship.id
    ).order_by(ShipmentTrace.id.asc()).all()
    resp.traces = [TraceResp.model_validate(t) for t in traces]
    return resp
