import asyncio
import pandas as pd
import time

import pandas_ta
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
        self._last_signal_time = None

    async def on_tick(self, tick):
        print("---- tick -----", tick)

        open_order_condition = False  # do your check
        if open_order_condition:
            await self.engine.open_order(None)

        await asyncio.sleep(2)

    def update_indicators(self):
        nmacd_cross = nmacd_signals(
            self.hist["c"], fast=13, slow=21, signal=9, normalize=50
        )
        rsi_cross = rsi_cross_signals(self.hist["c"], rsi_length=21, sma_length=55)
        enhanced = enhanced_signals(
            nmacd_cross["signal"], rsi_cross["signal"], windows=8
        )
        df = pd.merge(nmacd_cross, rsi_cross, left_index=True, right_index=True)
        df["enhanced"] = enhanced
        self.enhanced = df
        self.enhanced["ma2min"] = pandas_ta.sma(self.hist["l"], 2).rolling(10).min()
        self.enhanced["ma2max"] = pandas_ta.sma(self.hist["h"], 2).rolling(10).max()

    def trigger_signal_open_order(self):
        open_order_condition = False  # do your check
        if open_order_condition:
            task = asyncio.get_event_loop().create_task(self.engine.open_order(None))

    def create_order(self, signal_kline_index):
        signal = self.enhanced.loc[signal_kline_index]["enhanced"]
        if signal == 0:
            return

        dt = (
            pd.to_datetime(signal_kline_index)
            .tz_localize("UTC")
            .tz_convert("Asia/Shanghai")
        )
        price = self.hist.loc[signal_kline_index]["c"]
        stop_loss = 10
        if signal > 0:
            buy_sell = "买"
            stop_loss_price = self.enhanced.loc[signal_kline_index]["ma2min"]
            order_size = stop_loss / (price - stop_loss_price) * price
            take_profit_price_1 = price + price - stop_loss_price
            take_profit_price_2 = price + (price - stop_loss_price) * 2
        else:
            buy_sell = "卖"
            stop_loss_price = self.enhanced.loc[signal_kline_index]["ma2max"]
            order_size = stop_loss / (stop_loss_price - price) * price
            take_profit_price_1 = price - (stop_loss_price - price)
            take_profit_price_2 = price - (stop_loss_price - price) * 2

        order_str = f"{dt.strftime('%Y-%m-%d %H:%M:%SZ+8')} {self.symbol} 以价格{price:.2f} {buy_sell} {order_size:.2f}USDT 止损价 {stop_loss_price:.2f} 1:1止盈价 {take_profit_price_1:.2f}  1:2止盈价 {take_profit_price_2:.2f}"

        class Order:
            pass

        order = Order()
        order.hint_str = order_str
        return order

    def _test_create_order(self, *args, **kwargs):
        return self.create_order(*args, **kwargs)

    def post_update_hist(self):
        self.update_indicators()
        self.notice_signal()
        self.trigger_signal_open_order()

    def notice_signal(self):
        tg_token = SecretKeys.get("TELEGRAM_BOT_TOKEN")
        chat_id = SecretKeys.get("TG_CHAT_ID_ORDER")
        test_str = "" if not self.engine.opts.test else "[测试]"
        order = None
        if not self.bot:
            self.bot = get_bot(tg_token, self.engine.opts.proxy_url)
        if not self._last_signal_time:
            last_signal = self.enhanced[self.enhanced.enhanced != 0]
            if not last_signal.empty:
                s = last_signal.iloc[-1]
                order = self._test_create_order(s.name)
        else:
            s = self.enhanced.iloc[-1]
            if s.enhanced != 0 and self.hist[-1]["t"] > self._last_signal_time * 1000:
                order = self._test_create_order(s.name)
        if order:
            if self.engine.opts.test:
                print(order.hint_str)
                self.hist.to_csv("tmp_hist_%s.csv" % self.symbol)
                self.enhanced.to_csv("tmp_signals_%s.csv" % self.symbol)
            else:
                asyncio.get_event_loop().create_task(
                    self.bot.send_message(
                        chat_id=chat_id,
                        text="NMACD_RSI策略%s: %s" % (test_str, order.hint_str),
                    )
                )

    def pre_open_order(self, order):
        print("---open order ----")


def main(symbol, test=True):
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
            test=test,
        ),
    )
    asyncio.run(engine.run())


if __name__ == "__main__":
    import sys

    symbol = sys.argv[1] if len(sys.argv) > 1 else "LINKUSDT"
    test = False if len(sys.argv[1:]) > 2 and sys.argv[2] == "product" else True
    main(symbol, test)
