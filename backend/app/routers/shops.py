from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Shop, Product, Follow
from app.schemas import ShopResp
from app.services import catalog_service
from app.utils.response import ok, fail

router = APIRouter(prefix="/api/v1/shops", tags=["shops"])


@router.get("")
def list_shops(keyword: str = None, db: Session = Depends(get_db)):
    q = db.query(Shop).filter(Shop.status == 1)
    if keyword:
        q = q.filter(Shop.name.like(f"%{keyword}%"))
    shops = q.order_by(Shop.id).all()
    return ok([ShopResp.model_validate(s).model_dump(mode="json") for s in shops])


@router.get("/{shop_id}")
def shop_detail(shop_id: int, db: Session = Depends(get_db)):
    shop = db.get(Shop, shop_id)
    if not shop:
        return fail("店铺不存在")
    cnt = db.query(Product).filter(Product.shop_id == shop_id).count()
    followers = db.query(func.count(Follow.id)).filter(Follow.shop_id == shop_id).scalar() or 0
    data = ShopResp.model_validate(shop).model_dump(mode="json")
    data["product_count"] = cnt
    data["follower_count"] = int(followers)
    return ok(data)


@router.get("/{shop_id}/products")
def shop_products(
    shop_id: int,
    keyword: str = None,
    category_id: int = None,
    sort: str = "default",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    return ok(catalog_service.list_products(
        db, keyword=keyword, category_id=category_id,
        shop_id=shop_id, sort=sort, page=page, page_size=page_size
    ))
