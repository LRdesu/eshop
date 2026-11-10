# -*- coding: utf-8 -*-
import io, os
BASE = "D:/Desktop/wanho/Python_code/103hanchao/eshop"

def patch(rel, old, new):
    p = os.path.join(BASE, rel)
    with io.open(p, encoding="utf-8") as f:
        s = f.read()
    if old not in s:
        if new in s:
            print("SKIP (already patched):", rel); return
        raise SystemExit("PATTERN NOT FOUND in %s: %r" % (rel, old[:70]))
    s = s.replace(old, new, 1)
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)
    print("PATCHED:", rel)

# 1. ORM: Product 增加 gallery
patch("backend/app/models/orm.py",
      "    category = Column(String(50))\n    cover = Column(String(255))\n    created_at",
      "    category = Column(String(50))\n    cover = Column(String(255))\n    gallery = Column(Text)\n    created_at")

# 2. Schema: ProductResp.gallery / OrderItemResp.product_cover
patch("backend/app/schemas/__init__.py",
      "    cover: Optional[str] = None\n    skus: List[SkuResp] = []",
      "    cover: Optional[str] = None\n    gallery: Optional[str] = None\n    skus: List[SkuResp] = []")
patch("backend/app/schemas/__init__.py",
      "    sku_spec: Optional[str] = None\n    product_name: Optional[str] = None",
      "    sku_spec: Optional[str] = None\n    product_name: Optional[str] = None\n    product_cover: Optional[str] = None")

# 3. order_service: 订单行返回商品主图
patch("backend/app/services/order_service.py",
      "        oir.sku_spec = sku.spec if sku else None\n        oir.product_name = prod.name if prod else None",
      "        oir.sku_spec = sku.spec if sku else None\n        oir.product_name = prod.name if prod else None\n        oir.product_cover = prod.cover if prod else None")

print("ALL PATCHES DONE")
