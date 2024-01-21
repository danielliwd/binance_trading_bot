from engine.base_strategy import BaseStrategy
from tools.readkeys import SecretKeys
import pandas as pd
import asyncio
from datetime import datetime
from tools.make_async import make_async
import pydantic
import logging

ALL=["BaseEngine"]

logger = logging.getLogger(__name__)


class Fake:
    @staticmethod
    def hist():
        return pd.DataFrame(
            {
                "time": [datetime(2021, 1, i+1, 0, 0, 0) for i in range(20)],
                "open": [i for i in range(20)], 
                "high": [i for i in range(20)],
                "low": [i for i in range(20)],
                "close": [i for i in range(20)],
                "volume": [i for i in range(20)],
            }
        )
    
    @staticmethod
    def ticks():
        for i in range(20):
            yield {
                "time": datetime(2021, 1, i+1, 0, 0, 0),
                "open": i,
                "high": i,
                "low": i,
                "close": i,
                "volume": i,
            }


PROCESS_TIMEOUT_MS = 10 * 1000  # on_tick 超时时间， 超时处理将会在 on_proccess_timeout 中处理
API_KEY_PREFIX = "API_"

class BaseOptions(pydantic.BaseModel):
    symbol: str = "ETHUSDT"
    proxy_url: str = None
    process_timeout_ms: int =PROCESS_TIMEOUT_MS
    api_key_prefix: str = API_KEY_PREFIX

class BaseEngine:
    """
    Engine for loading strategy
    - init client
    - load data
    - run strategy
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        api_key=None,
        api_secret=None,
        *,
        opts: BaseOptions = None,
    ):
        self.async_client = None
        self.ws_client = None
        self.strategy = strategy
        self.strategy.engine = self
        self.opts = opts or BaseOptions()
        self.api_key = api_key or SecretKeys.get(self.opts.api_key_prefix+ "_KEY")
        self.api_secret = api_secret or SecretKeys.get(self.opts.api_key_prefix+ "_SECRET")

        # running context
        self._hist = None
        self._last_fut = None
        self._update_hist_fut = None
        self._runtime = {}

    def init_client(self):
        self.async_client = None
        self.ws_client = None

    def init_hist(self):
        """
        init history klines
        """
        self._hist = Fake.hist()
    
    async def _open_order(self, order):
        pass

    async def open_order(self, order):
        """
        open order
        """
        self.strategy.pre_open_order(order)
        await self._open_order(order)
        self.strategy.post_open_order(order)

    def close_order(self, order_id):
        pass

    def close_all_order(self, order_id):
        pass

    async def update_hist(self):
        """
        call when needed
        """
        pass
    
    async def subscribe(self):
        for tick in Fake.ticks():
            yield tick
    
    def parse_conents(self, contents):
        """
        return <dispatch_type>, <parsed_contents>
        """
        return "tick", contents

    def _get_dispatcher(self):
        d = self.get_dispatcher()
        return {k:make_async(v) for k, v in d.items()}

    def get_dispatcher(self):
        """
        implete me
        """
        return {
            "dispatch_type_1": None,
            "tick": self.strategy.on_tick,
        }

    async def _trading_strategy(self, dispatcher, contents):
        """
        基类隐式实现，不要重写
        """
        disptcher_type, msg = self.parse_conents(contents)
        if disptcher_type not in dispatcher:
            raise ValueError(f"unknown dispatcher type: {disptcher_type}")

        try:
            fut = dispatcher[disptcher_type](msg)
            await asyncio.wait_for(fut, timeout=self.opts.process_timeout_ms / 1000)
        except asyncio.TimeoutError as e:
            self.strategy.on_process_timeout(disptcher_type, e)
        
    async def _process_message(self, dispatcher, contents):
        """
        基类隐式实现，不要重写
        """
        if not self._last_fut or self._last_fut.done():
            self._last_fut = asyncio.create_task(self._trading_strategy(dispatcher, contents))
        else:
            self.strategy.on_tick_latency(contents)
    
    def hist_need_auto_update(self):
        return False

    async def _update_hist_loop(self):
        while True:
            try:
                need_update = False
                if self.strategy.auto_update_hist:
                    need_update = self.hist_need_auto_update()
                else:
                    need_update = self.strategy.hist_need_update()
                
                if need_update:
                    self.strategy.pre_update_hist()
                    self._update_hist_fut = asyncio.create_task(self.update_hist())
                    self._update_hist_fut.add_done_callback(lambda ctx: self.strategy.post_update_hist())
            except Exception as e:
                logger.exception(e)

            if not need_update:
                await asyncio.sleep(1)
            else:
                await self._update_hist_fut
                await asyncio.sleep(10)

    async def _message_loop(self):
        dispatcher = self._get_dispatcher()
        async for content in self.subscribe():
            if self._update_hist_fut and not self._update_hist_fut.done():
                await asyncio.ensure_future(self._update_hist_fut)
            await self._process_message(dispatcher, content)
    
    async def run(self):
        self.strategy.pre_init()
        await make_async(self.init_client)()
        await make_async(self.init_hist)()
        self.strategy.post_init()
        asyncio.create_task(self._update_hist_loop())
        await self._message_loop()


# %%
if __name__ == "__main__":
    from engine.base_strategy import SimpleStrategy
    def test1():
        class MyStrategy(SimpleStrategy):
            async def on_tick(self, tick):
                print(tick)
                if tick["close"] % 7 == 0:
                    self.update_hist()
                    print(self.hist[-4:])
                await asyncio.sleep(0.5)

        engine = BaseEngine(MyStrategy())
        asyncio.run(engine.run())
    test1()

# %%