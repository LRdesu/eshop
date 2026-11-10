# -*- coding: utf-8 -*-
"""商家后台迁移：users 表新增 role 列（0买家 / 1商家管理员），并创建管理员账号。

用法：
    cd backend
    python migrate_admin.py

幂等：列已存在则跳过；管理员账号已存在则只确保 role=1。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

from app.database import engine, SessionLocal
from app.models import User
from app.utils.security import hash_password

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_NICKNAME = "平台管理员"


def ensure_column():
    """users 表若无 role 列则添加。"""
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'role'"
        )).scalar()
        if row:
            print("[=] users.role 列已存在，跳过")
            return
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN role SMALLINT NOT NULL DEFAULT 0 COMMENT '0买家 1商家管理员'"
        ))
        conn.commit()
        print("[+] users.role 列已添加（默认 0=买家）")


def ensure_admin():
    """创建/修正管理员账号。"""
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == ADMIN_USERNAME).first()
        if not u:
            u = User(
                username=ADMIN_USERNAME,
                password_hash=hash_password(ADMIN_PASSWORD),
                nickname=ADMIN_NICKNAME,
                phone="13800000000",
                points=0,
                role=1,
            )
            db.add(u)
            db.commit()
            print(f"[+] 已创建管理员账号：{ADMIN_USERNAME} / {ADMIN_PASSWORD}")
        else:
            changed = False
            if (u.role or 0) != 1:
                u.role = 1
                changed = True
            if changed:
                db.commit()
                print(f"[~] 已修正 {ADMIN_USERNAME} 的 role 为 1")
            else:
                print(f"[=] 管理员账号 {ADMIN_USERNAME} 已存在，无需变更")
    finally:
        db.close()


def main():
    ensure_column()
    ensure_admin()
    print("[✓] 商家后台迁移完成")


if __name__ == "__main__":
    main()
