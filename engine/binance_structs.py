# %%
import pydantic
from engine.base_structs import Candle, KlineTick

class BinanceCandle(Candle):
    t: int = pydantic.Field(alias="t")  # kline time start
    e: int = pydantic.Field(alias="T")  # kline time end
    interval: str = pydantic.Field(alias="i")
    ## skip fields
    # first_trade_id: int = pydantic.Field(alias="f")
    # last_trade_id: int = pydantic.Field(alias="L")
    # n: int = pydantic.Field(alias="n")  # number of trades
    o: float = pydantic.Field(alias="o")  # open
    h: float = pydantic.Field(alias="h")  # high
    l: float = pydantic.Field(alias="l")  # low
    c: float = pydantic.Field(alias="c")  # close
    v: float = pydantic.Field(alias="v")  # volume
    q: float = pydantic.Field(alias="q")  # quote volume
    closed: bool = pydantic.Field(alias="x")  # is this kline closed?


class BinanceKlineTick(KlineTick):
    event: str = pydantic.Field(alias="e")
    symbol: str = pydantic.Field(alias="ps")
    contract_type: str = pydantic.Field(alias="ct")
    t: int = pydantic.Field(alias="E")
    k: BinanceCandle = pydantic.Field(alias="k")


if __name__ == "__main__":
    msg_data = '{"e":"continuous_kline","E":1706144867564,"ps":"ILVUSDT","ct":"PERPETUAL","k":{"t":1706144820000,"T":1706144879999,"i":"1m","f":3883429994698,"L":3883432678663,"o":"73.43000","c":"73.48000","h":"73.51000","l":"73.42000","v":"61.9","n":75,"x":false,"q":"4548.372000","V":"59.7","Q":"4386.822000","B":"0"}}'
    msg = BinanceKlineTick.model_validate_json(msg_data)
    print(msg)
# %%