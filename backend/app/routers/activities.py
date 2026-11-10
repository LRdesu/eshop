"""活动管理：
- 平台管理员(role==2)：创建/编辑/删除活动、查看报名店铺
- 商家(role==1)：查看活动列表、报名参加 / 退出报名（作用于自己店铺）
- 买家：查看进行中的活动（用于活动页展示）
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_platform_admin, get_admin_user, resolve_shop_id
from app.models import Activity, ActivityShop, Shop, User
from app.schemas import ActivityCreate, ActivityUpdate
from app.utils.response import ok, fail

router = APIRouter(prefix="/api/v1", tags=["activities"])


def _activity_dict(db: Session, a: Activity, shop_ids=None, for_merchant=False):
    """序列化活动；for_merchant 时额外标注该商家的报名状态。"""
    joined_ids = {r.shop_id for r in db.query(ActivityShop.shop_id).filter(
        ActivityShop.activity_id == a.id).all()}
    # 动态 status：按当前时间刷新未开始/进行中/已结束
    now = datetime.now()
    if now < a.start_at:
        status = 0
    elif now > a.end_at:
        status = 2
    else:
        status = 1
    item = {
        "id": a.id, "name": a.name, "type": a.type,
        "threshold": float(a.threshold), "value": float(a.value),
        "start_at": a.start_at.isoformat() if a.start_at else None,
        "end_at": a.end_at.isoformat() if a.end_at else None,
        "status": status, "description": a.description,
        "joined_shops": len(joined_ids),
    }
    if for_merchant and shop_ids is not None:
        item["joined"] = any(sid in joined_ids for sid in shop_ids)
    return item


# ---------------------------------------------------------------
# 商家：活动列表 + 报名/退出
# ---------------------------------------------------------------
@router.get("/admin/activities")
def list_for_admin(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    rows = db.query(Activity).order_by(Activity.id.desc()).all()
    return ok([_activity_dict(db, a, shop_ids, for_merchant=True) for a in rows])


@router.post("/admin/activities/{aid}/join")
def join_activity(aid: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    if (admin.role or 0) != 1:
        return fail("仅商家可报名参加活动")
    a = db.get(Activity, aid)
    if not a:
        return fail("活动不存在")
    now = datetime.now()
    if now > a.end_at:
        return fail("活动已结束")
    shop_ids = resolve_shop_id(admin, db)
    if not shop_ids or shop_ids == [-1]:
        return fail("您还没有店铺")
    for sid in shop_ids:
        exists = db.query(ActivityShop).filter(
            ActivityShop.activity_id == aid, ActivityShop.shop_id == sid).first()
        if not exists:
            db.add(ActivityShop(activity_id=aid, shop_id=sid))
    db.commit()
    return ok({"joined": True})


@router.post("/admin/activities/{aid}/quit")
def quit_activity(aid: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    shop_ids = resolve_shop_id(admin, db)
    if not shop_ids or shop_ids == [-1]:
        return fail("您还没有店铺")
    db.query(ActivityShop).filter(
        ActivityShop.activity_id == aid,
        ActivityShop.shop_id.in_(shop_ids),
    ).delete(synchronize_session=False)
    db.commit()
    return ok({"joined": False})


# ---------------------------------------------------------------
# 平台管理员：活动 CRUD
# ---------------------------------------------------------------
@router.get("/admin/activities/manage")
def list_manage(admin: User = Depends(get_platform_admin), db: Session = Depends(get_db)):
    rows = db.query(Activity).order_by(Activity.id.desc()).all()
    out = []
    for a in rows:
        item = _activity_dict(db, a)
        joined = db.query(ActivityShop).filter(ActivityShop.activity_id == a.id).all()
        shops = {s.id: s.name for s in db.query(Shop).filter(
            Shop.id.in_([j.shop_id for j in joined])).all()} if joined else {}
        item["shops"] = [{"shop_id": sid, "shop_name": shops.get(sid, "?")} for sid in
                         (j.shop_id for j in joined)]
        out.append(item)
    return ok(out)


@router.post("/admin/activities")
def create_activity(req: ActivityCreate, admin: User = Depends(get_platform_admin), db: Session = Depends(get_db)):
    if req.type not in ("FULL", "DISCOUNT"):
        return fail("活动类型仅支持 FULL(满减) / DISCOUNT(折扣)")
    a = Activity(
        name=req.name, type=req.type, threshold=req.threshold, value=req.value,
        start_at=req.start_at, end_at=req.end_at, description=req.description,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return ok(_activity_dict(db, a))


@router.put("/admin/activities/{aid}")
def update_activity(aid: int, req: ActivityUpdate, admin: User = Depends(get_platform_admin), db: Session = Depends(get_db)):
    a = db.get(Activity, aid)
    if not a:
        return fail("活动不存在")
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return ok(_activity_dict(db, a))


@router.delete("/admin/activities/{aid}")
def delete_activity(aid: int, admin: User = Depends(get_platform_admin), db: Session = Depends(get_db)):
    a = db.get(Activity, aid)
    if not a:
        return fail("活动不存在")
    db.query(ActivityShop).filter(ActivityShop.activity_id == aid).delete(synchronize_session=False)
    db.delete(a)
    db.commit()
    return ok({"deleted": aid})


# ---------------------------------------------------------------
# 买家：进行中的活动（活动会场）
# ---------------------------------------------------------------
@router.get("/activities")
def list_public(db: Session = Depends(get_db)):
    now = datetime.now()
    rows = db.query(Activity).filter(Activity.start_at <= now, Activity.end_at >= now).order_by(
        Activity.end_at.asc()).all()
    return ok([_activity_dict(db, a) for a in rows])
