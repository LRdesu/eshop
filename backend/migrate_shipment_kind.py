"""迁移：放宽 shipments.order_id 唯一约束（支持换货重发第二张运单），并新增 kind 列。
可直接重复运行（幂等）。
"""
from sqlalchemy import text
from app.database import engine


def migrate():
    with engine.connect() as conn:
        # 1) 找到并删除 order_id 上的外键（其依赖唯一索引）
        fk_res = conn.execute(text(
            "SELECT CONSTRAINT_NAME FROM information_schema.key_column_usage "
            "WHERE table_schema=DATABASE() AND table_name='shipments' "
            "AND referenced_table_name='orders'"
        ))
        fk_names = [row[0] for row in fk_res]
        for fk in fk_names:
            conn.execute(text(f"ALTER TABLE shipments DROP FOREIGN KEY `{fk}`"))
            print(f"[*] 已删除外键 {fk}")

        # 2) 删除 order_id 上的唯一索引（若存在）
        res = conn.execute(text(
            "SHOW INDEX FROM shipments WHERE Non_unique=0 AND Column_name='order_id'"
        ))
        idx_names = [row[2] for row in res]  # Key_name 在第 3 列
        for idx in idx_names:
            conn.execute(text(f"ALTER TABLE shipments DROP INDEX `{idx}`"))
            print(f"[*] 已删除唯一索引 {idx}")

        # 3) 重新添加非唯一外键（保留关联，去掉唯一约束）
        conn.execute(text(
            "ALTER TABLE shipments ADD CONSTRAINT fk_shipments_order_id "
            "FOREIGN KEY (order_id) REFERENCES orders(id)"
        ))
        print("[*] 已重建非唯一外键 fk_shipments_order_id")

        # 4) 新增 kind 列（若不存在）
        r = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema=DATABASE() AND table_name='shipments' AND column_name='kind'"
        ))
        if r.scalar() == 0:
            conn.execute(text(
                "ALTER TABLE shipments ADD COLUMN kind VARCHAR(20) NOT NULL DEFAULT 'forward' "
                "COMMENT 'forward=正向发货 exchange=换货重发'"
            ))
            print("[*] 已新增 kind 列")
        else:
            print("[*] kind 列已存在，跳过")

        conn.commit()
    print("== migrate_shipment_kind 完成 ==")


if __name__ == "__main__":
    migrate()
