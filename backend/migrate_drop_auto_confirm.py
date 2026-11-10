"""幂等迁移：删除 orders.auto_confirm_at 列（清理从未被调用的 auto_confirm 死代码）。

运行：backend/ 目录下
    .venv/Scripts/python.exe migrate_drop_auto_confirm.py
"""
from sqlalchemy import text

from app.database import engine


def migrate():
    with engine.connect() as conn:
        exists = conn.execute(
            text("SHOW COLUMNS FROM orders LIKE 'auto_confirm_at'")
        ).fetchone()
        if exists:
            conn.execute(text("ALTER TABLE orders DROP COLUMN auto_confirm_at"))
            conn.commit()
            print("已删除 orders.auto_confirm_at 列")
        else:
            print("orders.auto_confirm_at 列不存在，跳过")


if __name__ == "__main__":
    migrate()
