"""商家后台接口：概览、商品/SKU 与库存、订单履约、售后审核、会员、优惠券、运费规则。

鉴权：
  - 除 /login 外，全部走 get_admin_user（role==1 商家 或 role==2 平台管理员）。
  - 商家(role==1)仅能操作「自己店铺」数据；平台管理员(role==2)看全部。
  - 运费规则为平台级，仅 role==2 可改。
"""
from decimal import Decimal
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_admin_user, get_platform_admin, resolve_shop_id
from app.models import (
    User, Product, Sku, Order, OrderItem, Shipment, ShipmentTrace,
    AfterSale, Coupon, UserCoupon, ShippingFee, UserTag, Review, Shop,
    ReturnShipment, ReturnTrace,
)
from app.schemas import (
    AdminLoginReq, AdminProductCreate, AdminProductUpdate, AdminSkuCreate, AdminSkuUpdate,
    AdminStockReq, AdminCouponCreate, AdminShippingFeeUpdate, AdminOrderShipReq,
    ShopStatusUpdate,
)
from app.utils.security import verify_password, create_token
from app.utils.response import ok, fail
from app.services import shipment_service, order_service, aftersale_service
from app.services.catalog_service import next_sku_code

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
LOW_STOCK = 10


# ---------------------------------------------------------------
# 按店铺隔离辅助
# ---------------------------------------------------------------
def _shop_product_ids(db: Session, shop_ids):
    if shop_ids is None:
        return None
    return [x[0] for x in db.query(Product.id).filter(Product.shop_id.in_(shop_ids)).all()]


def _shop_order_ids(db: Session, shop_ids):
    pids = _shop_product_ids(db, shop_ids)
    if pids is None:
        return None
    if not pids:
        return []
    return [x[0] for x in db.query(OrderItem.order_id).filter(
        OrderItem.product_id.in_(pids)).distinct().all()]


def _shop_sku_ids(db: Session, shop_ids):
    pids = _shop_product_ids(db, shop_ids)
    if pids is None:
        return None
    if not pids:
        return []
    return [s.id for s in db.query(Sku).filter(Sku.product_id.in_(pids)).all()]


def _check_product_shop(db: Session, pid: int, shop_ids):
    if shop_ids is None:
        return True
    p = db.get(Product, pid)
    return bool(p and p.shop_id in shop_ids)


# ---------------------------------------------------------------
# 登录
# ---------------------------------------------------------------
@router.post("/login")
def login(req: AdminLoginReq, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.username == req.username).first()
    if not u or not verify_password(req.password, u.password_hash):
        return fail("账号或密码错误")
    if (u.role or 0) not in (1, 2):
        return fail("该账号无商家后台权限")
    return ok({
        "token": create_token(u.id),
        "username": u.username,
        "nickname": u.nickname,
        "role": u.role,
    })


# ---------------------------------------------------------------
# 概览统计
# ---------------------------------------------------------------
@router.get("/stats")
def stats(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    pids = _shop_product_ids(db, shop_ids)
    oids = _shop_order_ids(db, shop_ids)
    sids = _shop_sku_ids(db, shop_ids)

    def oid_filter(q):
        if oids is None:
            return q
        return q.filter(Order.id.in_(oids)) if oids else q.filter(Order.id == -1)

    def sid_filter(q):
        if sids is None:
            return q
        return q.filter(AfterSale.sku_id.in_(sids)) if sids else q.filter(AfterSale.id == -1)

    def pid_filter(q):
        if pids is None:
            return q
        return q.filter(Product.id.in_(pids)) if pids else q.filter(Product.id == -1)

    paid_q = db.query(func.coalesce(func.sum(Order.pay_amount), 0)).filter(Order.pay_status == 1)
    paid_q = oid_filter(paid_q)
    paid = paid_q.scalar() or 0

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    t_order = oid_filter(db.query(Order)).filter(Order.created_at >= today).count()
    t_paid_q = db.query(func.coalesce(func.sum(Order.pay_amount), 0)).filter(
        Order.pay_status == 1, Order.created_at >= today)
    t_paid = oid_filter(t_paid_q).scalar() or 0

    def cnt(model, col, values, *conds):
        q = db.query(func.count(model.id))
        if values is not None:
            q = q.filter(col.in_(values)) if values else q.filter(model.id == -1)
        for c in conds:
            q = q.filter(c)
        return q.scalar() or 0

    return ok({
        "gmv": float(paid),
        "today_orders": int(t_order),
        "today_gmv": float(t_paid),
        "orders_total": int(cnt(Order, Order.id, oids)),
        "orders_wait_ship": int(cnt(Order, Order.id, oids, Order.order_status == 1)),
        "orders_shipped": int(cnt(Order, Order.id, oids, Order.order_status == 2)),
        "orders_signed": int(cnt(Order, Order.id, oids, Order.order_status == 3)),
        "orders_done": int(cnt(Order, Order.id, oids, Order.order_status == 4)),
        "orders_canceled": int(cnt(Order, Order.id, oids, Order.order_status == 5)),
        "aftersale_pending": int(cnt(AfterSale, AfterSale.id, sids, AfterSale.status == 0)),
        "aftersale_total": int(cnt(AfterSale, AfterSale.id, sids)),
        "products": int(cnt(Product, Product.id, pids)),
        "skus": int(cnt(Sku, Sku.id, pids)),
        "low_stock": int(cnt(Sku, Sku.id, pids, Sku.stock <= LOW_STOCK)),
        "members": int(cnt(User, User.id, None, User.role == 0)),
        "reviews": int(cnt(Review, Review.sku_id, sids)),
    })


# ---------------------------------------------------------------
# 商品 / SKU
# ---------------------------------------------------------------
def _sku_dict(s: Sku):
    return {
        "id": s.id, "sku_code": s.sku_code, "product_id": s.product_id, "spec": s.spec,
        "price": float(s.price), "stock": s.stock, "image": s.image,
    }


def _product_dict(db: Session, p: Product):
    skus = db.query(Sku).filter(Sku.product_id == p.id).all()
    return {
        "id": p.id, "name": p.name, "description": p.description, "category": p.category,
        "cover": p.cover, "gallery": p.gallery,
        "shop_id": p.shop_id,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "skus": [_sku_dict(s) for s in skus],
        "stock": sum(s.stock for s in skus),
    }


@router.get("/products")
def list_products(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    q = db.query(Product)
    if shop_ids is not None:
        q = q.filter(Product.shop_id.in_(shop_ids))
    rows = q.order_by(Product.id.desc()).all()
    return ok([_product_dict(db, p) for p in rows])


@router.post("/products")
def create_product(req: AdminProductCreate, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    p = Product(
        name=req.name, description=req.description, category=req.category,
        cover=req.cover, gallery=req.gallery,
        shop_id=shop_ids[0] if shop_ids else 1,  # 商家建商品归其名下首店；平台管理员归官方旗舰店
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return ok(_product_dict(db, p))


@router.put("/products/{pid}")
def update_product(pid: int, req: AdminProductUpdate, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    p = db.get(Product, pid)
    if not p:
        return fail("商品不存在")
    if shop_ids is not None and p.shop_id not in shop_ids:
        return fail("无权限操作该商品")
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return ok(_product_dict(db, p))


@router.delete("/products/{pid}")
def delete_product(pid: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    p = db.get(Product, pid)
    if not p:
        return fail("商品不存在")
    if shop_ids is not None and p.shop_id not in shop_ids:
        return fail("无权限操作该商品")
    sku_ids = [s.id for s in db.query(Sku).filter(Sku.product_id == pid).all()]
    if sku_ids:
        used = db.query(func.count(OrderItem.id)).filter(OrderItem.sku_id.in_(sku_ids)).scalar() or 0
        if used:
            return fail("该商品已产生订单，不能删除（可改为调整库存）")
        db.query(Sku).filter(Sku.product_id == pid).delete(synchronize_session=False)
    db.delete(p)
    db.commit()
    return ok({"deleted": pid})


@router.post("/products/{pid}/skus")
def add_sku(pid: int, req: AdminSkuCreate, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    if not _check_product_shop(db, pid, shop_ids):
        return fail("商品不存在或无权限")
    s = Sku(product_id=pid, spec=req.spec, price=req.price, stock=req.stock, image=req.image, sku_code=next_sku_code(db))
    db.add(s)
    db.commit()
    db.refresh(s)
    return ok(_sku_dict(s))


@router.put("/skus/{sid}")
def update_sku(sid: int, req: AdminSkuUpdate, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    s = db.get(Sku, sid)
    if not s:
        return fail("SKU 不存在")
    if not _check_product_shop(db, s.product_id, shop_ids):
        return fail("无权限操作该 SKU")
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return ok(_sku_dict(s))


@router.delete("/skus/{sid}")
def delete_sku(sid: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    s = db.get(Sku, sid)
    if not s:
        return fail("SKU 不存在")
    if not _check_product_shop(db, s.product_id, shop_ids):
        return fail("无权限操作该 SKU")
    used = db.query(func.count(OrderItem.id)).filter(OrderItem.sku_id == sid).scalar() or 0
    if used:
        return fail("该 SKU 已产生订单，不能删除")
    db.delete(s)
    db.commit()
    return ok({"deleted": sid})


@router.post("/skus/{sid}/stock")
def adjust_stock(sid: int, req: AdminStockReq, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    s = db.get(Sku, sid)
    if not s:
        return fail("SKU 不存在")
    if not _check_product_shop(db, s.product_id, shop_ids):
        return fail("无权限操作该 SKU")
    if req.stock < 0:
        return fail("库存不能为负")
    s.stock = req.stock
    db.commit()
    db.refresh(s)
    return ok(_sku_dict(s))


# ---------------------------------------------------------------
# 订单管理
# ---------------------------------------------------------------
@router.get("/orders")
def list_orders(
    status: int = Query(None),
    kw: str = Query(None),
    page: int = Query(1),
    page_size: int = Query(20),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    page = max(int(page), 1)
    page_size = min(max(int(page_size), 1), 100)
    shop_ids = resolve_shop_id(admin, db)
    oids = _shop_order_ids(db, shop_ids)
    q = db.query(Order)
    if oids is not None:
        q = q.filter(Order.id.in_(oids)) if oids else q.filter(Order.id == -1)
    if status is not None:
        q = q.filter(Order.order_status == status)
    if kw:
        like = f"%{kw}%"
        q = q.join(User, User.id == Order.user_id).filter(
            or_(Order.order_no.like(like), User.username.like(like), User.nickname.like(like))
        )
    total = q.count()
    rows = q.order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ok({
        "items": [order_service.to_resp(db, o).model_dump(mode="json") for o in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@router.get("/orders/{oid}")
def order_detail(oid: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    oids = _shop_order_ids(db, shop_ids)
    if oids is not None and (not oids or oid not in oids):
        return fail("无权限查看该订单")
    o = db.get(Order, oid)
    if not o:
        return fail("订单不存在")
    resp = order_service.to_resp(db, o).model_dump(mode="json")
    ship = db.query(Shipment).filter(Shipment.order_id == oid).first()
    resp["shipment_full"] = shipment_service.to_resp(db, ship).model_dump(mode="json") if ship else None
    return ok(resp)


@router.post("/orders/{oid}/ship")
def ship_order(oid: int, req: AdminOrderShipReq, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    oids = _shop_order_ids(db, shop_ids)
    if oids is not None and (not oids or oid not in oids):
        return fail("无权限操作该订单")
    o = db.get(Order, oid)
    if not o:
        return fail("订单不存在")
    try:
        ship = shipment_service.ship(db, o, req.carrier)
    except HTTPException as e:
        return fail(e.detail)
    return ok(shipment_service.to_resp(db, ship).model_dump(mode="json"))


@router.post("/orders/{oid}/advance")
def advance_order(oid: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    oids = _shop_order_ids(db, shop_ids)
    if oids is not None and (not oids or oid not in oids):
        return fail("无权限操作该订单")
    ship = db.query(Shipment).filter(Shipment.order_id == oid).first()
    if not ship:
        return fail("该订单尚未发货")
    ship = shipment_service.advance(db, ship.id)
    return ok(shipment_service.to_resp(db, ship).model_dump(mode="json"))


@router.post("/orders/{oid}/cancel")
def cancel_order(oid: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    oids = _shop_order_ids(db, shop_ids)
    if oids is not None and (not oids or oid not in oids):
        return fail("无权限操作该订单")
    o = db.get(Order, oid)
    if not o:
        return fail("订单不存在")
    if o.order_status in (4, 5):
        return fail("订单已完成或已取消")
    if o.order_status >= 3:
        return fail("已签收订单请走售后流程")
    for oi in db.query(OrderItem).filter(OrderItem.order_id == oid).all():
        sku = db.get(Sku, oi.sku_id)
        if sku:
            sku.stock += oi.quantity
    o.order_status = 5
    if o.pay_status == 0:
        o.pay_status = 2
    db.commit()
    return ok({"canceled": oid})


# ---------------------------------------------------------------
# 售后管理
# ---------------------------------------------------------------
AS_TEXT = ["申请中", "已同意", "退款中", "已完成", "已拒绝"]


def _as_dict(db: Session, a: AfterSale, sku_map=None, prod_map=None, order_map=None):
    o = order_map.get(a.order_id) if order_map is not None else db.get(Order, a.order_id)
    sku = sku_map.get(a.sku_id) if sku_map is not None else db.get(Sku, a.sku_id)
    if prod_map is not None:
        prod = prod_map.get(sku.product_id) if sku else None
    else:
        prod = db.get(Product, sku.product_id) if sku else None
    rs = db.query(ReturnShipment).filter(ReturnShipment.after_sale_id == a.id).first()
    ret = None
    if rs:
        traces = db.query(ReturnTrace).filter(ReturnTrace.return_shipment_id == rs.id).all()
        ret = {
            "id": rs.id, "carrier": rs.carrier, "tracking_no": rs.tracking_no,
            "return_status": rs.return_status, "from_city": rs.from_city, "to_city": rs.to_city,
            "traces": [{"node": t.node, "city": t.city, "description": t.description,
                        "occurred_at": t.occurred_at.isoformat() if t.occurred_at else None}
                       for t in traces],
        }
    return {
        "id": a.id, "as_no": a.as_no, "order_id": a.order_id,
        "order_no": o.order_no if o else None,
        "user_id": a.user_id, "type": a.type,
        "sku_id": a.sku_id, "sku_spec": sku.spec if sku else None,
        "product_name": prod.name if prod else None,
        "quantity": a.quantity, "reason": a.reason,
        "refund_amount": float(a.refund_amount), "status": a.status,
        "status_text": AS_TEXT[a.status] if 0 <= a.status < len(AS_TEXT) else "未知",
        "return_address": "上海中心仓（上海）" if a.status in (1, 2) else None,
        "return_shipment": ret,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/aftersales")
def list_aftersales(status: int = Query(None), page: int = Query(1), page_size: int = Query(20),
                    admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    page = max(int(page), 1)
    page_size = min(max(int(page_size), 1), 100)
    shop_ids = resolve_shop_id(admin, db)
    sids = _shop_sku_ids(db, shop_ids)
    q = db.query(AfterSale)
    if sids is not None:
        q = q.filter(AfterSale.sku_id.in_(sids)) if sids else q.filter(AfterSale.id == -1)
    if status is not None:
        q = q.filter(AfterSale.status == status)
    total = q.count()
    rows = q.order_by(AfterSale.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    sku_ids = [a.sku_id for a in rows]
    sku_map = {s.id: s for s in db.query(Sku).filter(Sku.id.in_(sku_ids)).all()} if sku_ids else {}
    prod_ids = [s.product_id for s in sku_map.values()]
    prod_map = {p.id: p for p in db.query(Product).filter(Product.id.in_(prod_ids)).all()} if prod_ids else {}
    order_ids = [a.order_id for a in rows]
    order_map = {o.id: o for o in db.query(Order).filter(Order.id.in_(order_ids)).all()} if order_ids else {}
    return ok({
        "items": [_as_dict(db, a, sku_map, prod_map, order_map) for a in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@router.post("/aftersales/{aid}/approve")
def approve(aid: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    a = db.get(AfterSale, aid)
    if not a:
        return fail("售后单不存在")
    sids = _shop_sku_ids(db, shop_ids)
    if sids is not None and (not sids or a.sku_id not in sids):
        return fail("无权限操作该售后单")
    try:
        a = aftersale_service.approve(db, aid)
    except HTTPException as e:
        return fail(e.detail)
    return ok(_as_dict(db, a))


@router.post("/aftersales/{aid}/reject")
def reject(aid: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    a = db.get(AfterSale, aid)
    if not a:
        return fail("售后单不存在")
    sids = _shop_sku_ids(db, shop_ids)
    if sids is not None and (not sids or a.sku_id not in sids):
        return fail("无权限操作该售后单")
    try:
        a = aftersale_service.reject(db, aid)
    except HTTPException as e:
        return fail(e.detail)
    return ok(_as_dict(db, a))


@router.post("/aftersales/{aid}/return-advance")
def return_advance(aid: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """商家推进退货物流（买家寄回→揽收→运输→签收），签收后系统自动退款/换货。"""
    shop_ids = resolve_shop_id(admin, db)
    a = db.get(AfterSale, aid)
    if not a:
        return fail("售后单不存在")
    sids = _shop_sku_ids(db, shop_ids)
    if sids is not None and (not sids or a.sku_id not in sids):
        return fail("无权限操作该售后单")
    rs = db.query(ReturnShipment).filter(ReturnShipment.after_sale_id == aid).first()
    if not rs:
        return fail("该售后单尚未生成退货运单")
    try:
        rs = aftersale_service.advance_return(db, rs.id)
    except HTTPException as e:
        return fail(e.detail)
    a = db.get(AfterSale, aid)
    return ok(_as_dict(db, a))


# ---------------------------------------------------------------
# 会员管理（平台级，全量买家）
# ---------------------------------------------------------------
@router.get("/users")
def list_users(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    rows = db.query(User).filter(User.role == 0).order_by(User.id.desc()).all()
    out = []
    for u in rows:
        tag = db.query(UserTag).filter(UserTag.user_id == u.id).first()
        cnt_o = db.query(func.count(Order.id)).filter(Order.user_id == u.id).scalar() or 0
        spent = db.query(func.coalesce(func.sum(Order.pay_amount), 0)).filter(
            Order.user_id == u.id, Order.pay_status == 1
        ).scalar() or 0
        out.append({
            "id": u.id, "username": u.username, "nickname": u.nickname, "phone": u.phone,
            "points": u.points, "order_count": int(cnt_o), "spent": float(spent),
            "rfm_level": tag.rfm_level if tag else None,
            "rfm_score": tag.rfm_score if tag else None,
            "tags": tag.tags if tag else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })
    return ok(out)


@router.get("/users/{uid}")
def user_detail(uid: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        return fail("用户不存在")
    tag = db.query(UserTag).filter(UserTag.user_id == uid).first()
    orders = db.query(Order).filter(Order.user_id == uid).order_by(Order.id.desc()).limit(50).all()
    return ok({
        "user": {
            "id": u.id, "username": u.username, "nickname": u.nickname,
            "phone": u.phone, "points": u.points,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        },
        "rfm": {
            "rfm_level": tag.rfm_level if tag else None,
            "rfm_score": tag.rfm_score if tag else None,
            "recency": tag.recency if tag else None,
            "frequency": tag.frequency if tag else None,
            "monetary": float(tag.monetary) if tag and tag.monetary is not None else None,
            "tags": tag.tags if tag else None,
        },
        "orders": [order_service.to_resp(db, o).model_dump(mode="json") for o in orders],
    })


# ---------------------------------------------------------------
# 优惠券管理（按店铺隔离）
# ---------------------------------------------------------------
@router.get("/coupons")
def list_coupons(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    q = db.query(Coupon).filter(Coupon.deleted == 0)
    if shop_ids is not None:
        q = q.filter(Coupon.shop_id.in_(shop_ids))
    rows = q.order_by(Coupon.id.desc()).all()
    out = []
    for c in rows:
        given = db.query(func.count(UserCoupon.id)).filter(UserCoupon.coupon_id == c.id).scalar() or 0
        used = db.query(func.count(UserCoupon.id)).filter(
            UserCoupon.coupon_id == c.id, UserCoupon.status == 1
        ).scalar() or 0
        out.append({
            "id": c.id, "shop_id": c.shop_id, "name": c.name, "type": c.type,
            "is_platform": c.shop_id is None,
            "threshold": float(c.threshold), "value": float(c.value),
            "scope": c.scope, "scope_value": c.scope_value,
            "valid_from": c.valid_from.isoformat() if c.valid_from else None,
            "valid_to": c.valid_to.isoformat() if c.valid_to else None,
            "total": c.total, "per_limit": c.per_limit,
            "given": int(given), "used": int(used),
        })
    return ok(out)


@router.post("/coupons")
def create_coupon(req: AdminCouponCreate, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """发券权限：平台管理员(role==2)可发平台券(shop_id=NULL)；
    商家(role==1)只能发「自己店铺券」(shop_id 强制=自己的店)，
    且 scope 仅限 ALL 或 PRODUCT(本店商品)，禁止平台券与跨店券(CATEGORY/跨店)。"""
    shop_ids = resolve_shop_id(admin, db)
    if (admin.role or 0) == 2:
        # 平台管理员：发平台券（shop_id=NULL）
        shop_id = None
    else:
        # 商家：只能发自己店铺券
        if not shop_ids or shop_ids == [-1]:
            return fail("您还没有店铺，无法发券")
        shop_id = shop_ids[0]
        # 商家禁止跨店/平台范围
        if req.scope == "CATEGORY":
            return fail("商家不可发布跨店券（分类范围），仅平台可发")
        if req.scope == "PRODUCT":
            # 校验 scope_value 里的商品都属于本店
            ids = [int(x) for x in (req.scope_value or "").split(",") if x.strip()]
            if ids:
                owned = {p.id for p in db.query(Product.id).filter(
                    Product.id.in_(ids), Product.shop_id.in_(shop_ids)).all()}
                if len(owned) != len(ids):
                    return fail("指定商品中存在非本店商品，商家不可跨店发券")
    c = Coupon(
        shop_id=shop_id,
        name=req.name, type=req.type, threshold=req.threshold, value=req.value,
        scope=req.scope, scope_value=req.scope_value,
        valid_from=req.valid_from or datetime.now(),
        valid_to=req.valid_to or (datetime.now() + timedelta(days=30)),
        total=req.total, per_limit=req.per_limit,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return ok({"id": c.id, "shop_id": c.shop_id, "name": c.name})


@router.post("/coupons/{cid}/grant")
def grant_coupon(cid: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    c = db.get(Coupon, cid)
    if not c:
        return fail("优惠券不存在")
    if c.deleted:
        return fail("该券已下架，不可发放")
    if shop_ids is not None and c.shop_id not in shop_ids:
        return fail("无权限操作该券")
    users = db.query(User).filter(User.role == 0).all()
    n = 0
    for u in users:
        holding = db.query(func.count(UserCoupon.id)).filter(
            UserCoupon.user_id == u.id, UserCoupon.coupon_id == cid
        ).scalar() or 0
        if holding >= (c.per_limit or 1):
            continue
        db.add(UserCoupon(user_id=u.id, coupon_id=cid, status=0))
        n += 1
    db.commit()
    return ok({"granted": n})


@router.delete("/coupons/{cid}")
def delete_coupon(cid: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """下架优惠券（软删除）：仅标记 deleted=1，券从领券中心/商家列表移除、不可再新领，
    但已领取的 user_coupons 与 coupons 行全部保留，已领买家不受影响、仍可使用。"""
    shop_ids = resolve_shop_id(admin, db)
    c = db.get(Coupon, cid)
    if not c:
        return fail("优惠券不存在")
    if shop_ids is not None and c.shop_id not in shop_ids:
        return fail("无权限操作该券")
    if c.deleted:
        return fail("该券已下架")
    c.deleted = 1
    db.commit()
    return ok({"deleted": cid})


# ---------------------------------------------------------------
# 运费规则（平台级，仅平台管理员）
# ---------------------------------------------------------------
@router.get("/shipping-fees")
def list_fees(admin: User = Depends(get_platform_admin), db: Session = Depends(get_db)):
    rows = db.query(ShippingFee).all()
    return ok([{"id": r.id, "region": r.region, "fee": float(r.fee)} for r in rows])


@router.put("/shipping-fees/{fid}")
def update_fee(fid: int, req: AdminShippingFeeUpdate, admin: User = Depends(get_platform_admin), db: Session = Depends(get_db)):
    r = db.get(ShippingFee, fid)
    if not r:
        return fail("运费规则不存在")
    r.fee = req.fee
    db.commit()
    return ok({"id": r.id, "region": r.region, "fee": float(r.fee)})


# ---------------------------------------------------------------
# 店铺权限管理（平台级，仅平台管理员）
# ---------------------------------------------------------------
@router.get("/shops")
def list_all_shops(admin: User = Depends(get_platform_admin), db: Session = Depends(get_db)):
    rows = db.query(Shop).order_by(Shop.id.asc()).all()
    out = []
    for s in rows:
        owner = db.get(User, s.owner_user_id) if s.owner_user_id else None
        out.append({
            "id": s.id, "name": s.name, "logo": s.logo,
            "status": s.status, "rating": float(s.rating),
            "owner_user_id": s.owner_user_id,
            "owner_name": owner.username if owner else None,
        })
    return ok(out)


@router.put("/shops/{sid}/status")
def set_shop_status(sid: int, req: ShopStatusUpdate, admin: User = Depends(get_platform_admin), db: Session = Depends(get_db)):
    s = db.get(Shop, sid)
    if not s:
        return fail("店铺不存在")
    if req.status not in (0, 1):
        return fail("状态值非法（0休息 / 1营业）")
    s.status = req.status
    db.commit()
    return ok({"id": s.id, "status": s.status})
