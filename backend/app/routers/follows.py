"""店铺关注：列表 / 关注或取消（toggle）/ 取消关注 / 访客态查询是否关注。"""
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_user, get_optional_user_id
from app.models import User, Shop, Follow
from app.schemas import ShopResp
from app.utils.response import ok, fail

router = APIRouter(prefix="/api/v1/follows", tags=["follows"])


class FollowReq(BaseModel):
    shop_id: int


@router.get("")
def my_follows(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Follow).filter(Follow.user_id == user.id).order_by(Follow.id.desc()).all()
    shops = []
    for f in rows:
        s = db.get(Shop, f.shop_id)
        if s:
            shops.append(ShopResp.model_validate(s).model_dump(mode="json"))
    return ok(shops)


@router.get("/check")
def check(shop_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    uid = get_optional_user_id(authorization)
    if not uid:
        return ok({"is_following": False})
    f = db.query(Follow).filter(Follow.user_id == uid, Follow.shop_id == shop_id).first()
    return ok({"is_following": bool(f)})


@router.post("")
def toggle(req: FollowReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    shop = db.get(Shop, req.shop_id)
    if not shop:
        return fail("店铺不存在")
    f = db.query(Follow).filter(Follow.user_id == user.id, Follow.shop_id == req.shop_id).first()
    if f:
        db.delete(f)
        db.commit()
        return ok({"following": False})
    db.add(Follow(user_id=user.id, shop_id=req.shop_id))
    db.commit()
    return ok({"following": True})


@router.delete("/{shop_id}")
def remove(shop_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Follow).filter(Follow.user_id == user.id, Follow.shop_id == shop_id).delete(
        synchronize_session=False)
    db.commit()
    return ok({"following": False})
