# %%
from decimal import Decimal, ROUND_DOWN, ROUND_UP

def round_down(value, precisions):
    assert isinstance(precisions, int)
    factor = Decimal("0.1") ** int(precisions)
    if isinstance(value, float):
        value = str(value)
    return Decimal(value).quantize(factor, rounding=ROUND_DOWN) 

def round_up(value, precisions):
    assert isinstance(precisions, int)
    factor = Decimal("0.1") ** int(precisions)
    if isinstance(value, float):
        value = str(value)
    return Decimal(value).quantize(factor, rounding=ROUND_UP) 

def qunatity_at_least(value, price, precisions):
    """
    价格为 price 时，买价值不少于 value 的quantity数量
    比如 blur price为 1.1， 需要买不少于 10U， 数量精度为2:
        round_down(1.1 / 10 , 2) = 9.09
        9.09 * 1.1 = 9.999 不足10， 所以需要最小精度+1
        9.09 + 0.01 = 9.1
    """

    if isinstance(value, float):
        value = str(value)
    value = Decimal(value)
    if isinstance(price, float):
        price = str(price)
    price = Decimal(price)

    return round_up(value / price, precisions)

if __name__ == "__main__":
    print(round_down(1.234567, 3))
    assert(qunatity_at_least(10, 1.1, 2) == Decimal("9.10"))
# %%