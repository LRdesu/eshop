"""商品收藏：列表 / 收藏或取消（toggle）/ 移除 / 访客态查询是否收藏。"""
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_user, get_optional_user_id
from app.models import User, Product, Sku, Favorite
from app.utils.response import ok, fail

router = APIRouter(prefix="/api/v1/favorites", tags=["favorites"])


class FavoriteReq(BaseModel):
    product_id: int


def _product_summary(db: Session, pid: int):
    p = db.get(Product, pid)
    if not p:
        return None
    min_price = db.query(func.min(Sku.price)).filter(Sku.product_id == pid).scalar()
    return {
        "id": p.id, "name": p.name, "cover": p.cover, "category": p.category,
        "shop_id": p.shop_id, "sales": p.sales,
        "price": float(min_price) if min_price is not None else None,
    }


@router.get("")
def my_favorites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = [f.product_id for f in
           db.query(Favorite).filter(Favorite.user_id == user.id).order_by(Favorite.id.desc()).all()]
    items = [s for s in (_product_summary(db, i) for i in ids) if s]
    return ok(items)


@router.get("/check")
def check(product_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    uid = get_optional_user_id(authorization)
    if not uid:
        return ok({"is_favorited": False})
    fav = db.query(Favorite).filter(Favorite.user_id == uid, Favorite.product_id == product_id).first()
    return ok({"is_favorited": bool(fav)})


@router.post("")
def toggle(req: FavoriteReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.get(Product, req.product_id):
        return fail("商品不存在")
    fav = db.query(Favorite).filter(Favorite.user_id == user.id, Favorite.product_id == req.product_id).first()
    if fav:
        db.delete(fav)
        db.commit()
        return ok({"favorited": False})
    db.add(Favorite(user_id=user.id, product_id=req.product_id))
    db.commit()
    return ok({"favorited": True})


@router.delete("/{product_id}")
def remove(product_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Favorite).filter(Favorite.user_id == user.id, Favorite.product_id == product_id).delete(
        synchronize_session=False)
    db.commit()
    return ok({"favorited": False})
