"""会员服务：积分查询、RFM 分层打标签、每日签到领淘金币。"""
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import User, Order, UserTag, PointsLog
from app.schemas import MemberResp

# 每日签到奖励淘金币数
CHECKIN_POINTS = 20


def get_member(db: Session, user_id: int) -> MemberResp:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    tag = db.query(UserTag).filter(UserTag.user_id == user_id).first()
    return MemberResp(
        user_id=user.id, username=user.username, nickname=user.nickname,
        points=user.points or 0,
        rfm_level=tag.rfm_level if tag else None,
        rfm_score=tag.rfm_score if tag else None,
        recency=tag.recency if tag else None,
        frequency=tag.frequency if tag else None,
        monetary=tag.monetary if tag else None,
        tags=tag.tags if tag else None,
    )


def checkin_status(db: Session, user_id: int) -> dict:
    """返回今日是否已签到、以及连续签到天数。"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_log = db.query(PointsLog).filter(
        PointsLog.user_id == user_id, PointsLog.type == "SIGNIN",
        PointsLog.created_at >= today,
    ).first()
    return {"checked": today_log is not None, "reward": CHECKIN_POINTS}


def do_checkin(db: Session, user_id: int) -> dict:
    """执行签到：每日一次，发放 CHECKIN_POINTS 淘金币。
    重复签到抛出 HTTPException(400)，由路由层 catch 后返回业务错误。"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    already = db.query(PointsLog).filter(
        PointsLog.user_id == user_id, PointsLog.type == "SIGNIN",
        PointsLog.created_at >= today,
    ).first()
    if already:
        raise HTTPException(400, "今日已签到，明天再来吧")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    user.points = (user.points or 0) + CHECKIN_POINTS
    db.add(PointsLog(user_id=user_id, point_delta=CHECKIN_POINTS, type="SIGNIN",
                     remark=f"每日签到领 {CHECKIN_POINTS} 淘金币"))
    db.commit()
    return {"reward": CHECKIN_POINTS, "points": user.points}


def _rfm_level(r: int, f: int, m: int) -> str:
    if f == 0:
        return "新客"
    rs = 3 if r <= 7 else (2 if r <= 30 else 1)
    fs = 3 if f >= 5 else (2 if f >= 2 else 1)
    ms = 3 if m >= 1000 else (2 if m >= 200 else 1)
    if rs == 3 and fs == 3 and ms == 3:
        return "重要价值客户"
    if rs == 1 and fs >= 2:
        return "重要挽留客户"
    if fs >= 2:
        return "重要保持客户"
    if fs <= 1 and ms <= 1:
        return "一般发展客户"
    return "一般客户"


def refresh_rfm(db: Session, user_id: int) -> UserTag:
    paid = db.query(Order).filter(Order.user_id == user_id, Order.pay_status == 1).all()
    frequency = len(paid)
    monetary = sum((o.pay_amount for o in paid), 0) if paid else 0
    if paid:
        last = max((o.paid_at for o in paid if o.paid_at), default=None)
        recency = (datetime.now() - last).days if last else 999
    else:
        recency = 999
    level = _rfm_level(recency, frequency, float(monetary))
    score = f"R{min(recency,99)}F{frequency}M{int(monetary)}"

    tag = db.query(UserTag).filter(UserTag.user_id == user_id).first()
    if not tag:
        tag = UserTag(user_id=user_id)
        db.add(tag)
    tag.recency = recency
    tag.frequency = frequency
    tag.monetary = monetary
    tag.rfm_level = level
    tag.rfm_score = score
    tag.tags = level
    db.commit()
    db.refresh(tag)
    return tag
