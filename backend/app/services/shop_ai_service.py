"""店铺 AI 助手：本地规则问答（零成本，无外部大模型）。

根据买家问题做关键词匹配，返回结构化回答。知识来源：
- 店铺基础信息（名称、评分、在售商品数）
- 商品信息（价格、库存、是否包邮）
- 运费规则（上海仓发货，省内/省外）
- 物流时效（正向 6 节点、逆向退货 4 节点）
- 售后政策（7天无理由、退货退款、换货）
"""

# 关键词 -> 回答类别
KEYWORDS = {
    "发货": "shipment",
    "多久": "shipment",
    "几天": "shipment",
    "什么时候": "shipment",
    "物流": "shipment",
    "快递": "shipment",
    "运费": "shipping",
    "邮费": "shipping",
    "包邮": "shipping",
    "免邮": "shipping",
    "售后": "aftersale",
    "退货": "aftersale",
    "退款": "aftersale",
    "换货": "aftersale",
    "七天": "aftersale",
    "无理由": "aftersale",
    "优惠": "coupon",
    "券": "coupon",
    "折扣": "coupon",
    "活动": "coupon",
    "库存": "stock",
    "有货": "stock",
    "现货": "stock",
    "价格": "price",
    "多少钱": "price",
    "便宜": "price",
    "营业": "business",
    "开门": "business",
    "时间": "business",
    "客服": "business",
    "联系": "business",
    "正品": "quality",
    "质量": "quality",
    "假货": "quality",
    "保质": "quality",
    "自营": "quality",
}


def _match_category(question: str):
    q = question or ""
    for kw, cat in KEYWORDS.items():
        if kw in q:
            return cat
    return "default"


def answer(db, shop, question: str) -> dict:
    """返回 {reply, category}。shop 为 Shop 对象。"""
    cat = _match_category(question)
    from app.models import Product, Sku, ShippingFee, Activity, ActivityShop

    # 店铺概况
    pcount = db.query(Product).filter(Product.shop_id == shop.id).count()
    rating = float(shop.rating) if shop.rating is not None else 5.0

    # 运费规则（取首条作参考）
    fee_rows = db.query(ShippingFee).order_by(ShippingFee.id.asc()).all()
    fee_txt = "、".join(f"{f.region}:¥{float(f.fee)}" for f in fee_rows[:3]) if fee_rows else "按地区计费"

    # 店铺最低价商品
    cheapest = None
    lowest = db.query(Sku).join(Product, Sku.product_id == Product.id).filter(
        Product.shop_id == shop.id).order_by(Sku.price.asc()).first()
    if lowest:
        p = db.get(Product, lowest.product_id)
        cheapest = (p.name if p else "", float(lowest.price), lowest.stock)

    # 进行中的活动
    from datetime import datetime
    now = datetime.now()
    joined_act = db.query(Activity).join(
        ActivityShop, ActivityShop.activity_id == Activity.id).filter(
        ActivityShop.shop_id == shop.id,
        Activity.start_at <= now, Activity.end_at >= now,
    ).all()

    if cat == "shipment":
        reply = (
            f"您好，本店商品从上海仓发货，下单后一般 24 小时内出库。"
            f"物流会依次经过：发货→拣货→揽收→运输→派送→签收，全程约 1-3 天送达（收货地南京）。"
            f"发货后您可在「订单详情」实时查看物流轨迹。"
        )
    elif cat == "shipping":
        reply = (
            f"本店运费按地区计费（{fee_txt}）。"
            f"上海仓库发货：上海视为省内，其余地区（含南京）按省外计费。"
            f"部分商品满额可包邮，下单结算页会显示最终运费，也可使用运费券抵扣。"
        )
    elif cat == "aftersale":
        reply = (
            f"本店支持 7 天无理由退货。售后流程：在「订单详情」发起售后申请 → 商家审核 → "
            f"填写退货物流寄回（南京→上海仓）→ 仓库签收后自动退款/换货。"
            f"仅退款无需寄回，退货退款和换货需寄回商品。"
        )
    elif cat == "coupon":
        act_txt = "；".join(a.name for a in joined_act) if joined_act else "暂无进行中的平台活动"
        reply = (
            f"您可前往「领券中心」领取本店优惠券和平台券。"
            f"本店参与的进行中活动：{act_txt}。领券后下单结算时可抵扣。"
        )
    elif cat == "stock":
        if cheapest:
            reply = f"本店多数商品现货充足。目前最低价商品「{cheapest[0]}」库存 {cheapest[2]} 件，可正常下单。"
        else:
            reply = "本店商品均可正常下单，库存以商品详情页实时显示为准。"
    elif cat == "price":
        if cheapest:
            reply = f"本店商品价格实惠，目前最低仅 ¥{cheapest[1]:.2f}（「{cheapest[0]}」）。具体以商品详情页标价为准。"
        else:
            reply = "本店商品性价比高，具体价格请查看商品详情页。"
    elif cat == "business":
        reply = (
            f"本店「{shop.name}」正常营业中（评分 {rating}）。"
            f"如需人工客服，可在订单详情页发起售后或留言，我们会在工作时间尽快回复。"
        )
    elif cat == "quality":
        reply = (
            f"本店「{shop.name}」承诺正品保障，所有商品支持 7 天无理由退货，"
            f"如遇质量问题可走售后流程（退货退款/换货），请放心购买。"
        )
    else:
        act_txt = "、".join(a.name for a in joined_act) if joined_act else "暂无"
        reply = (
            f"您好，这里是「{shop.name}」智能助手（评分 {rating}，在售 {pcount} 件商品）。"
            f"您可以问我：发货时间、运费、售后、优惠券、库存、价格等问题。"
            f"本店当前进行中活动：{act_txt}。"
        )

    return {"reply": reply, "category": cat}
