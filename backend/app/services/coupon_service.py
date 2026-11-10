"""优惠券服务：可用性评估、叠加互斥、优惠额计算。

叠加互斥规则（确定性，杜绝组合歧义）：
  - 商品维度（FULL 满减 / DISCOUNT 折扣）：一个订单最多 1 张，二者互斥取其一
  - 运费维度（SHIPPING 运费券）：一个订单最多 1 张，可与商品券叠加
  - 即：商品券 <=1 张 + 运费券 <=1 张，跨维度可叠加，同维度绝不叠加
"""
from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Coupon, UserCoupon
from app.utils.money import money
from app.schemas import CouponResp, AvailableCoupon


def get_user_usable_coupons(db: Session, user_id: int):
    """返回用户持有的未使用且在有效期内的 (UserCoupon, Coupon) 列表。"""
    now = datetime.now()
    rows = (
        db.query(UserCoupon, Coupon)
        .join(Coupon, Coupon.id == UserCoupon.coupon_id)
        .filter(UserCoupon.user_id == user_id, UserCoupon.status == 0)
        .all()
    )
    out = []
    for uc, c in rows:
        if c.valid_from and now < c.valid_from:
            continue
        if c.valid_to and now > c.valid_to:
            continue
        out.append((uc, c))
    return out


def _scope_amount(coupon: Coupon, items: list) -> tuple:
    """返回券适用范围内的商品金额合计与是否命中范围。

    items: [{"product_id":int, "category":str, "amount":Decimal}]
    """
    if coupon.scope == "ALL":
        return sum((it["amount"] for it in items), Decimal("0")), True
    if coupon.scope == "CATEGORY":
        amt = sum((it["amount"] for it in items if it["category"] == coupon.scope_value), Decimal("0"))
        return amt, amt > 0
    if coupon.scope == "PRODUCT":
        ids = {int(x) for x in (coupon.scope_value or "").split(",") if x.strip()}
        amt = sum((it["amount"] for it in items if it["product_id"] in ids), Decimal("0"))
        return amt, amt > 0
    return Decimal("0"), False


def evaluate_coupon(coupon: Coupon, items: list, goods_total: Decimal, shipping_fee: Decimal):
    """评估单张券对当前订单的适用性，返回 (applicable, reason, discount, is_shipping)。"""
    scoped, hit = _scope_amount(coupon, items)
    if not hit:
        return False, "不适用范围", Decimal("0"), coupon.type == "SHIPPING"

    if coupon.type in ("FULL", "DISCOUNT"):
        if scoped < coupon.threshold:
            return False, f"未满门槛 {coupon.threshold}", Decimal("0"), False
        if coupon.type == "FULL":
            disc = money(min(coupon.value, scoped))
        else:  # DISCOUNT：value 为折扣率，如 0.9 表示打九折
            disc = money(scoped * (Decimal(1) - coupon.value))
        return True, None, disc, False

    if coupon.type == "SHIPPING":
        if goods_total < coupon.threshold:
            return False, f"未满门槛 {coupon.threshold}", Decimal("0"), True
        disc = money(min(coupon.value, shipping_fee))
        return True, None, disc, True

    return False, "未知券类型", Decimal("0"), False


def list_available(db: Session, user_id: int, items: list, goods_total: Decimal, shipping_fee: Decimal):
    """结算预估价用的可用券列表，分别给出商品券与运费券。"""
    usable = get_user_usable_coupons(db, user_id)
    goods_coupons, ship_coupons = [], []
    for uc, c in usable:
        applicable, reason, disc, is_ship = evaluate_coupon(c, items, goods_total, shipping_fee)
        ac = AvailableCoupon(
            user_coupon_id=uc.id,
            coupon=CouponResp.model_validate(c),
            applicable=applicable,
            reason=None if applicable else reason + (f"（可减 {disc}）" if disc > 0 else ""),
        )
        (ship_coupons if is_ship else goods_coupons).append(ac)
    return goods_coupons, ship_coupons


def validate_chosen(db: Session, user_id: int, coupon_id, shipping_coupon_id, items, goods_total, shipping_fee):
    """下单时校验所选券：类型正确、可用、计算优惠额。返回 (goods_discount, ship_discount)。"""
    goods_discount = Decimal("0")
    ship_discount = Decimal("0")
    usable = {(uc.id, c.type): (uc, c) for uc, c in get_user_usable_coupons(db, user_id)}

    if coupon_id:
        key = (coupon_id, None)
        # 先定位 user_coupon
        uc = db.get(UserCoupon, coupon_id)
        if not uc or uc.user_id != user_id or uc.status != 0:
            raise HTTPException(400, "优惠券不可用")
        c = db.get(Coupon, uc.coupon_id)
        if c.type not in ("FULL", "DISCOUNT"):
            raise HTTPException(400, "该券不是商品券")
        applicable, reason, disc, _ = evaluate_coupon(c, items, goods_total, shipping_fee)
        if not applicable:
            raise HTTPException(400, f"商品券不可用：{reason}")
        goods_discount = disc

    if shipping_coupon_id:
        uc = db.get(UserCoupon, shipping_coupon_id)
        if not uc or uc.user_id != user_id or uc.status != 0:
            raise HTTPException(400, "运费券不可用")
        c = db.get(Coupon, uc.coupon_id)
        if c.type != "SHIPPING":
            raise HTTPException(400, "该券不是运费券")
        applicable, reason, disc, _ = evaluate_coupon(c, items, goods_total, shipping_fee)
        if not applicable:
            raise HTTPException(400, f"运费券不可用：{reason}")
        ship_discount = disc

    return goods_discount, ship_discount
