"""金额处理：统一用 Decimal，杜绝 float 误差。"""
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def money(x) -> Decimal:
    """转成保留两位小数的 Decimal。"""
    return Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP)


def distribute_discount(total_discount: Decimal, items: list) -> list:
    """把订单级优惠额按行金额比例分摊到各行，尾差补到金额最大行。

    items: [{"amount": Decimal, ...}]，返回与 items 等长的分摊列表。
    """
    total = sum((it["amount"] for it in items), Decimal("0"))
    if total <= 0 or total_discount <= 0:
        return [Decimal("0") for _ in items]
    shares = []
    allocated = Decimal("0")
    max_idx, max_amt = 0, Decimal("-1")
    for i, it in enumerate(items):
        if it["amount"] > max_amt:
            max_amt, max_idx = it["amount"], i
        raw = total_discount * it["amount"] / total
        sh = raw.quantize(CENT, rounding=ROUND_HALF_UP)
        shares.append(sh)
        allocated += sh
    # 尾差补到最大行
    diff = total_discount - allocated
    if diff != 0 and items:
        shares[max_idx] = (shares[max_idx] + diff).quantize(CENT, rounding=ROUND_HALF_UP)
    return shares
