"""ORM 模型：映射 eshop 库 18 张表（与 db/schema.sql 字段一一对应）。"""
from decimal import Decimal
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DECIMAL, DateTime, Text, ForeignKey, SmallInteger, func,
)
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(100), nullable=False)
    phone = Column(String(20))
    nickname = Column(String(50))
    points = Column(Integer, default=0, nullable=False)
    role = Column(SmallInteger, default=0, nullable=False)  # 0买家 1商家(开店) 2平台管理员
    created_at = Column(DateTime, default=func.now())


class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    province = Column(String(50))
    city = Column(String(50))
    district = Column(String(50))
    detail = Column(String(200), nullable=False)
    is_default = Column(SmallInteger, default=0)
    created_at = Column(DateTime, default=func.now())


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    category = Column(String(50))            # 冗余类名（兼容历史/前端展示），新数据由 category_id 回填
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    sales = Column(Integer, default=0, nullable=False)  # 销量（演示数据填充）
    cover = Column(String(255))
    gallery = Column(Text)
    created_at = Column(DateTime, default=func.now())


class Sku(Base):
    __tablename__ = "skus"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sku_code = Column(Integer, unique=True, nullable=False, index=True)  # 独立 SKU 编码，5 位数（10000-99999），全局唯一
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    spec = Column(String(100), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    stock = Column(Integer, default=0, nullable=False)
    image = Column(String(255))
    created_at = Column(DateTime, default=func.now())


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(SmallInteger, nullable=False)
    content = Column(Text)
    images = Column(String(512))
    created_at = Column(DateTime, default=func.now())


class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=func.now())


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(32), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    address_id = Column(Integer, ForeignKey("addresses.id"), nullable=False)
    goods_amount = Column(DECIMAL(10, 2), default=0, nullable=False)
    discount_amount = Column(DECIMAL(10, 2), default=0, nullable=False)
    points_used = Column(Integer, default=0, nullable=False)       # 淘金币抵扣所用币数
    points_discount = Column(DECIMAL(10, 2), default=0, nullable=False)  # 金币抵扣金额
    shipping_fee = Column(DECIMAL(10, 2), default=0, nullable=False)
    pay_amount = Column(DECIMAL(10, 2), default=0, nullable=False)
    coupon_id = Column(Integer)
    shipping_coupon_id = Column(Integer)
    pay_status = Column(SmallInteger, default=0, nullable=False)
    order_status = Column(SmallInteger, default=0, nullable=False)
    expire_at = Column(DateTime)
    paid_at = Column(DateTime)
    confirmed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    goods_amount = Column(DECIMAL(10, 2), default=0, nullable=False)
    discount_amount = Column(DECIMAL(10, 2), default=0, nullable=False)
    pay_amount = Column(DECIMAL(10, 2), default=0, nullable=False)


class Shipment(Base):
    __tablename__ = "shipments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 一个订单可有多条运单：正向发货 forward + 换货重发 exchange（故去掉 order_id 唯一约束）
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    kind = Column(String(20), default="forward", nullable=False)  # forward=正向发货 exchange=换货重发
    carrier = Column(String(50))
    tracking_no = Column(String(50))
    # 0待发货 1已发货 2仓库拣货 3已揽收 4运输中 5派送中 6已签收
    ship_status = Column(SmallInteger, default=0, nullable=False)
    from_city = Column(String(50))  # 发货城市（仓库所在，统一上海）
    to_city = Column(String(50))  # 收货城市（统一南京）
    shipped_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())


class ShipmentTrace(Base):
    __tablename__ = "shipment_traces"
    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    node = Column(String(50))
    city = Column(String(50))  # 轨迹发生城市
    description = Column(String(255))
    occurred_at = Column(DateTime)


class Coupon(Base):
    __tablename__ = "coupons"
    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=True)  # 归属店铺，NULL 为平台级
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # FULL / DISCOUNT / SHIPPING
    threshold = Column(DECIMAL(10, 2), default=0, nullable=False)
    value = Column(DECIMAL(10, 2), nullable=False)
    scope = Column(String(20), default="ALL", nullable=False)
    scope_value = Column(String(100))
    valid_from = Column(DateTime)
    valid_to = Column(DateTime)
    total = Column(Integer, default=0, nullable=False)
    per_limit = Column(Integer, default=1, nullable=False)
    deleted = Column(SmallInteger, default=0, nullable=False)  # 0正常 1已下架(卖家删除)
    created_at = Column(DateTime, default=func.now())


class UserCoupon(Base):
    __tablename__ = "user_coupons"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=False)
    status = Column(SmallInteger, default=0, nullable=False)  # 0未用 1已用 2作废
    order_id = Column(Integer)
    obtained_at = Column(DateTime, default=func.now())
    used_at = Column(DateTime)


class ShippingFee(Base):
    __tablename__ = "shipping_fees"
    id = Column(Integer, primary_key=True, autoincrement=True)
    region = Column(String(50), unique=True, nullable=False)
    fee = Column(DECIMAL(10, 2), nullable=False)


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_no = Column(String(40), unique=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel = Column(String(20), default="BALANCE", nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    status = Column(SmallInteger, default=0, nullable=False)  # 0待付 1成功 2关闭
    expire_at = Column(DateTime)
    paid_at = Column(DateTime)
    callback_data = Column(Text)
    created_at = Column(DateTime, default=func.now())


class Refund(Base):
    __tablename__ = "refunds"
    id = Column(Integer, primary_key=True, autoincrement=True)
    refund_no = Column(String(40), unique=True, nullable=False)
    after_sale_id = Column(Integer, ForeignKey("after_sales.id"), nullable=False)
    payment_no = Column(String(40))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    channel = Column(String(20))
    status = Column(SmallInteger, default=0, nullable=False)  # 0待退 1成功 2失败
    reason = Column(String(255))
    created_at = Column(DateTime, default=func.now())
    finished_at = Column(DateTime)


class AfterSale(Base):
    __tablename__ = "after_sales"
    id = Column(Integer, primary_key=True, autoincrement=True)
    as_no = Column(String(40), unique=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(20), nullable=False)  # REFUND / RETURN / EXCHANGE
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    reason = Column(String(255))
    refund_amount = Column(DECIMAL(10, 2), default=0, nullable=False)
    status = Column(SmallInteger, default=0, nullable=False)  # 0申请 1同意 2退款中 3完成 4拒绝
    created_at = Column(DateTime, default=func.now())
    handled_at = Column(DateTime)


class PointsLog(Base):
    __tablename__ = "points_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    point_delta = Column(Integer, nullable=False)
    type = Column(String(20), nullable=False)  # EARN / SPEND / REFUND
    ref_order_no = Column(String(32))
    remark = Column(String(255))
    created_at = Column(DateTime, default=func.now())


class UserTag(Base):
    __tablename__ = "user_tags"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    rfm_level = Column(String(20))
    rfm_score = Column(String(20))
    recency = Column(Integer)
    frequency = Column(Integer)
    monetary = Column(DECIMAL(10, 2))
    tags = Column(String(512))
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Shop(Base):
    __tablename__ = "shops"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    logo = Column(String(255))
    description = Column(Text)
    rating = Column(DECIMAL(2, 1), default=Decimal("5.0"), nullable=False)  # 店铺综合评分
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)   # 所属商家账号
    status = Column(SmallInteger, default=1, nullable=False)  # 1营业 0休息
    created_at = Column(DateTime, default=func.now())


class ReturnShipment(Base):
    """退货逆向物流：买家把商品寄回仓库/商家（南京→上海）。"""
    __tablename__ = "return_shipments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    after_sale_id = Column(Integer, ForeignKey("after_sales.id"), unique=True, nullable=False)
    carrier = Column(String(50))
    tracking_no = Column(String(50))
    # 0待寄回 1已揽收 2运输中 3已签收(入库)
    return_status = Column(SmallInteger, default=0, nullable=False)
    from_city = Column(String(50))   # 寄出城市（买家，统一南京）
    to_city = Column(String(50))     # 退货目的地（仓库，统一上海）
    shipped_at = Column(DateTime)
    received_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())


class ReturnTrace(Base):
    """退货物流轨迹。"""
    __tablename__ = "return_traces"
    id = Column(Integer, primary_key=True, autoincrement=True)
    return_shipment_id = Column(Integer, ForeignKey("return_shipments.id"), nullable=False)
    node = Column(String(50))
    city = Column(String(50))
    description = Column(String(255))
    occurred_at = Column(DateTime)


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    icon = Column(String(255))         # 图标（emoji 或图片 URL）
    sort = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now())


class Activity(Base):
    """平台发起的营销活动（满减/折扣），商家报名参加。"""
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # FULL 满减 / DISCOUNT 折扣
    threshold = Column(DECIMAL(10, 2), default=0, nullable=False)  # 满门槛
    value = Column(DECIMAL(10, 2), nullable=False)  # 满减金额 或 折扣率(0.9=九折)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    status = Column(SmallInteger, default=0, nullable=False)  # 0未开始 1进行中 2已结束
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())


class ActivityShop(Base):
    """活动-店铺报名（多对多，附状态）。"""
    __tablename__ = "activity_shops"
    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)
    joined_at = Column(DateTime, default=func.now())



class Favorite(Base):
    """用户收藏的商品（多对多中间表，附时间）。"""
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())


class Follow(Base):
    """用户关注的店铺（多对多中间表，附时间）。"""
    __tablename__ = "follows"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())


# 导出所有模型，便于 `from app.models import User, Order, ...`
__all__ = [
    "User", "Address", "Product", "Sku", "Review", "CartItem", "Order", "OrderItem",
    "Shipment", "ShipmentTrace", "Coupon", "UserCoupon", "ShippingFee", "Payment",
    "Refund", "AfterSale", "PointsLog", "UserTag", "Shop", "Category",
    "Favorite", "Follow", "ReturnShipment", "ReturnTrace",
    "Activity", "ActivityShop",
]
