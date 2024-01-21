import asyncio
import sys
import pandas as pd
import time

from engine.base_strategy import BaseStrategy
from engine.binance_engine import BinanceFutureEngine, BinanceOptions
from ta.indictor_nmacd import nmacd_signals
from ta.indictor_rsi_cross import rsi_cross_signals
from ta.algo import enhanced_signals
from tools.telegram_bot import get_bot
from tools.readkeys import SecretKeys


class NmacdRsiStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.enhanced = None
        self.bot = None

    async def on_tick(self, tick):
        print("---- tick -----", tick)

        open_order_condition = False  # do your check
        if open_order_condition:
            await self.engine.open_order(None)

        await asyncio.sleep(2)

    def update_indicators(self):
        nmacd_cross = nmacd_signals(self.hist["c"], fast=13, slow=21, signal=9, normalize=50)
        rsi_cross = rsi_cross_signals(self.hist["c"], rsi_length=21, sma_length=55)
        enhanced = enhanced_signals(nmacd_cross["signal"], rsi_cross["signal"], windows=8)
        df = pd.merge(nmacd_cross, rsi_cross, left_index=True, right_index=True)
        df["enhanced"] = enhanced
        self.enhanced = df

        open_order_condition = True  # do your check
        if open_order_condition:
            task = asyncio.get_event_loop().create_task(self.engine.open_order(None))

    def post_update_hist(self):
        self.update_indicators()
    
    def pre_open_order(self, order):
        tg_token = SecretKeys.get("TELEGRAM_BOT_TOKEN")
        chat_id = SecretKeys.get("TG_CHAT_ID_ORDER")
        if not self.bot:
            self.bot = get_bot(tg_token, self.engine.opts.proxy_url)
        last_signal = self.enhanced[self.enhanced.enhanced != 0]
        if not last_signal.empty:
            s = last_signal.iloc[-1]
            buy_sell = "买" if s.enhanced > 0 else "卖"
            last_signal_str = f"{s.name} {self.symbol} {buy_sell}"
            asyncio.get_event_loop().create_task(self.bot.send_message(chat_id=chat_id, text="NMACD_RSI策略: %s" % last_signal_str))



def main():
    symbol = sys.argv[1]
    strategy = NmacdRsiStrategy()
    strategy.auto_update_hist = True
    engine = BinanceFutureEngine(
        NmacdRsiStrategy(),
        opts=BinanceOptions(
            # symbol="ETHUSDT",
            symbol=symbol,
            proxy_url="http://127.0.0.1:7890",
            hist_interval="1h", 
            hist_start_str="20 day ago UTC",
        ),
    )
    asyncio.run(engine.run())


if __name__ == "__main__":
    main()
