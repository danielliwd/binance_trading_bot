import pydantic


PROCESS_TIMEOUT_MS = 10 * 1000  # on_tick 超时时间， 超时处理将会在 on_proccess_timeout 中处理
API_KEY_PREFIX = "API_"

class BaseOptions(pydantic.BaseModel):
    symbol: str = "ETHUSDT"
    proxy_url: str = None
    process_timeout_ms: int = PROCESS_TIMEOUT_MS
    api_key_prefix: str = API_KEY_PREFIX
    test: bool = False

class SymbolInfo(pydantic.BaseModel):
    symbol: str
    quantity_precision: int


class Candle(pydantic.BaseModel):
    t: int  # kline time start
    e: int  # kline time end
    interval: str 
    o: float   # open
    h: float   # high
    l: float   # low
    c: float   # close
    v: float   # volume
    q: float   # quote volume
    closed: bool  # is this kline closed?

class KlineTick(pydantic.BaseModel):
    k: Candle # kline data

class position(pydantic.BaseModel):
    symbol: str
    amount: float  # 持仓数量
    side: str  # long short
    notional: float
    isolatedWallet: float
    updateTime: int