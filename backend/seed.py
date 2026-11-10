# -*- coding: utf-8 -*-
"""演示数据：运费规则、商品/SKU（含图片）、优惠券，并创建演示买家且发放券。

用法：
    cd backend
    python seed.py
可重复执行：已存在数据则跳过；商品/SKU 图片字段为空时自动回填。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import (
    ShippingFee, Product, Sku, Coupon, UserCoupon, User, Address,
)
from app.utils.security import hash_password
from app.services.catalog_service import next_sku_code

# ---- 商品图片配置（文件位于 frontend/public/images/，前端以 /images/xxx 访问）----
PRODUCT_IMAGES = {
    "纯棉短袖T恤": {
        "cover": "/images/tshirt-white.png",
        "gallery": "/images/tshirt-white.png,/images/tshirt-black.png,/images/tshirt-detail.png",
    },
    "蓝牙耳机": {
        "cover": "/images/earphone-white.png",
        "gallery": "/images/earphone-white.png,/images/earphone-black.png,/images/earphone-detail.png",
    },
    "保温杯": {
        "cover": "/images/bottle.png",
        "gallery": "/images/bottle.png,/images/bottle-detail.png",
    },
}

# (商品分类, 规格关键词) -> SKU 图
SKU_IMAGES = [
    ("服装", "白", "/images/tshirt-white.png"),
    ("服装", "黑", "/images/tshirt-black.png"),
    ("数码", "白", "/images/earphone-white.png"),
    ("数码", "黑", "/images/earphone-black.png"),
    ("家居", "500ml", "/images/bottle.png"),
]


def _sku_image(category, spec):
    for cat, kw, img in SKU_IMAGES:
        if cat == category and kw in (spec or ""):
            return img
    return None


def seed():
    db = SessionLocal()
    try:
        # ---- 运费规则 ----
        if not db.query(ShippingFee).first():
            db.add_all([
                ShippingFee(region="省内", fee="6.00"),
                ShippingFee(region="省外", fee="12.00"),
            ])
            print("inserted shipping_fees")

        # ---- 商品 + SKU ----
        if not db.query(Product).first():
            c1 = PRODUCT_IMAGES["纯棉短袖T恤"]
            c2 = PRODUCT_IMAGES["蓝牙耳机"]
            c3 = PRODUCT_IMAGES["保温杯"]
            p1 = Product(name="纯棉短袖T恤", description="夏季百搭基础款，100%纯棉亲肤透气，多色多码可选",
                         category="服装", cover=c1["cover"], gallery=c1["gallery"])
            p2 = Product(name="蓝牙耳机", description="主动降噪，蓝牙5.3，超长续航",
                         category="数码", cover=c2["cover"], gallery=c2["gallery"])
            p3 = Product(name="保温杯", description="316不锈钢内胆，12小时长效保温",
                         category="家居", cover=c3["cover"], gallery=c3["gallery"])
            db.add_all([p1, p2, p3])
            db.flush()
            c0 = next_sku_code(db)
            db.add_all([
                Sku(product_id=p1.id, spec="颜色:白/尺寸:M", price="39.90", stock=100,
                    image=_sku_image("服装", "颜色:白"), sku_code=c0),
                Sku(product_id=p1.id, spec="颜色:黑/尺寸:L", price="39.90", stock=80,
                    image=_sku_image("服装", "颜色:黑"), sku_code=c0 + 1),
                Sku(product_id=p2.id, spec="颜色:白", price="199.00", stock=50,
                    image=_sku_image("数码", "颜色:白"), sku_code=c0 + 2),
                Sku(product_id=p2.id, spec="颜色:黑", price="209.00", stock=50,
                    image=_sku_image("数码", "颜色:黑"), sku_code=c0 + 3),
                Sku(product_id=p3.id, spec="容量:500ml", price="59.00", stock=120,
                    image=_sku_image("家居", "容量:500ml"), sku_code=c0 + 4),
            ])
            print("inserted products + skus (with images)")

        # ---- 图片回填（存量数据：cover / gallery / image 为空时补齐）----
        changed = False
        for p in db.query(Product).all():
            cfg = PRODUCT_IMAGES.get(p.name)
            if not cfg:
                continue
            if not p.cover:
                p.cover = cfg["cover"]
                changed = True
            if not p.gallery:
                p.gallery = cfg["gallery"]
                changed = True
        for s in db.query(Sku).all():
            if s.image:
                continue
            prod = db.get(Product, s.product_id)
            img = _sku_image(prod.category if prod else None, s.spec)
            if img:
                s.image = img
                changed = True
        if changed:
            print("backfilled product/sku images")
        db.commit()

        # ---- 优惠券模板 ----
        if not db.query(Coupon).first():
            db.add_all([
                Coupon(name="满100减20", type="FULL", threshold="100.00", value="20.00",
                       scope="ALL", valid_from=None, valid_to=None, total=999, per_limit=1),
                Coupon(name="全场9折", type="DISCOUNT", threshold="0.00", value="0.90",
                       scope="ALL", total=999, per_limit=1),
                Coupon(name="运费券减10", type="SHIPPING", threshold="0.00", value="10.00",
                       scope="ALL", total=999, per_limit=1),
                Coupon(name="服装满50减15", type="FULL", threshold="50.00", value="15.00",
                       scope="CATEGORY", scope_value="服装", total=999, per_limit=1),
            ])
            print("inserted coupons")

        # ---- 收货地址统一为南京（演示约定：上海仓发货 → 南京收货）----
        n_addr = 0
        for a in db.query(Address).all():
            if a.city != "南京" or a.province != "江苏":
                a.province = "江苏"
                a.city = "南京"
                n_addr += 1
        if n_addr:
            print("normalized %d addresses -> 江苏/南京" % n_addr)

        # ---- 演示买家 + 默认地址 + 发券 ----
        demo = db.query(User).filter(User.username == "alice").first()
        if not demo:
            demo = User(username="alice", password_hash=hash_password("alice123"),
                        nickname="演示买家", phone="13800000000", points=0)
            db.add(demo)
            db.flush()
            db.add(Address(user_id=demo.id, receiver="小明", phone="13800000000",
                           province="江苏", city="南京", district="鼓楼区",
                           detail="中山北路1号(南京)", is_default=1))
            coupons = db.query(Coupon).all()
            for c in coupons:
                db.add(UserCoupon(user_id=demo.id, coupon_id=c.id, status=0))
            print("inserted demo user 'alice' / alice123 + 默认地址 + 4张券")

        db.commit()
        print("SEED DONE")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
