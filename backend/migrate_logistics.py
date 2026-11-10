# -*- coding: utf-8 -*-
"""物流系统迁移：新增城市字段，并把旧的 4 段状态码重映射到新的 7 段链路。

旧语义 -> 新语义：
  1 揽收   -> 3 已揽收
  2 运输中 -> 4 运输中
  3 派送   -> 5 派送中
  4 已签收 -> 6 已签收

幂等：字段已存在则跳过；重映射只在字段首次新增时执行一次（由 shipments.from_city 是否为新加判断）。
用法：
    cd backend && .venv/Scripts/python.exe migrate_logistics.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymysql
from app.config import config

DDL = [
    ("shipments", "from_city", "ALTER TABLE shipments ADD COLUMN from_city VARCHAR(50) COMMENT '发货城市（仓库所在，统一上海）'"),
    ("shipments", "to_city", "ALTER TABLE shipments ADD COLUMN to_city VARCHAR(50) COMMENT '收货城市（统一南京）'"),
    ("shipment_traces", "city", "ALTER TABLE shipment_traces ADD COLUMN city VARCHAR(50) COMMENT '发生城市'"),
]

# 旧 -> 新，降序执行避免覆盖
REMAP = [(4, 6), (3, 5), (2, 4), (1, 3)]


def column_exists(cur, table, column):
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
        (config.DB_NAME, table, column),
    )
    return cur.fetchone()[0] > 0


def main():
    conn = pymysql.connect(
        host=config.DB_HOST, port=config.DB_PORT, user=config.DB_USER,
        password=config.DB_PASSWORD, database=config.DB_NAME, charset="utf8mb4",
    )
    added_any = False
    try:
        with conn.cursor() as cur:
            for table, column, ddl in DDL:
                if column_exists(cur, table, column):
                    print("SKIP (exists): %s.%s" % (table, column))
                    continue
                cur.execute(ddl)
                print("ADDED: %s.%s" % (table, column))
                added_any = True

            if added_any:
                for old, new in REMAP:
                    cur.execute("UPDATE shipments SET ship_status=%s WHERE ship_status=%s", (new, old))
                print("REMAP ship_status: 1->3, 2->4, 3->5, 4->6")
            else:
                print("SKIP remap (no new columns, already migrated)")
        conn.commit()
        print("MIGRATION DONE")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
