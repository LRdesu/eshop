"""配置：优先读 shell 环境变量，缺省时从 backend/.env 载入。"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_env(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env(os.path.join(BASE_DIR, ".env"))


class Config:
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
    DB_NAME = os.getenv("DB_NAME", "eshop")

    SECRET_KEY = os.getenv("SECRET_KEY", "eshop-dev-secret-key-change-me")
    TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", "48"))

    # 支付超时关单时长（分钟），需求要求 15~30 分钟
    PAY_EXPIRE_MINUTES = int(os.getenv("PAY_EXPIRE_MINUTES", "30"))
    # 签收后自动确认收货天数
    AUTO_CONFIRM_DAYS = int(os.getenv("AUTO_CONFIRM_DAYS", "7"))
    # 每消费 1 元获得的积分
    POINTS_PER_YUAN = int(os.getenv("POINTS_PER_YUAN", "1"))

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )


config = Config()
