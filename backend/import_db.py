"""从 .env 读取数据库配置并执行 db/schema.sql（重建 eshop 库）。

用法：
    cd backend
    python import_db.py
"""
import os
import pymysql

BASE = os.path.dirname(os.path.abspath(__file__))


def load_env(path):
    cfg = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg


def main():
    cfg = load_env(os.path.join(BASE, ".env"))
    host = cfg.get("DB_HOST", "127.0.0.1")
    port = int(cfg.get("DB_PORT", "3306"))
    user = cfg.get("DB_USER", "root")
    pwd = cfg.get("DB_PASSWORD", "")
    name = cfg.get("DB_NAME", "eshop")

    schema_path = os.path.join(BASE, "..", "db", "schema.sql")
    with open(schema_path, encoding="utf-8") as f:
        sql = f.read()

    conn = pymysql.connect(host=host, port=port, user=user, password=pwd,
                           charset="utf8mb4", connect_timeout=5)
    cur = conn.cursor()
    stmts = []
    for blk in sql.split(";"):
        lines = [l for l in blk.splitlines()
                 if not l.strip().startswith("--") and l.strip()]
        if lines:
            stmts.append("\n".join(lines))
    for s in stmts:
        cur.execute(s)
    print(f"executed {len(stmts)} statements")

    conn.select_db(name)
    cur.execute("SHOW TABLES")
    tables = sorted(r[0] for r in cur.fetchall())
    print("tables(%d):" % len(tables), tables)
    conn.commit()
    conn.close()
    print("IMPORT OK")


if __name__ == "__main__":
    main()
