"""建表：activities / activity_shops；并新建平台管理员账号 platform(role=2)。"""
from app.database import engine, Base
from app.models import Activity, ActivityShop  # 触发模型注册

# 建表
Base.metadata.create_all(bind=engine)
print("[1] activities / activity_shops 表已就绪")

# 新建 platform 平台管理员账号（密码由参数传入，避免明文）
import sys
from app.utils.security import hash_password
from sqlalchemy import text

pw = sys.stdin.read().strip()
with engine.begin() as c:
    row = c.execute(text("SELECT id FROM users WHERE username='platform'")).first()
    if row:
        c.execute(text("UPDATE users SET role=2, password_hash=:h WHERE username='platform'"),
                   {"h": hash_password(pw)})
        print("[2] platform 账号已存在，已重置密码与角色")
    else:
        c.execute(text(
            "INSERT INTO users (username, password_hash, nickname, role) VALUES "
            "('platform', :h, '平台运营', 2)"
        ), {"h": hash_password(pw)})
        print("[2] 已新建平台管理员账号 platform (role=2)")
print("== 迁移完成 ==")
