"""幂等迁移：新增 favorites / follows 两张社交关系表。

可直接重复运行；已存在则跳过（基于 SQLAlchemy metadata.create_all）。
运行：backend/ 目录下 `python migrate_social.py`
"""
from app.database import engine, Base
from app.models import Favorite, Follow


def main():
    # 仅对这两张表执行创建，避免影响其它已存在表
    Base.metadata.create_all(bind=engine, tables=[Favorite.__table__, Follow.__table__])
    print("[+] favorites / follows 表就绪（已存在则跳过）")


if __name__ == "__main__":
    main()
