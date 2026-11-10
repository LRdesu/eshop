"""幂等铺入演示优惠券：1 张平台券 + 多家店铺券（已存在则跳过）。

运行：backend/ 目录下 `python seed_coupons.py`
"""
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import Coupon


# (名称, shop_id or None, type, threshold, value, total, per_limit)
COUPONS = [
    ("全场满199减30", None, "FULL", 199.0, 30.0, 9999, 1),
    ("新人无门槛减10", None, "FULL", 0.0, 10.0, 9999, 1),
    ("官方旗舰店满99减15", 1, "FULL", 99.0, 15.0, 2000, 1),
    ("官方旗舰店9折券", 1, "DISCOUNT", 0.0, 0.9, 1000, 1),
    ("优品女装满120减20", 2, "FULL", 120.0, 20.0, 1000, 1),
    ("臻选男装满100减12", 3, "FULL", 100.0, 12.0, 1000, 1),
    ("潮购数码满300减40", 4, "FULL", 300.0, 40.0, 800, 1),
    ("良仓电脑满500减60", 5, "FULL", 500.0, 60.0, 600, 1),
    ("严选家电满400减50", 6, "FULL", 400.0, 50.0, 600, 1),
    ("优品美妆满150减25", 7, "FULL", 150.0, 25.0, 800, 1),
    ("臻选母婴满200减30", 8, "FULL", 200.0, 30.0, 600, 1),
    ("潮购食品满80减10", 9, "FULL", 80.0, 10.0, 1200, 1),
    ("包邮券（店铺）", 10, "SHIPPING", 0.0, 0.0, 500, 1),
]


def main():
    db = SessionLocal()
    now = datetime.now()
    vto = now + timedelta(days=30)
    added = 0
    for name, shop_id, ctype, th, val, total, per in COUPONS:
        exists = db.query(Coupon).filter(Coupon.name == name,
                                         Coupon.shop_id == shop_id).first()
        if exists:
            continue
        db.add(Coupon(
            shop_id=shop_id, name=name, type=ctype,
            threshold=th, value=val, scope="ALL", scope_value=None,
            valid_from=now, valid_to=vto, total=total, per_limit=per,
        ))
        added += 1
    db.commit()
    total = db.query(Coupon).count()
    db.close()
    print(f"[+] 新增优惠券 {added} 张，当前共 {total} 张")


if __name__ == "__main__":
    main()
