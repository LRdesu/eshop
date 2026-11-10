"""端到端链路验证：登录→商品→加购→结算→下单→支付→发货→签收→售后退款。"""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000/api/v1"


def call(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def main():
    # 1. 登录演示买家
    s, d = call("POST", "/auth/login", {"username": "alice", "password": "alice123"})
    print("login", s, d.get("msg"))
    token = d["data"]["token"]

    # 2. 商品列表
    s, d = call("GET", "/products")
    prods = d["data"]
    print("products count", len(prods), "| first:", prods[0]["name"])
    sku1 = prods[0]["skus"][0]["id"]
    print("use sku_id", sku1, "price", prods[0]["skus"][0]["price"])

    # 3. 加购
    s, d = call("POST", "/cart", {"sku_id": sku1, "quantity": 2}, token)
    print("add cart", s, d.get("msg"))

    # 4. 结算预估价（先探测可用券，避免复用已占用的券导致失败）
    s, d = call("POST", "/orders/preview", {
        "items": [{"sku_id": sku1, "quantity": 2}],
        "address_id": 1,
    }, token)
    if not d.get("data"):
        print("probe preview FAILED", s, d)
        return
    probe = d["data"]
    goods_coupons = probe.get("available_coupons") or []
    ship_coupons = probe.get("available_shipping_coupons") or []
    coupon_id = goods_coupons[0]["coupon"]["id"] if goods_coupons else None
    ship_coupon_id = ship_coupons[0]["coupon"]["id"] if ship_coupons else None
    print("available goods coupons:", [c["coupon"]["name"] for c in goods_coupons])
    print("available shipping coupons:", [c["coupon"]["name"] for c in ship_coupons])

    s, d = call("POST", "/orders/preview", {
        "items": [{"sku_id": sku1, "quantity": 2}],
        "address_id": 1, "coupon_id": coupon_id, "shipping_coupon_id": ship_coupon_id,
    }, token)
    pv = d["data"]
    print("preview", s, "goods", pv["goods_amount"], "discount", pv["discount_amount"],
          "ship", pv["shipping_fee"], "pay", pv["pay_amount"],
          "| avail_goods", len(pv["available_coupons"]), "avail_ship", len(pv["available_shipping_coupons"]))

    # 5. 下单
    s, d = call("POST", "/orders", {
        "items": [{"sku_id": sku1, "quantity": 2}],
        "address_id": 1, "coupon_id": coupon_id, "shipping_coupon_id": ship_coupon_id,
    }, token)
    if not d.get("data"):
        print("create order FAILED", s, d)
        return
    order = d["data"]
    print("create order", s, "no", order["order_no"], "pay", order["pay_amount"],
          "status", order["order_status"], "pay_status", order["pay_status"])
    order_id = order["id"]
    # 校验分摊：明细分摊合计 == 订单优惠
    items = order["items"]
    disc_sum = sum(float(i["discount_amount"]) for i in items)
    print("  分摊校验: 行优惠合计", round(disc_sum, 2), "== 订单discount", float(order["discount_amount"]))

    # 6. 生成支付单
    s, d = call("POST", "/payments", {"order_id": order_id, "channel": "BALANCE"}, token)
    pay_no = d["data"]["payment_no"]
    print("create payment", s, pay_no, "amount", d["data"]["amount"])

    # 7. 付款（模拟）
    s, d = call("POST", f"/payments/{pay_no}/pay", {"channel": "BALANCE"})
    print("pay", s, d.get("data"))

    # 8. 幂等回调（重复 SUCCESS 不应再加积分/重复发货）
    before = call("GET", f"/members/me", token=token)  # 记录积分
    s, d = call("POST", "/payments/callback", {"payment_no": pay_no, "status": "SUCCESS"})
    after = call("GET", "/members/me", token=token)
    print("callback idempotent", s, "| points before/after:", before[1]["data"]["points"], after[1]["data"]["points"])

    # 9. 发货（上海仓 → 南京）
    s, d = call("POST", f"/shipments/{order_id}/ship", {"carrier": "顺丰速运"}, token)
    ship = d["data"]
    print("ship", s, "ship_status", ship["ship_status"], ship["ship_status_text"],
          "| route", ship["from_city"], "->", ship["to_city"])
    ship_id = ship["id"]

    # 10. 推进物流到签收（已发货→仓库拣货→已揽收→运输中→派送中→已签收，共 5 步）
    for i in range(5):
        s, d = call("POST", f"/shipments/{ship_id}/advance")
        print("   advance", i + 1, "->", d["data"]["ship_status"], d["data"]["ship_status_text"])
    ship = d["data"]
    print("   轨迹明细：")
    for t in ship["traces"]:
        print("     -", t["node"], "| 城市:", t["city"], "|", t["description"])

    # 11. 确认收货
    s, d = call("POST", f"/orders/{order_id}/confirm", token=token)
    print("confirm", s, "order_status", d["data"]["order_status"])

    # 12. 售后（按分摊比例退款）
    s, d = call("POST", "/aftersales", {
        "order_id": order_id, "type": "REFUND", "sku_id": sku1, "quantity": 1,
    }, token)
    as_id = d["data"]["id"]
    print("aftersale", s, "refund_amount", d["data"]["refund_amount"], "status", d["data"]["status"])

    # 13. 退款
    s, d = call("POST", f"/aftersales/{as_id}/refund", token=token)
    print("refund", s, "refund_amount", d["data"]["refund_amount"], "status", d["data"]["status"])

    # 14. RFM
    s, d = call("POST", "/members/rfm/refresh", token=token)
    print("rfm", s, d.get("data"))


if __name__ == "__main__":
    main()
