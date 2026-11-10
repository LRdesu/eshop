"""Pydantic 请求/响应模型（v2）。"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------- 认证 ----------------
class RegisterReq(BaseModel):
    username: str
    password: str
    phone: Optional[str] = None
    nickname: Optional[str] = None
    as_merchant: bool = False                       # 是否注册为商家（开店）
    shop_name: Optional[str] = None
    shop_description: Optional[str] = None
    shop_logo: Optional[str] = None


class LoginReq(BaseModel):
    username: str
    password: str


class TokenResp(BaseModel):
    token: str
    user_id: int
    username: str
    nickname: Optional[str] = None


class UserResp(ORMModel):
    id: int
    username: str
    nickname: Optional[str] = None
    phone: Optional[str] = None
    points: int = 0


# ---------------- 地址 ----------------
class AddressCreate(BaseModel):
    receiver: str
    phone: str
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    detail: str
    is_default: int = 0


class AddressUpdate(AddressCreate):
    pass


class AddressResp(ORMModel):
    id: int
    user_id: int
    receiver: str
    phone: str
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    detail: str
    is_default: int = 0


# ---------------- 商品 / SKU / 评价 ----------------
class SkuResp(ORMModel):
    id: int
    sku_code: int
    product_id: int
    spec: str
    price: Decimal
    stock: int
    image: Optional[str] = None


class ProductResp(ORMModel):
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    category_id: Optional[int] = None
    shop_id: Optional[int] = None
    shop_name: Optional[str] = None
    shop_logo: Optional[str] = None
    shop_rating: Optional[float] = None
    sales: Optional[int] = 0
    cover: Optional[str] = None
    gallery: Optional[str] = None
    skus: List[SkuResp] = []


class CategoryResp(ORMModel):
    id: int
    name: str
    icon: Optional[str] = None
    sort: int = 0


class ShopResp(ORMModel):
    id: int
    name: str
    logo: Optional[str] = None
    description: Optional[str] = None
    rating: Optional[Decimal] = None
    status: int = 1
    follower_count: Optional[int] = None


class ReviewCreate(BaseModel):
    order_id: int
    sku_id: int
    rating: int = Field(ge=1, le=5)
    content: Optional[str] = None
    images: Optional[str] = None


class ReviewResp(ORMModel):
    id: int
    order_id: int
    sku_id: int
    user_id: int
    rating: int
    content: Optional[str] = None
    images: Optional[str] = None
    created_at: Optional[datetime] = None


# ---------------- 购物车 ----------------
class CartAdd(BaseModel):
    sku_id: int
    quantity: int = 1


class CartUpdate(BaseModel):
    quantity: int


class CartItemResp(ORMModel):
    id: int
    user_id: int
    sku_id: int
    quantity: int
    sku: Optional[SkuResp] = None
    product_name: Optional[str] = None


# ---------------- 优惠券 ----------------
class CouponResp(ORMModel):
    id: int
    shop_id: Optional[int] = None
    name: str
    type: str
    threshold: Decimal
    value: Decimal
    scope: str
    scope_value: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None


class UserCouponResp(ORMModel):
    id: int
    user_id: int
    coupon_id: int
    status: int
    order_id: Optional[int] = None
    obtained_at: Optional[datetime] = None
    coupon: Optional[CouponResp] = None


# ---------------- 订单 ----------------
class OrderPreviewItem(BaseModel):
    sku_id: int
    quantity: int


class OrderPreviewReq(BaseModel):
    items: List[OrderPreviewItem]
    address_id: int
    coupon_id: Optional[int] = None
    shipping_coupon_id: Optional[int] = None
    use_points: bool = False  # 是否使用淘金币抵扣


class AvailableCoupon(BaseModel):
    user_coupon_id: int
    coupon: CouponResp
    applicable: bool
    reason: Optional[str] = None


class OrderPreviewResp(BaseModel):
    goods_amount: Decimal
    discount_amount: Decimal
    points_discount: Decimal = Decimal("0")
    points_used: int = 0
    points_available: int = 0
    shipping_fee: Decimal
    pay_amount: Decimal
    items: List[dict]
    available_coupons: List[AvailableCoupon] = []
    available_shipping_coupons: List[AvailableCoupon] = []


class OrderCreateReq(BaseModel):
    items: List[OrderPreviewItem]
    address_id: int
    coupon_id: Optional[int] = None
    shipping_coupon_id: Optional[int] = None
    use_points: bool = False


class OrderItemResp(ORMModel):
    id: int
    order_id: int
    sku_id: int
    product_id: int
    quantity: int
    price: Decimal
    goods_amount: Decimal
    discount_amount: Decimal
    pay_amount: Decimal
    sku_spec: Optional[str] = None
    product_name: Optional[str] = None
    product_cover: Optional[str] = None
    product_cover: Optional[str] = None


class OrderResp(ORMModel):
    id: int
    order_no: str
    user_id: int
    address_id: int
    goods_amount: Decimal
    discount_amount: Decimal
    points_used: int = 0
    points_discount: Decimal = Decimal("0")
    shipping_fee: Decimal
    pay_amount: Decimal
    coupon_id: Optional[int] = None
    shipping_coupon_id: Optional[int] = None
    pay_status: int
    order_status: int
    expire_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    items: List[OrderItemResp] = []
    address: Optional[AddressResp] = None
    shipment: Optional["ShipSummary"] = None


class ShipSummary(ORMModel):
    """订单列表/详情附带的最小运单摘要，用于前端判断是否可推进物流。"""
    id: int
    ship_status: int
    ship_status_text: Optional[str] = None


# ---------------- 支付 ----------------
class PaymentCreateResp(BaseModel):
    payment_no: str
    order_no: str
    amount: Decimal
    channel: str
    expire_at: Optional[datetime] = None


class PayReq(BaseModel):
    channel: str = "BALANCE"


class CallbackReq(BaseModel):
    payment_no: str
    status: str = "SUCCESS"  # SUCCESS / FAIL
    trade_no: Optional[str] = None


# ---------------- 履约 ----------------
class ShipReq(BaseModel):
    carrier: str = "顺丰"
    tracking_no: Optional[str] = None


class TraceResp(ORMModel):
    id: int
    shipment_id: int
    node: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None
    occurred_at: Optional[datetime] = None


class ShipmentResp(ORMModel):
    id: int
    order_id: int
    carrier: Optional[str] = None
    tracking_no: Optional[str] = None
    ship_status: int
    ship_status_text: Optional[str] = None
    from_city: Optional[str] = None
    to_city: Optional[str] = None
    shipped_at: Optional[datetime] = None
    traces: List[TraceResp] = []


# ---------------- 售后 ----------------
class AfterSaleCreate(BaseModel):
    order_id: int
    type: str  # REFUND / RETURN / EXCHANGE
    sku_id: int
    quantity: int = 1
    reason: Optional[str] = None


class ReturnShipReq(BaseModel):
    carrier: str = "顺丰"
    tracking_no: Optional[str] = None


class AfterSaleResp(ORMModel):
    id: int
    as_no: str
    order_id: int
    user_id: int
    type: str
    sku_id: int
    quantity: int
    reason: Optional[str] = None
    refund_amount: Decimal
    status: int
    created_at: Optional[datetime] = None
    return_address: Optional[str] = None
    return_shipment: Optional[dict] = None


# ---------------- 会员 / RFM ----------------
class MemberResp(BaseModel):
    user_id: int
    username: str
    nickname: Optional[str] = None
    points: int
    rfm_level: Optional[str] = None
    rfm_score: Optional[str] = None
    recency: Optional[int] = None
    frequency: Optional[int] = None
    monetary: Optional[Decimal] = None
    tags: Optional[str] = None


# ---------------- 商家后台 ----------------
class AdminLoginReq(BaseModel):
    username: str
    password: str


class AdminProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    cover: Optional[str] = None
    gallery: Optional[str] = None


class AdminProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    cover: Optional[str] = None
    gallery: Optional[str] = None


class AdminSkuCreate(BaseModel):
    spec: str
    price: Decimal
    stock: int = 0
    image: Optional[str] = None


class AdminSkuUpdate(BaseModel):
    spec: Optional[str] = None
    price: Optional[Decimal] = None
    stock: Optional[int] = None
    image: Optional[str] = None


class AdminStockReq(BaseModel):
    """库存调整：直接设定目标库存值。"""
    stock: int


class AdminCouponCreate(BaseModel):
    name: str
    type: str = "FULL"          # FULL / DISCOUNT / SHIPPING
    threshold: Decimal = Decimal("0")
    value: Decimal
    scope: str = "ALL"          # ALL / CATEGORY / PRODUCT
    scope_value: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    total: int = 100
    per_limit: int = 1


class AdminShippingFeeUpdate(BaseModel):
    fee: Decimal


class AdminOrderShipReq(BaseModel):
    carrier: str = "顺丰速运"


# ---------------- 活动 ----------------
class ActivityCreate(BaseModel):
    name: str
    type: str = "FULL"          # FULL 满减 / DISCOUNT 折扣
    threshold: Decimal = Decimal("0")
    value: Decimal
    start_at: datetime
    end_at: datetime
    description: Optional[str] = None


class ActivityUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    threshold: Optional[Decimal] = None
    value: Optional[Decimal] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    description: Optional[str] = None


# ---------------- 店铺权限管理 ----------------
class ShopStatusUpdate(BaseModel):
    status: int  # 1 营业 / 0 休息(下架)


# ---------------- 店铺 AI 助手 ----------------
class ShopAiAsk(BaseModel):
    shop_id: int
    question: str

