"""订单服务：结算预估价、锁库存、下单、优惠分摊。"""
import random
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Sku, Product, Order, OrderItem, Address, ShippingFee, UserCoupon, Shipment, User, PointsLog
from app.schemas import OrderPreviewResp, OrderResp, OrderItemResp, AddressResp, ShipSummary
from app.config import config
from app.utils.money import money, distribute_discount
from app.services import coupon_service, payment_service
from app.services.shipment_service import SHIP_STATUS_TEXT

# 演示用「本省」判定：仓库位于上海，故上海视为省内，其余（含南京）为省外
LOCAL_PROVINCE = "上海"

# 淘金币规则
POINTS_TO_YUAN = 100           # 100 淘金币 = 1 元
MAX_POINTS_RATIO = Decimal("0.03")  # 单笔最高抵订单金额的 3%


def _gen_order_no():
    return "E" + datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))


def _resolve_items(db: Session, req_items: list):
    """把请求里的 items 展开成带价格/分类/金额的结构，并校验库存。"""
    items = []
    for it in req_items:
        sku = db.get(Sku, it.sku_id)
        if not sku:
            raise HTTPException(404, f"SKU {it.sku_id} 不存在")
        if sku.stock < it.quantity:
            raise HTTPException(400, f"SKU {it.sku_id} 库存不足")
        prod = db.get(Product, sku.product_id)
        items.append({
            "sku_id": sku.id,
            "product_id": sku.product_id,
            "category": prod.category if prod else None,
            "spec": sku.spec,
            "product_name": prod.name if prod else None,
            "price": money(sku.price),
            "quantity": it.quantity,
            "amount": money(sku.price) * it.quantity,
        })
    return items


def _region_of(province: str) -> str:
    return "省内" if province == LOCAL_PROVINCE else "省外"


def _calc_points_discount(use_points: bool, user_points: int, payable: Decimal):
    """计算淘金币抵扣。返回 (points_used, points_discount)。
    - 100 币 = 1 元，用币数须为 100 的整数倍
    - 单笔抵扣上限 = payable(券后+运费) 的 3%
    """
    if not use_points or not payable or payable <= 0:
        return 0, Decimal("0")
    max_discount = (payable * MAX_POINTS_RATIO).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    # 用户币数能抵的金额上限
    affordable = Decimal(user_points) / Decimal(POINTS_TO_YUAN)
    discount = min(max_discount, affordable).quantize(Decimal("0.01"), rounding=ROUND_FLOOR)
    if discount <= 0:
        return 0, Decimal("0")
    # 用币数向下取整到 100 的整数倍（避免用小数币）
    points_used = int((discount * POINTS_TO_YUAN).to_integral_value(rounding=ROUND_FLOOR))
    points_used = (points_used // POINTS_TO_YUAN) * POINTS_TO_YUAN
    if points_used <= 0:
        return 0, Decimal("0")
    points_discount = Decimal(points_used) / Decimal(POINTS_TO_YUAN)
    return points_used, points_discount


def calc_shipping_fee(db: Session, province: str) -> Decimal:
    region = _region_of(province)
    sf = db.query(ShippingFee).filter(ShippingFee.region == region).first()
    return money(sf.fee) if sf else Decimal("0")


def _compute(db, user_id, req, lock_stock: bool):
    address = db.get(Address, req.address_id)
    if not address or address.user_id != user_id:
        raise HTTPException(400, "收货地址不存在")
    items = _resolve_items(db, req.items)
    goods_total = sum((it["amount"] for it in items), Decimal("0"))

    goods_discount, ship_discount = coupon_service.validate_chosen(
        db, user_id, req.coupon_id, req.shipping_coupon_id, items, goods_total,
        calc_shipping_fee(db, address.province),
    )
    region_fee = calc_shipping_fee(db, address.province)
    shipping_fee = max(region_fee - ship_discount, Decimal("0"))
    discount_amount = goods_discount
    payable_before_points = (goods_total - discount_amount + shipping_fee).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # 淘金币抵扣（100币=1元，上限3%）
    user = db.get(User, user_id)
    points_used, points_discount = _calc_points_discount(
        getattr(req, "use_points", False), (user.points or 0) if user else 0, payable_before_points
    )
    pay_amount = (payable_before_points - points_discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # 优惠分摊到每行（用于明细展示/退款口径）
    shares = distribute_discount(discount_amount, items)
    for it, sh in zip(items, shares):
        it["discount"] = sh
        it["pay"] = (it["amount"] - sh).quantize(Decimal("0.01"))

    preview_items = [{
        "sku_id": it["sku_id"], "product_id": it["product_id"], "spec": it["spec"],
        "product_name": it["product_name"], "price": it["price"], "quantity": it["quantity"],
        "goods_amount": it["amount"], "discount_amount": it["discount"], "pay_amount": it["pay"],
    } for it in items]

    goods_coupons, ship_coupons = coupon_service.list_available(
        db, user_id, items, goods_total, region_fee
    )

    return {
        "items": items, "goods_total": goods_total, "discount_amount": discount_amount,
        "points_used": points_used, "points_discount": points_discount,
        "points_available": (user.points or 0) if user else 0,
        "shipping_fee": shipping_fee, "pay_amount": pay_amount,
        "preview_items": preview_items, "goods_coupons": goods_coupons, "ship_coupons": ship_coupons,
        "address": address,
    }


def preview_order(db: Session, user_id: int, req):
    r = _compute(db, user_id, req, lock_stock=False)
    return OrderPreviewResp(
        goods_amount=r["goods_total"], discount_amount=r["discount_amount"],
        points_discount=r["points_discount"], points_used=r["points_used"],
        points_available=r["points_available"],
        shipping_fee=r["shipping_fee"], pay_amount=r["pay_amount"],
        items=r["preview_items"], available_coupons=r["goods_coupons"],
        available_shipping_coupons=r["ship_coupons"],
    )


def create_order(db: Session, user_id: int, req) -> Order:
    # 写路径触发：释放过期未付订单占用的库存（不再在读接口产生副作用）
    payment_service.close_expired(db)
    r = _compute(db, user_id, req, lock_stock=True)

    # 锁库存（下单即扣，超时关单回补）
    for it in r["items"]:
        sku = db.get(Sku, it["sku_id"])
        sku.stock -= it["quantity"]

    order = Order(
        order_no=_gen_order_no(), user_id=user_id, address_id=r["address"].id,
        goods_amount=r["goods_total"], discount_amount=r["discount_amount"],
        points_used=r["points_used"], points_discount=r["points_discount"],
        shipping_fee=r["shipping_fee"], pay_amount=r["pay_amount"],
        coupon_id=req.coupon_id, shipping_coupon_id=req.shipping_coupon_id,
        pay_status=0, order_status=0,
        expire_at=datetime.now() + timedelta(minutes=config.PAY_EXPIRE_MINUTES),
    )
    db.add(order)
    db.flush()
    # 淘金币：下单即扣，超时/取消关单时回补（与库存/券对称）
    if r["points_used"] > 0:
        buyer = db.get(User, user_id)
        buyer.points = max(0, (buyer.points or 0) - r["points_used"])
        db.add(PointsLog(user_id=user_id, point_delta=-r["points_used"], type="SPEND",
                         ref_order_no=order.order_no, remark=f"淘金币抵扣 {r['points_discount']} 元"))
    for it in r["items"]:
        oi = OrderItem(
            order_id=order.id, sku_id=it["sku_id"], product_id=it["product_id"],
            quantity=it["quantity"], price=it["price"], goods_amount=it["amount"],
            discount_amount=it["discount"], pay_amount=it["pay"],
        )
        db.add(oi)
    # 占用券
    for cid in (req.coupon_id, req.shipping_coupon_id):
        if cid:
            uc = db.get(UserCoupon, cid)
            if uc and uc.status == 0:
                uc.status = 1
                uc.order_id = order.id
                uc.used_at = datetime.now()
    db.commit()
    db.refresh(order)
    return order


def get_order(db: Session, user_id: int, order_id: int):
    order = db.get(Order, order_id)
    if not order or order.user_id != user_id:
        raise HTTPException(404, "订单不存在")
    return order


def list_orders(db: Session, user_id: int, status: int = None):
    q = db.query(Order).filter(Order.user_id == user_id)
    if status is not None:
        q = q.filter(Order.order_status == status)
    return q.order_by(Order.id.desc()).all()


def list_orders_paged(db: Session, user_id: int, status: int = None, page: int = 1, page_size: int = 20):
    q = db.query(Order).filter(Order.user_id == user_id)
    if status is not None:
        q = q.filter(Order.order_status == status)
    total = q.count()
    rows = q.order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return total, rows


def to_resp(db: Session, order: Order) -> OrderResp:
    resp = OrderResp.model_validate(order)
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    # 批量预取 SKU / Product，避免逐行 N+1（订单列表/详情的共性瓶颈）
    sku_ids = [oi.sku_id for oi in items]
    prod_ids = [oi.product_id for oi in items]
    skus = {s.id: s for s in db.query(Sku).filter(Sku.id.in_(sku_ids)).all()} if sku_ids else {}
    prods = {p.id: p for p in db.query(Product).filter(Product.id.in_(prod_ids)).all()} if prod_ids else {}
    oi_resps = []
    for oi in items:
        oir = OrderItemResp.model_validate(oi)
        sku = skus.get(oi.sku_id)
        prod = prods.get(oi.product_id)
        oir.sku_spec = sku.spec if sku else None
        oir.product_name = prod.name if prod else None
        oir.product_cover = prod.cover if prod else None
        oi_resps.append(oir)
    resp.items = oi_resps
    addr = db.get(Address, order.address_id)
    resp.address = AddressResp.model_validate(addr) if addr else None
    # 附带运单摘要：供订单列表/详情页判断能否「一键推进物流」
    ship = db.query(Shipment).filter(Shipment.order_id == order.id).first()
    if ship:
        resp.shipment = ShipSummary(
            id=ship.id, ship_status=ship.ship_status,
            ship_status_text=SHIP_STATUS_TEXT[ship.ship_status] if 0 <= ship.ship_status < len(SHIP_STATUS_TEXT) else "未知",
        )
    return resp
