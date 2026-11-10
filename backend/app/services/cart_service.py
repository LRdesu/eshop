"""购物车服务。"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import CartItem, Sku, Product
from app.schemas import CartItemResp, SkuResp
from app.utils.money import money


def list_cart(db: Session, user_id: int):
    items = db.query(CartItem).filter(CartItem.user_id == user_id).order_by(CartItem.id.desc()).all()
    result = []
    for it in items:
        resp = CartItemResp.model_validate(it)
        sku = db.get(Sku, it.sku_id)
        if sku:
            resp.sku = SkuResp.model_validate(sku)
            prod = db.get(Product, sku.product_id)
            resp.product_name = prod.name if prod else None
        result.append(resp)
    return result


def add_cart(db: Session, user_id: int, sku_id: int, quantity: int) -> CartItem:
    sku = db.get(Sku, sku_id)
    if not sku:
        raise HTTPException(404, "SKU 不存在")
    if sku.stock < quantity:
        raise HTTPException(400, "库存不足")
    exist = db.query(CartItem).filter(
        CartItem.user_id == user_id, CartItem.sku_id == sku_id
    ).first()
    if exist:
        if exist.quantity + quantity > sku.stock:
            raise HTTPException(400, "库存不足")
        exist.quantity += quantity
        db.commit()
        db.refresh(exist)
        return exist
    item = CartItem(user_id=user_id, sku_id=sku_id, quantity=quantity)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_cart(db: Session, user_id: int, item_id: int, quantity: int) -> CartItem:
    item = db.get(CartItem, item_id)
    if not item or item.user_id != user_id:
        raise HTTPException(404, "购物车项不存在")
    sku = db.get(Sku, item.sku_id)
    if quantity > sku.stock:
        raise HTTPException(400, "库存不足")
    item.quantity = quantity
    db.commit()
    db.refresh(item)
    return item


def remove_cart(db: Session, user_id: int, item_id: int):
    item = db.get(CartItem, item_id)
    if not item or item.user_id != user_id:
        raise HTTPException(404, "购物车项不存在")
    db.delete(item)
    db.commit()
    return {"deleted": item_id}
