"""为商品 / 店铺 / 首页 Banner 生成专属 SVG 图片（幂等，可重复运行）。

执行：
    cd backend
    .venv/Scripts/python.exe gen_images.py

动作：
    1. 每个商品 -> frontend/public/images/prod_{id}.svg（专属封面，含商品名+类目 emoji+渐变底）
    2. 每个 SKU  -> image 同步指向其商品封面
    3. 每个店铺 -> frontend/public/images/shop_{id}.svg（专属 logo，店名首字+渐变圆底）
    4. 3 张首页 Banner -> frontend/public/images/banner_{1,2,3}.svg
    5. 更新数据库 products.cover / skus.image / shops.logo 指向专属图路径

说明：复用既有类目渐变风格，全部本地生成 SVG，零外部依赖、零成本、可重复。
"""
import os

from app.database import SessionLocal
from app.models import Product, Sku, Shop, Category

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(BASE, "frontend", "public", "images")
os.makedirs(IMG_DIR, exist_ok=True)

# 与 seed_shops.py 一致的渐变池
GRAD = [
    ("#ff9a9e", "#fad0c4"), ("#a18cd1", "#fbc2eb"), ("#84fab0", "#8fd3f4"),
    ("#ffecd2", "#fcb69f"), ("#a1c4fd", "#c2e9fb"), ("#fbc2eb", "#a6c1ee"),
    ("#fdcbf1", "#e6dee9"), ("#f6d365", "#fda085"), ("#cd9cf2", "#f6f3ff"),
    ("#96fbc4", "#f9f586"), ("#2af598", "#009efd"), ("#ee9ca7", "#ffdde1"),
    ("#5ee7df", "#b490ca"), ("#c79081", "#dfa579"), ("#d299c2", "#fef9d7"),
    ("#f5576c", "#f093fb"), ("#4facfe", "#00f2fe"), ("#43e97b", "#38f9d7"),
    ("#fa709a", "#fee140"), ("#30cfd0", "#330867"),
]

# 每个类目一组 emoji，用于商品封面与 SKU 图，按序号轮换以保证同店不同商品有差异
CATEGORY_EMOJI = {
    "女装": ["👗", "👚", "👜", "🧥"], "男装": ["👔", "👕", "🧥", "👞"],
    "手机数码": ["📱", "💻", "🔌", "🎧"], "电脑办公": ["💻", "🖥️", "⌨️", "🖨️"],
    "家用电器": ["🔌", "📺", "🧊", "🧹"], "美妆护肤": ["💄", "🧴", "💅", "🪞"],
    "母婴用品": ["🍼", "👶", "🧸", "🚼"], "食品生鲜": ["🍎", "🥩", "🍜", "🥬"],
    "鞋靴箱包": ["👟", "👠", "👜", "🥾"], "运动户外": ["⚽", "🏃", "🚴", "🏕️"],
    "家居家装": ["🛋️", "🛏️", "🪑", "🛁"], "图书文娱": ["📚", "📖", "🎮", "🎬"],
    "玩具乐器": ["🧸", "🎸", "🪀", "🎹"], "汽车用品": ["🚗", "🛞", "🔧", "🧼"],
    "珠宝钟表": ["💎", "⌚", "💍", "📿"], "医药健康": ["💊", "🩺", "🌿", "🧪"],
    "鲜花绿植": ["🌸", "🌿", "🪴", "🌺"], "宠物用品": ["🐶", "🐱", "🐾", "🦴"],
    "厨具餐具": ["🍳", "🍴", "🥘", "🍵"], "内衣配饰": ["🩲", "🧦", "👜", "🧣"],
}

DEFAULT_EMOJI = ["🛍️", "🎁", "✨", "🛒"]


def write_svg(filename, content):
    path = os.path.join(IMG_DIR, filename)
    if os.path.exists(path):
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def product_svg(pname, emoji, c1, c2):
    # 商品名过长则截断，避免溢出
    label = pname if len(pname) <= 8 else pname[:7] + "…"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400">'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/>'
        f'</linearGradient></defs>'
        f'<rect width="400" height="400" rx="16" fill="url(#g)"/>'
        f'<text x="200" y="200" font-size="150" text-anchor="middle" dominant-baseline="middle">{emoji}</text>'
        f'<rect x="0" y="320" width="400" height="80" fill="rgba(0,0,0,0.28)"/>'
        f'<text x="200" y="368" font-size="30" fill="#ffffff" text-anchor="middle" '
        f'font-family="sans-serif" font-weight="700">{label}</text>'
        f'</svg>'
    )


def shop_svg(chars, c1, c2):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120">'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/>'
        f'</linearGradient></defs>'
        f'<circle cx="60" cy="60" r="58" fill="url(#g)"/>'
        f'<text x="60" y="60" font-size="56" fill="#ffffff" text-anchor="middle" '
        f'dominant-baseline="central" font-family="sans-serif" font-weight="800">{chars}</text>'
        f'</svg>'
    )


def banner_svg(title, subtitle, emoji, c1, c2):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="360">'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/>'
        f'</linearGradient></defs>'
        f'<rect width="1000" height="360" fill="url(#g)"/>'
        f'<text x="70" y="170" font-size="66" fill="#ffffff" font-family="sans-serif" font-weight="800">{title}</text>'
        f'<text x="72" y="240" font-size="32" fill="#ffffff" opacity="0.92" font-family="sans-serif">{subtitle}</text>'
        f'<text x="820" y="200" font-size="160" text-anchor="middle" dominant-baseline="central">{emoji}</text>'
        f'</svg>'
    )


def main():
    db = SessionLocal()
    try:
        # 类目名 -> 渐变序号，使同类目商品底色一致、不同类目有区分
        cats = db.query(Category).order_by(Category.sort).all()
        cat_index = {c.name: i for i, c in enumerate(cats)}

        # 1) 商品专属封面 + 2) SKU 图同步
        products = db.query(Product).order_by(Product.id).all()
        cat_counter = {}
        for p in products:
            ci = cat_index.get(p.category, len(cats))  # 历史商品无类目则排末尾
            seq = cat_counter.get(p.category, 0)
            cat_counter[p.category] = seq + 1
            c1, c2 = GRAD[(ci + seq) % len(GRAD)]
            pool = CATEGORY_EMOJI.get(p.category, DEFAULT_EMOJI)
            emoji = pool[seq % len(pool)]
            cover_path = f"/images/prod_{p.id}.svg"
            write_svg(f"prod_{p.id}.svg", product_svg(p.name or f"商品{p.id}", emoji, c1, c2))
            p.cover = cover_path
            db.query(Sku).filter(Sku.product_id == p.id).update(
                {Sku.image: cover_path}, synchronize_session=False
            )
        db.commit()
        print(f"[+] 商品封面更新 {len(products)} 件，SKU 图同步完成")

        # 3) 店铺专属 logo
        shops = db.query(Shop).order_by(Shop.id).all()
        for i, s in enumerate(shops):
            c1, c2 = GRAD[i % len(GRAD)]
            chars = (s.name or "店")[:2]
            logo_path = f"/images/shop_{s.id}.svg"
            write_svg(f"shop_{s.id}.svg", shop_svg(chars, c1, c2))
            s.logo = logo_path
        db.commit()
        print(f"[+] 店铺 logo 更新 {len(shops)} 家")

        # 4) 首页 3 张 Banner（注意：Vite dev 服务会拦截文件名含 "banner" 前缀的静态资源，
        #    故统一用 slide_*.svg 命名，避免返回 SPA 兜底页导致裂图）
        banners = [
            ("slide_1.svg", "手机数码狂欢节", "新品首发 至高省 2000", "📱", GRAD[2][0], GRAD[2][1]),
            ("slide_2.svg", "美妆护肤焕新季", "大牌甄选 满 300 减 50", "💄", GRAD[5][0], GRAD[5][1]),
            ("slide_3.svg", "食品生鲜特惠", "产地直发 当日送达", "🍎", GRAD[7][0], GRAD[7][1]),
        ]
        for fn, t, sub, em, c1, c2 in banners:
            write_svg(fn, banner_svg(t, sub, em, c1, c2))
        print(f"[+] 首页 Banner 生成 {len(banners)} 张")

        print(f"[=] 图片目录文件数: {len(os.listdir(IMG_DIR))}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
