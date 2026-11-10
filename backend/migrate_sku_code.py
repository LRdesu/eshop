# -*- coding: utf-8 -*-
"""迁移：skus 表新增独立 5 位 SKU 编码列 sku_code 并回填、加唯一索引。

可重复执行：
  - sku_code 列已存在则跳过 ALTER；
  - 仅对未分配（IS NULL 或 <=0）的行按 id 顺序赋 10000 起的连续唯一编码；
  - 唯一索引 uq_skus_code 不存在才创建。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine


def migrate():
    with engine.begin() as conn:
        # 1) 加列（幂等）
        cols = conn.execute(text("SHOW COLUMNS FROM skus LIKE 'sku_code'")).fetchall()
        if not cols:
            print("[*] ALTER TABLE skus ADD sku_code")
            conn.execute(text(
                "ALTER TABLE skus ADD COLUMN sku_code INT NOT NULL DEFAULT 0"
            ))
        else:
            print("[*] sku_code 列已存在，跳过 ALTER")

        # 2) 回填未分配的行：从当前最大值之后继续，保证全局唯一且为 5 位数
        max_code = conn.execute(text("SELECT COALESCE(MAX(sku_code), 0) FROM skus")).scalar()
        start = max(int(max_code), 9999) + 1
        conn.execute(text("SET @n = :start"), {"start": start - 1})
        res = conn.execute(text(
            "UPDATE skus SET sku_code = (@n := @n + 1) "
            "WHERE sku_code IS NULL OR sku_code <= 0 "
            "ORDER BY id"
        ))
        print(f"[*] 回填 sku_code 行数 = {res.rowcount}（起始值 {start}）")

        # 3) 唯一索引（幂等）
        u = conn.execute(text("SHOW INDEX FROM skus WHERE Key_name='uq_skus_code'")).fetchall()
        if not u:
            print("[*] 创建唯一索引 uq_skus_code")
            conn.execute(text("ALTER TABLE skus ADD UNIQUE KEY uq_skus_code (sku_code)"))
        else:
            print("[*] 唯一索引已存在，跳过")

        # 4) 校验：是否存在超范围 / 重复
        over = conn.execute(text(
            "SELECT COUNT(*) FROM skus WHERE sku_code < 10000 OR sku_code > 99999"
        )).scalar()
        dup = conn.execute(text(
            "SELECT COUNT(*) FROM (SELECT sku_code FROM skus GROUP BY sku_code HAVING COUNT(*) > 1) t"
        )).scalar()
        print(f"[*] 校验：超范围({over}) / 重复({dup})")
        if over or dup:
            raise RuntimeError("sku_code 校验失败：存在超范围或重复值")


if __name__ == "__main__":
    migrate()
    print("MIGRATE SKU_CODE DONE")
