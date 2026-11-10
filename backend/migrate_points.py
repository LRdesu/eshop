"""迁移：orders 表新增 points_used / points_discount 字段（淘金币抵扣）。"""
from app.database import engine
from sqlalchemy import text


def add_col(conn, col, ddl):
    r = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema=DATABASE() AND table_name='orders' AND column_name=:c"
    ), {"c": col}).scalar()
    if r == 0:
        conn.execute(text(ddl))
        print(f"[*] 新增列 {col}")
    else:
        print(f"[*] 列 {col} 已存在，跳过")


with engine.begin() as c:
    add_col(c, "points_used", "ALTER TABLE orders ADD COLUMN points_used INT NOT NULL DEFAULT 0 COMMENT '淘金币抵扣所用币数'")
    add_col(c, "points_discount", "ALTER TABLE orders ADD COLUMN points_discount DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '金币抵扣金额'")
print("== migrate_points 完成 ==")
