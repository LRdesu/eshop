"""新增买家账号（幂等迁移脚本）。

用法（在 backend/ 目录下运行）：
    .venv/Scripts/python.exe migrate_buyer.py        # Windows venv
    python migrate_buyer.py                            # 其他环境

行为：
    - 待新增账号见下方 BUYERS 列表，按需修改 username / password / nickname。
    - 用户名已存在则跳过，不重复插入。
    - 新账号固定 role=0（买家），与 /api/v1/auth/register 默认行为一致。
"""
from app.database import SessionLocal
from app.models import User
from app.utils.security import hash_password

# 待新增的买家账号（如需多个，往列表里继续加即可）
BUYERS = [
    {"username": "bob", "password": "bob123", "nickname": "Bob"},
]


def ensure_buyer(db, username: str, password: str, nickname: str):
    exist = db.query(User).filter(User.username == username).first()
    if exist:
        print(f"[=] 买家账号 {username} 已存在（role={exist.role}），跳过")
        return
    u = User(
        username=username,
        password_hash=hash_password(password),
        nickname=nickname,
        role=0,  # 0=买家
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    print(f"[+] 已新增买家账号 {username}（id={u.id}, role=0）")


def main():
    db = SessionLocal()
    try:
        for b in BUYERS:
            ensure_buyer(db, b["username"], b["password"], b.get("nickname", b["username"]))
    finally:
        db.close()


if __name__ == "__main__":
    main()
