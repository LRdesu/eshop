"""依赖：解析 Bearer Token 拿到当前登录用户。"""
from typing import Optional
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, Shop
from app.utils.security import decode_token


def get_current_user(authorization: str = Header(None)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:]
    try:
        payload = decode_token(token)
        uid = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="登录已失效")
    db: Session = SessionLocal()
    user = db.get(User, uid)
    db.close()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def get_admin_user(authorization: str = Header(None)) -> User:
    """商家后台鉴权：需登录且角色为商家(1)或平台管理员(2)。"""
    user = get_current_user(authorization)
    if (user.role or 0) not in (1, 2):
        raise HTTPException(status_code=403, detail="无商家后台权限")
    return user


def get_platform_admin(authorization: str = Header(None)) -> User:
    """仅平台管理员(role==2)可访问（运费规则等平台级配置）。"""
    user = get_current_user(authorization)
    if (user.role or 0) != 2:
        raise HTTPException(status_code=403, detail="仅平台管理员可操作")
    return user


def resolve_shop_id(user: User, db: Session):
    """当前管理员可操作的店铺 id 列表；平台管理员返回 None（看全部）。
    商家(role==1)可拥有多个店铺（≤5），返回其拥有的全部店铺 id；
    若没有任何店铺则返回 [-1]，使按店过滤结果为空，避免越权。"""
    if (user.role or 0) == 2:
        return None
    ids = [s.id for s in db.query(Shop.id).filter(Shop.owner_user_id == user.id).all()]
    return ids if ids else [-1]


def get_optional_user_id(authorization: str = Header(None)) -> Optional[int]:
    """尝试从 Bearer Token 解析用户 id；缺失或无效返回 None（访客态查询用）。"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return int(decode_token(authorization[7:])["sub"])
    except Exception:
        return None
