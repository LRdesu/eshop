"""生成多店铺 + 多商品演示数据（幂等，可重复运行）。

执行：
    cd backend
    .venv/Scripts/python.exe seed_shops.py

动作：
    1. 为 20 个类目，每类目建 2 家店铺（不同品牌），共 40 家。
    2. 每店 5 个商品，每商品 2 个 SKU（规格/价格/库存），共约 200 商品。
    3. 生成 20 张类目封面 SVG 到 frontend/public/images/cat_{id}.svg。
    4. 店铺/商品按名称去重，重跑安全。
"""
import os
import random

from app.database import SessionLocal
from app.models import Category, Shop, Product, Sku
from app.services.catalog_service import next_sku_code

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(BASE, "frontend", "public", "images")

# 类目核心词 + 品牌 + 修饰 + 价格区间（基础价下限, 上限）
CORE = {
    "女装": ("女装", 59, 599), "男装": ("男装", 69, 699), "手机数码": ("手机", 999, 6999),
    "电脑办公": ("电脑", 899, 8999), "家用电器": ("家电", 199, 4999), "美妆护肤": ("美妆", 49, 899),
    "母婴用品": ("母婴", 39, 599), "食品生鲜": ("食品", 19, 299), "鞋靴箱包": ("鞋包", 99, 1299),
    "运动户外": ("运动", 49, 999), "家居家装": ("家居", 29, 1999), "图书文娱": ("图书", 19, 199),
    "玩具乐器": ("玩具", 29, 899), "汽车用品": ("车品", 39, 1299), "珠宝钟表": ("珠宝", 299, 9999),
    "医药健康": ("健康", 19, 499), "鲜花绿植": ("花植", 29, 399), "宠物用品": ("宠物", 29, 699),
    "厨具餐具": ("厨具", 39, 999), "内衣配饰": ("内衣", 39, 399),
}
BRANDS = ["优品", "臻选", "潮购", "良仓", "严选"]
MODIFIERS = ["新款", "爆款", "旗舰", "臻品", "轻奢", "经典", "热销", "限定"]
SPECS = [("标准装", 1.0), ("豪华装", 1.4), ("组合装", 1.8)]
GRAD = [
    ("#ff9a9e", "#fad0c4"), ("#a18cd1", "#fbc2eb"), ("#84fab0", "#8fd3f4"),
    ("#ffecd2", "#fcb69f"), ("#a1c4fd", "#c2e9fb"), ("#fbc2eb", "#a6c1ee"),
    ("#fdcbf1", "#e6dee9"), ("#f6d365", "#fda085"), ("#cd9cf2", "#f6f3ff"),
    ("#96fbc4", "#f9f586"), ("#2af598", "#009efd"), ("#ee9ca7", "#ffdde1"),
    ("#5ee7df", "#b490ca"), ("#c79081", "#dfa579"), ("#d299c2", "#fef9d7"),
    ("#f5576c", "#f093fb"), ("#4facfe", "#00f2fe"), ("#43e97b", "#38f9d7"),
    ("#fa709a", "#fee140"), ("#30cfd0", "#330867"),
]


def make_svg(cid, emoji, title, c1, c2):
    os.makedirs(IMG_DIR, exist_ok=True)
    path = os.path.join(IMG_DIR, f"cat_{cid}.svg")
    if os.path.exists(path):
        return
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400">'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/>'
        f'</linearGradient></defs>'
        f'<rect width="400" height="400" fill="url(#g)"/>'
        f'<text x="200" y="175" font-size="130" text-anchor="middle">{emoji}</text>'
        f'<text x="200" y="300" font-size="36" fill="#ffffff" text-anchor="middle" '
        f'font-family="sans-serif" font-weight="700">{title}</text>'
        f'</svg>'
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)


def main():
    random.seed(20261006)
    db = SessionLocal()
    try:
        cats = db.query(Category).order_by(Category.sort).all()
        if not cats:
            print("[!] 未找到类目，请先运行 migrate_shop.py")
            return

        shop_count = 0
        prod_count = 0
        last_sku = next_sku_code(db) - 1  # 独立 5 位 SKU 编码游标（10000 起），全局唯一
        for idx, c in enumerate(cats):
            c1, c2 = GRAD[idx % len(GRAD)]
            make_svg(c.id, c.icon or "🛍️", c.name, c1, c2)
            core_word, lo, hi = CORE.get(c.name, (c.name, 39, 599))

            # 每类目 2 家店铺（不同品牌）
            for b in range(2):
                brand = BRANDS[b % len(BRANDS)]
                shop_name = f"{brand}{core_word}官方店"
                shop = db.query(Shop).filter(Shop.name == shop_name).first()
                if not shop:
                    shop = Shop(
                        name=shop_name,
                        logo=f"/images/cat_{c.id}.svg",
                        description=f"{brand}旗下{c.name}精选好店，正品保障，极速发货。",
                        owner_user_id=None,
                        status=1,
                        rating=round(random.uniform(4.6, 5.0), 1),
                    )
                    db.add(shop)
                    db.commit()
                    db.refresh(shop)
                    shop_count += 1

                # 每店 5 个商品
                for k in range(5):
                    pname = f"{MODIFIERS[(b * 5 + k) % len(MODIFIERS)]}{core_word}{['套装', '单品', '礼盒', '基础款', '升级款'][k % 5]}"
                    exist = db.query(Product).filter(
                        Product.shop_id == shop.id, Product.name == pname
                    ).first()
                    if exist:
                        if not exist.sales:
                            exist.sales = random.randint(50, 5000)
                        continue
                    base = round(random.uniform(lo, hi), 2)
                    p = Product(
                        name=pname,
                        description=f"{c.name} {pname}，品质优选，七天无理由退换，假一赔十。",
                        category=c.name,
                        shop_id=shop.id,
                        category_id=c.id,
                        sales=random.randint(50, 5000),
                        cover=f"/images/cat_{c.id}.svg",
                    )
                    db.add(p)
                    db.commit()
                    db.refresh(p)
                    # 每个商品 2 个 SKU
                    for si, (spec, mult) in enumerate(SPECS[:2]):
                        last_sku += 1
                        db.add(Sku(
                            product_id=p.id,
                            spec=spec,
                            price=round(base * mult, 2),
                            stock=random.randint(10, 500),
                            image=f"/images/cat_{c.id}.svg",
                            sku_code=last_sku,
                        ))
                    prod_count += 1
        db.commit()
        print(f"[+] 新增店铺 {shop_count} 家，新增商品 {prod_count} 件；类目封面 20 张已生成")
        print(f"[=] 当前店铺总数 {db.query(Shop).count()}，商品总数 {db.query(Product).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
