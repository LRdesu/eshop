"""给买家 demo 账号预置收藏与关注店铺数据（幂等，可重复跑）。

- 每个买家（role=0）：若无收藏则收藏 6 个随机商品；若无关注则关注 2 个店铺。
- 已有数据的买家跳过对应部分，不重复插入。
"""
import random

from app.database import SessionLocal
from app.models import User, Product, Shop, Favorite, Follow


def main():
    db = SessionLocal()
    try:
        buyers = db.query(User).filter(User.role == 0).all()
        product_ids = [p.id for p in db.query(Product.id).all()]
        shop_ids = [s.id for s in db.query(Shop.id).all()]
        if not product_ids:
            print("no products, skip")
            return

        fav_total = follow_total = 0
        for u in buyers:
            has_fav = db.query(Favorite).filter(Favorite.user_id == u.id).first()
            if not has_fav:
                picks = random.sample(product_ids, min(6, len(product_ids)))
                for pid in picks:
                    db.add(Favorite(user_id=u.id, product_id=pid))
                fav_total += len(picks)
                print(f"user {u.username}: +{len(picks)} favorites")

            has_follow = db.query(Follow).filter(Follow.user_id == u.id).first()
            if not has_follow and shop_ids:
                picks = random.sample(shop_ids, min(2, len(shop_ids)))
                for sid in picks:
                    db.add(Follow(user_id=u.id, shop_id=sid))
                follow_total += len(picks)
                print(f"user {u.username}: +{len(picks)} follows")

        db.commit()
        print(f"done: +{fav_total} favorites, +{follow_total} follows for {len(buyers)} buyers")
    finally:
        db.close()


if __name__ == "__main__":
    main()
