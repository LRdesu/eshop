"""商品 / SKU / 评价 / 类目 / 首页 服务。"""
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from datetime import datetime

from app.models import Product, Sku, Review, Order, OrderItem, Shop, Category
from app.schemas import ProductResp, ReviewResp, SkuResp, CategoryResp

MAX_PAGE_SIZE = 100


def next_sku_code(db: Session) -> int:
    """生成下一个独立且唯一的 5 位 SKU 编码（10000-99999）。"""
    mx = db.query(func.max(Sku.sku_code)).scalar()
    nxt = (mx or 9999) + 1
    if nxt > 99999:
        used = {r[0] for r in db.query(Sku.sku_code).all()}
        nxt = next((c for c in range(10000, 100000) if c not in used), None)
        if nxt is None:
            raise RuntimeError("SKU 编码已用尽（超过 99999）")
    return nxt


def db_query_min_price():
    # 商品最低 SKU 价，用于价格排序（关联子查询）
    return (
        select(func.min(Sku.price))
        .where(Sku.product_id == Product.id)
        .correlate(Product)
        .scalar_subquery()
    )


def list_products(
    db: Session,
    keyword: str = None,
    category: str = None,
    category_id: int = None,
    shop_id: int = None,
    sort: str = "default",
    page: int = 1,
    page_size: int = 20,
):
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), MAX_PAGE_SIZE))
    q = db.query(Product)
    if shop_id:
        q = q.filter(Product.shop_id == shop_id)
    if category_id:
        q = q.filter(Product.category_id == category_id)
    elif category:
        q = q.filter(Product.category == category)
    if keyword:
        q = q.filter(Product.name.like(f"%{keyword}%"))

    min_price = db_query_min_price()
    if sort == "price_asc":
        q = q.order_by(min_price.asc())
    elif sort == "price_desc":
        q = q.order_by(min_price.desc())
    elif sort == "sales":
        q = q.order_by(Product.sales.desc())
    else:
        q = q.order_by(Product.id.desc())

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    # 批量预取 SKU 与店铺，避免 N+1
    prod_ids = [p.id for p in items]
    skus = db.query(Sku).filter(Sku.product_id.in_(prod_ids)).all() if prod_ids else []
    sku_map = {}
    for s in skus:
        sku_map.setdefault(s.product_id, []).append(s)
    shop_ids = [p.shop_id for p in items if p.shop_id]
    shops = db.query(Shop).filter(Shop.id.in_(shop_ids)).all() if shop_ids else []
    shop_map = {s.id: s for s in shops}

    result = []
    for p in items:
        resp = ProductResp.model_validate(p)
        resp.skus = [SkuResp.model_validate(s) for s in sku_map.get(p.id, [])]
        shop = shop_map.get(p.shop_id)
        if shop:
            resp.shop_name = shop.name
            resp.shop_logo = shop.logo
            resp.shop_rating = float(shop.rating) if shop.rating is not None else None
        result.append(resp)

    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_product(db: Session, product_id: int):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "商品不存在")
    skus = db.query(Sku).filter(Sku.product_id == p.id).all()
    resp = ProductResp.model_validate(p)
    resp.skus = [SkuResp.model_validate(s) for s in skus]
    if p.shop_id:
        shop = db.get(Shop, p.shop_id)
        if shop:
            resp.shop_name = shop.name
            resp.shop_logo = shop.logo
            resp.shop_rating = float(shop.rating) if shop.rating is not None else None
    return resp


def list_categories(db: Session):
    return db.query(Category).order_by(Category.sort).all()


def home_data(db: Session):
    categories = list_categories(db)
    # 首页推荐：数码类(cat=3)全部前置，再补其他高销量商品，凑 20
    dig = db.query(Product).filter(Product.category_id == 3).order_by(Product.sales.desc()).all()
    rest = (
        db.query(Product)
        .filter(Product.category_id.notin_([3]))
        .order_by(Product.sales.desc())
        .limit(max(0, 20 - len(dig)))
        .all()
    )
    rec_products = dig + rest
    prod_ids = [p.id for p in rec_products]
    skus = db.query(Sku).filter(Sku.product_id.in_(prod_ids)).all() if prod_ids else []
    sku_map = {}
    for s in skus:
        sku_map.setdefault(s.product_id, []).append(s)
    shop_ids = [p.shop_id for p in rec_products if p.shop_id]
    shops = db.query(Shop).filter(Shop.id.in_(shop_ids)).all() if shop_ids else []
    shop_map = {s.id: s for s in shops}
    recommend = []
    for p in rec_products:
        resp = ProductResp.model_validate(p)
        resp.skus = [SkuResp.model_validate(s) for s in sku_map.get(p.id, [])]
        shop = shop_map.get(p.shop_id)
        if shop:
            resp.shop_name = shop.name
            resp.shop_logo = shop.logo
            resp.shop_rating = float(shop.rating) if shop.rating is not None else None
        recommend.append(resp)
    banners = [
        {"id": 1, "image": "/images/slide_1.png", "title": "手机数码狂欢节"},
        {"id": 2, "image": "/images/slide_2.png", "title": "美妆护肤焕新季"},
        {"id": 3, "image": "/images/slide_3.png", "title": "食品生鲜特惠"},
    ]
    channels = [
        {"name": "聚划算", "icon": "🔥", "url": "/channel/juhuasuan"},
        {"name": "百亿补贴", "icon": "💰", "url": "/channel/subsidy"},
        {"name": "天猫超市", "icon": "🛒", "url": "/channel/mall"},
        {"name": "天天特卖", "icon": "🏷️", "url": "/channel/temai"},
        {"name": "淘抢购", "icon": "⚡", "url": "/channel/qiang"},
    ]
    return {
        "banners": banners,
        "channels": channels,
        "categories": [CategoryResp.model_validate(c).model_dump(mode="json") for c in categories],
        "recommend": [r.model_dump(mode="json") for r in recommend],
    }


def list_reviews(db: Session, sku_id: int = None, product_id: int = None):
    q = db.query(Review)
    if sku_id:
        q = q.filter(Review.sku_id == sku_id)
    reviews = q.order_by(Review.id.desc()).all()
    if product_id:
        sku_ids = [s.id for s in db.query(Sku).filter(Sku.product_id == product_id).all()]
        reviews = [r for r in reviews if r.sku_id in sku_ids]
    return [ReviewResp.model_validate(r) for r in reviews]


def average_rating(db: Session, sku_id: int) -> float:
    rows = db.query(Review.rating).filter(Review.sku_id == sku_id).all()
    if not rows:
        return 0.0
    return sum(r[0] for r in rows) / len(rows)


def add_review(db: Session, user_id: int, req) -> Review:
    order = db.get(Order, req.order_id)
    if not order or order.user_id != user_id:
        raise HTTPException(400, "订单不存在或不属于你")
    if order.order_status < 3:
        raise HTTPException(400, "订单未完成，无法评价")
    has_sku = db.query(OrderItem).filter(
        OrderItem.order_id == req.order_id, OrderItem.sku_id == req.sku_id
    ).first()
    if not has_sku:
        raise HTTPException(400, "订单不含该商品")
    existed = db.query(Review).filter(
        Review.order_id == req.order_id, Review.sku_id == req.sku_id,
        Review.user_id == user_id
    ).first()
    if existed:
        raise HTTPException(400, "已评价过")
    rev = Review(
        order_id=req.order_id, sku_id=req.sku_id, user_id=user_id,
        rating=req.rating, content=req.content, images=req.images,
    )
    db.add(rev)
    db.commit()
    db.refresh(rev)
    return rev
