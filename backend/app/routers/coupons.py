"""面向买家的优惠券：浏览可用券 / 领取 / 我的券。

可用券规则：
- 传 shop_id：返回该店铺券 + 平台级券(shop_id 为 NULL)
- 不传 shop_id：仅返回平台级券
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, Coupon, UserCoupon, Shop
from app.schemas import CouponResp, UserCouponResp
from app.utils.response import ok, fail

router = APIRouter(prefix="/api/v1/coupons", tags=["coupons"])


@router.get("")
def list_coupons(shop_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Coupon).filter(Coupon.deleted == 0)
    if shop_id is not None:
        q = q.filter((Coupon.shop_id == shop_id) | (Coupon.shop_id.is_(None)))
    else:
        q = q.filter(Coupon.shop_id.is_(None))
    rows = q.order_by(Coupon.id.desc()).all()
    return ok([CouponResp.model_validate(c).model_dump(mode="json") for c in rows])


@router.get("/center")
def coupon_center(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """领券中心：展示全部可领券（平台券 + 店铺券），附店铺名与当前用户领取状态。"""
    now = datetime.now()
    coupons = db.query(Coupon).filter(Coupon.deleted == 0).order_by(Coupon.id.desc()).all()
    shop_ids = [c.shop_id for c in coupons if c.shop_id]
    shops = {s.id: s for s in db.query(Shop).filter(Shop.id.in_(shop_ids)).all()} if shop_ids else {}
    # 当前用户已领取的券（用于标记状态）
    held = db.query(UserCoupon.coupon_id, func.count(UserCoupon.id)).filter(
        UserCoupon.user_id == user.id
    ).group_by(UserCoupon.coupon_id).all()
    held_map = {cid: cnt for cid, cnt in held}
    # 各券总发放量（用于判断是否抢光）
    issued_rows = db.query(UserCoupon.coupon_id, func.count(UserCoupon.id)).group_by(
        UserCoupon.coupon_id).all()
    issued_map = {cid: cnt for cid, cnt in issued_rows}

    out = []
    for c in coupons:
        item = CouponResp.model_validate(c).model_dump(mode="json")
        item["shop_name"] = shops[c.shop_id].name if c.shop_id and c.shop_id in shops else "平台通用"
        item["my_count"] = held_map.get(c.id, 0)
        item["issued_count"] = issued_map.get(c.id, 0)
        item["remain"] = max(0, (c.total or 0) - issued_map.get(c.id, 0)) if (c.total or 0) > 0 else None
        # 是否可领：未达个人上限、未抢光、且在有效期内
        per_ok = item["my_count"] < (c.per_limit or 1)
        stock_ok = item["remain"] is None or item["remain"] > 0
        time_ok = (not c.valid_from or now >= c.valid_from) and (not c.valid_to or now <= c.valid_to)
        item["claimable"] = per_ok and stock_ok and time_ok
        out.append(item)
    return ok(out)


@router.get("/mine")
def my_coupons(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(UserCoupon).filter(UserCoupon.user_id == user.id).order_by(UserCoupon.id.desc()).all()
    out = []
    for u in rows:
        item = UserCouponResp.model_validate(u).model_dump(mode="json")
        c = db.get(Coupon, u.coupon_id)
        item["coupon"] = CouponResp.model_validate(c).model_dump(mode="json") if c else None
        out.append(item)
    return ok(out)


@router.post("/{cid}/claim")
def claim(cid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.get(Coupon, cid)
    if not c:
        return fail("优惠券不存在")
    if c.deleted:
        return fail("优惠券已下架，不可领取")
    held = db.query(func.count(UserCoupon.id)).filter(
        UserCoupon.user_id == user.id, UserCoupon.coupon_id == cid).scalar() or 0
    if held >= (c.per_limit or 1):
        return fail("您已领取，达到领取上限")
    issued = db.query(func.count(UserCoupon.id)).filter(UserCoupon.coupon_id == cid).scalar() or 0
    if (c.total or 0) > 0 and issued >= c.total:
        return fail("优惠券已被抢光")
    db.add(UserCoupon(user_id=user.id, coupon_id=cid, status=0))
    db.commit()
    return ok({"claimed": True})
