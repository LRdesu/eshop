"""migrate_coupons_deleted.py

给 coupons 表加 deleted 标记列（0正常/1已下架）。
卖家「删除」优惠券改为软删除：券从领券中心/商家列表下架，
但已领取的 user_coupons 与 coupons 行均保留，已领买家不受影响。
幂等：列已存在则跳过。
"""
from sqlalchemy import text

from app.database import SessionLocal


def main():
    db = SessionLocal()
    try:
        # 已存在则跳过
        exists = db.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = 'coupons' "
            "AND column_name = 'deleted'"
        )).scalar()
        if exists:
            print("coupons.deleted 已存在，跳过")
            return
        db.execute(text(
            "ALTER TABLE coupons ADD COLUMN deleted SMALLINT NOT NULL DEFAULT 0"
        ))
        db.commit()
        print("已为 coupons 表添加 deleted 列（默认 0）")
    finally:
        db.close()


if __name__ == "__main__":
    main()
