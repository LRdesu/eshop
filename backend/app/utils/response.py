"""统一返回结构：{code, msg, data}。"""
from typing import Any, Optional


def ok(data: Any = None, msg: str = "ok"):
    return {"code": 0, "msg": msg, "data": data}


def fail(msg: str = "error", code: int = 1, data: Any = None):
    return {"code": code, "msg": msg, "data": data}
