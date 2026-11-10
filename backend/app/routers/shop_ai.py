"""店铺 AI 助手接口：买家在店铺内咨询，本地规则问答。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_optional_user_id
from app.models import Shop
from app.schemas import ShopAiAsk
from app.services import shop_ai_service
from app.utils.response import ok, fail

router = APIRouter(prefix="/api/v1", tags=["shop-ai"])


@router.post("/shop-ai/ask")
def ask(req: ShopAiAsk, db: Session = Depends(get_db), user_id: int = Depends(get_optional_user_id)):
    shop = db.get(Shop, req.shop_id)
    if not shop:
        return fail("店铺不存在")
    if shop.status != 1:
        return fail("店铺休息中，暂无法咨询")
    if not req.question or not req.question.strip():
        return fail("请输入要咨询的问题")
    result = shop_ai_service.answer(db, shop, req.question.strip())
    return ok({
        "shop_id": shop.id,
        "shop_name": shop.name,
        "question": req.question.strip(),
        **result,
    })
