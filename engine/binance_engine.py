from tools.binance_ws_patcher import monkey_patch

# **!重要** binance需要代理, binance ws代理patch.
monkey_patch()

from engine.base_engine import BaseEngine, BaseOptions
from binance.client import BaseClient
from binance import BinanceSocketManager, AsyncClient
from binance.enums import FuturesType, HistoricalKlinesType
import logging
import time
import asyncio
import pydantic
from dataclasses import dataclass
import pandas as pd
import numpy as np
import pandas_ta as ta
import pydantic

API_KEY_PREFIX = "BINANCE_API_"
HIST_START_STR = "20 day ago UTC"

kline_interval_map = {
    BaseClient.KLINE_INTERVAL_1MINUTE: 60,
    BaseClient.KLINE_INTERVAL_1HOUR: 60 * 60,
}


class BinanceOptions(BaseOptions):
    api_key_prefix: str = API_KEY_PREFIX
    symbol: str = "ETHUSDT"
    tick_interval: str = BaseClient.KLINE_INTERVAL_1MINUTE
    hist_start_str: str = HIST_START_STR
    hist_interval: str = BaseClient.KLINE_INTERVAL_1HOUR


class Candle(pydantic.BaseModel):
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
    close: bool = pydantic.Field(alias="x")  # is this kline closed?


class BinanceKlineTick(pydantic.BaseModel):
    event: str = pydantic.Field(alias="e")
    symbol: str = pydantic.Field(alias="ps")
    contract_type: str = pydantic.Field(alias="ct")
    t: int = pydantic.Field(alias="E")
    k: Candle = pydantic.Field(alias="k")


class BinanceFutureEngine(BaseEngine):
    def __init__(
        self, strategy, api_key=None, api_secret=None, *, opts: BinanceOptions = None
    ):
        super().__init__(strategy, api_key, api_secret, opts=opts or BinanceOptions())
        self.opts: BinanceOptions

    def init_client(self):
        requests_params = {}
        if self.opts.proxy_url:
            requests_params["proxy"] = self.opts.proxy_url
        self.async_client = AsyncClient(
            api_key=self.api_key,
            api_secret=self.api_secret,
            requests_params=requests_params,
        )
        self.ws_client = BinanceSocketManager(self.async_client)
        if self.opts.proxy_url:
            self.ws_client.proxy_url = self.opts.proxy_url
        else:
            self.ws_client.proxy_url = None

    async def get_kline(self, limit=None, start_str=None):
        kws = {}
        if limit:
            kws["limit"] = limit
        else:
            kws["start_str"] = start_str or self.opts.hist_start_str

        klines = await self.async_client.get_historical_klines(
            symbol=self.opts.symbol,
            interval=self.opts.hist_interval,
            klines_type=HistoricalKlinesType.FUTURES,
            **kws
        )
        columns = [
            "t",
            "o",
            "h",
            "l",
            "c",
            "v",
            "e",
            "q",
            "n_of_trades",
            "ig1",  # "Taker buy base asset volume",
            "ig2",  # "Taker buy quote asset volume",
            "ig3",  # "Ignore",
        ]
        klines_df = pd.DataFrame(klines, columns=columns)
        del klines_df["ig1"]
        del klines_df["ig2"]
        del klines_df["ig3"]
        del klines_df["n_of_trades"]
        klines_df["time"] = pd.to_datetime(klines_df["t"].map(float), unit="ms")
        klines_df.set_index("time", inplace=True)
        klines_df["t"] = klines_df["t"].astype(int)
        for col in ["o", "h", "l", "c", "v", "q"]:
            klines_df[col] = klines_df[col].astype(float)
        return klines_df
    
    def is_last_hist_kline_closed(self):
        interval = kline_interval_map[self.opts.hist_interval]
        return self.is_last_kline_closed(self._hist, interval)

    async def init_hist(self):
        self._hist = await self.get_kline()

    async def update_hist(self):
        self.strategy.on_update_hist()
        last_t = self._hist.iloc[-2]["t"]
        klines = await self.get_kline(start_str=int(last_t))
        self._hist.update(klines)
        self._hist = self._hist.combine_first(klines)
        self._runtime["last_update_hist_t"] = time.time()

    def hist_need_auto_update(self):
        """
        是否需要更新历史数据
        """
        last_hist_t = self._hist.iloc[-1]["t"] / 1000
        now = time.time()
        expires_t = kline_interval_map[self.opts.hist_interval]

        return now - last_hist_t > expires_t

    async def subscribe(self):
        tick_socket = self.ws_client.kline_futures_socket(
            self.opts.symbol,
            interval=self.opts.tick_interval,
            futures_type=FuturesType.USD_M,
        )
        while not tick_socket.ws:
            logging.info("Websocket Connection...")
            time.sleep(1)
            await tick_socket.connect()

        async for msg in tick_socket.ws:
            yield msg

    def parse_conents(self, contents):
        """
        return <dispatch_type>, <parsed_contents>
        """
        ws_type_, msg_data, _ = contents
        try:
            msg = BinanceKlineTick.model_validate_json(msg_data)
        except pydantic.ValidationError as e:
            logging.exception(e)
            return
        return msg.event, msg

    def get_dispatcher(self):
        """
        using msg.type as dispatch_type
        """
        return {
            "continuous_kline": self.strategy.on_tick,
        }

    async def _open_order(self, order):
        pass

    async def close_all_position(self):
        pos = await self.async_client.futures_position_information(symbol=self.opts.symbol)
        print(pos)
        # TODO:
        # await self.cancel_all_order()

    async def cancel_all_order(self):
        await self.async_client.futures_cancel_all_open_orders(symbol=self.opts.symbol)


# %%

if __name__ == "__main__":
    from engine.base_strategy import SimpleStrategy

    class MyStrategy(SimpleStrategy):
        async def on_tick(self, tick):
            print("---- tick -----", tick)
            await asyncio.sleep(2)

        def pre_update_hist(self):
            print("pre update hist")

    def test1():
        strategy = MyStrategy()
        strategy.auto_update_hist = True
        engine = BinanceFutureEngine(
            MyStrategy(), opts=BinanceOptions(proxy_url="http://127.0.0.1:7890")
        )
        asyncio.run(engine.run())

    test1()
# %%
