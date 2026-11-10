"""平台升级迁移：多店铺体系 + 20 类目（幂等，可重复运行）。

执行：
    cd backend
    .venv/Scripts/python.exe migrate_shop.py

动作：
    1. 建 shops / categories 表（IF NOT EXISTS）。
    2. products 增加 shop_id / category_id 列（已存在则跳过）。
    3. 插入 20 个标准类目（按 name 去重）。
    4. 现有 admin 账号 role 1 -> 2（平台管理员，运营总后台）。
    5. 建「淘京官方旗舰店」接收历史商品；所有无 shop 的商品归到该店。
    6. 历史商品按 category 名称回填 category_id（匹配不上则按 id 轮询分配）。
"""
from sqlalchemy import text

from app.config import config
from app.database import engine, SessionLocal
from app.models import User, Shop, Category, Product

DB_NAME = config.DB_NAME

# 20 个标准类目（name, icon）
CATEGORIES = [
    ("女装", "👗"), ("男装", "👔"), ("手机数码", "📱"), ("电脑办公", "💻"),
    ("家用电器", "🔌"), ("美妆护肤", "💄"), ("母婴用品", "🍼"), ("食品生鲜", "🍎"),
    ("鞋靴箱包", "👟"), ("运动户外", "⚽"), ("家居家装", "🛋️"), ("图书文娱", "📚"),
    ("玩具乐器", "🎸"), ("汽车用品", "🚗"), ("珠宝钟表", "💎"), ("医药健康", "💊"),
    ("鲜花绿植", "🌿"), ("宠物用品", "🐾"), ("厨具餐具", "🍳"), ("内衣配饰", "🧦"),
]

OFFICIAL_SHOP = "淘京官方旗舰店"


def col_exists(conn, table, col):
    r = conn.execute(
        text(
            "SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA=:db AND TABLE_NAME=:t AND COLUMN_NAME=:c"
        ),
        {"db": DB_NAME, "t": table, "c": col},
    ).fetchone()
    return r is not None


def ensure_tables(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS shops (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            logo VARCHAR(255),
            description TEXT,
            rating DECIMAL(2,1) NOT NULL DEFAULT 5.0,
            owner_user_id INT,
            status SMALLINT NOT NULL DEFAULT 1,
            created_at DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS categories (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(50) NOT NULL,
            icon VARCHAR(255),
            sort INT NOT NULL DEFAULT 0,
            created_at DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """))
    conn.commit()
    print("[+] 表 shops / categories 就绪")


def ensure_columns(conn):
    for col in ("shop_id", "category_id", "sales"):
        if not col_exists(conn, "products", col):
            conn.execute(text(f"ALTER TABLE products ADD COLUMN {col} INT"))
            print(f"[+] products 增加列 {col}")
        else:
            print(f"[=] products 已有列 {col}，跳过")
    conn.commit()


def ensure_categories(db):
    for i, (name, icon) in enumerate(CATEGORIES, start=1):
        if not db.query(Category).filter(Category.name == name).first():
            db.add(Category(name=name, icon=icon, sort=i))
    db.commit()
    print(f"[+] 类目就绪（共 {db.query(Category).count()} 个）")


def ensure_official_shop(db):
    admin = db.query(User).filter(User.username == "admin").first()
    if admin and admin.role == 1:
        admin.role = 2
        db.commit()
        print("[+] admin 账号 role 1 -> 2（平台管理员）")

    official = db.query(Shop).filter(Shop.name == OFFICIAL_SHOP).first()
    if not official:
        official = Shop(
            name=OFFICIAL_SHOP,
            logo="",
            description="平台自营官方旗舰店",
            owner_user_id=admin.id if admin else None,
            status=1,
        )
        db.add(official)
        db.commit()
        db.refresh(official)
        print(f"[+] 已建官方旗舰店 {OFFICIAL_SHOP}（id={official.id}）")
    else:
        print(f"[=] 官方旗舰店已存在（id={official.id}）")
    return official


def bind_products(db, official):
    cat_map = {c.name: c.id for c in db.query(Category).all()}
    n = 0
    for p in db.query(Product).all():
        if p.shop_id is None:
            p.shop_id = official.id
            n += 1
        if p.category_id is None:
            cid = cat_map.get(p.category)
            if not cid:
                cid = (p.id % len(CATEGORIES)) + 1
                p.category = CATEGORIES[cid - 1][0]
            p.category_id = cid
    db.commit()
    print(f"[+] 历史商品归店 / 回填类目完成（归店 {n} 件）")


def main():
    conn = engine.connect()
    try:
        ensure_tables(conn)
        ensure_columns(conn)
        # Coupon 增加 shop_id 列，以便按店铺隔离优惠券
        if not col_exists(conn, "coupons", "shop_id"):
            conn.execute(text("ALTER TABLE coupons ADD COLUMN shop_id INT"))
            conn.commit()
            print("[+] coupons 增加列 shop_id")
    finally:
        conn.close()

    db = SessionLocal()
    try:
        ensure_categories(db)
        official = ensure_official_shop(db)
        bind_products(db, official)
    finally:
        db.close()
    print("== migrate_shop 完成 ==")


if __name__ == "__main__":
    main()
