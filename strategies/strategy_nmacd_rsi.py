import os
import asyncio
import threading
import concurrent.futures


import pandas as pd
import time
from datetime import datetime, timezone, timedelta
from tools.precisions import qunatity_at_least

import pandas_ta
from engine.base_strategy import BaseStrategy
from engine.base_structs import BaseOptions, SymbolInfo, KlineTick
from engine.binance_engine import BinanceFutureEngine, BinanceOptions
from ta.indictor_nmacd import nmacd_signals
from ta.indictor_rsi_cross import rsi_cross_signals
from ta.algo import enhanced_signals
from tools.telegram_bot import get_bot
from tools.readkeys import SecretKeys

class NmacdRsiStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.test_trigger_once = False
        self.enhanced = None
        self.bot = None
        self._last_signal_ms = None
        self._last_signal_idx = None
        self.trigger_orders = {}
        self._last_check_position_ts = 0
        self._check_position_interval = 60
        self.position = None, None  # side, amount
        self.init()

    def init(self):
        self._thread_pool = concurrent.futures.ThreadPoolExecutor()
        self._pool = self._thread_pool.submit
    
    async def update_position_info(self):
        now = time.time()
        if now - self._last_check_position_ts < self._check_position_interval:
            return self.position
        self._last_check_position_ts = time.time()
        self.position = await self.engine.get_position()
    
    async def check_signal(self):
        # 检查信号: 1. 上个kline是否有信号 2 该信号是否开过单 3 当前postion是否与开单方向一致
        signal_idx = self.get_signal_idx()
        if signal_idx and signal_idx in [self.hist.iloc[-2].name , self.hist.iloc[-1].name]:
            if signal_idx not in self.trigger_orders:
                # 该信号未开过单
                await self.update_position_info()
                # 方向不一致
                signal_side = "LONG" if self.enhanced.loc[signal_idx]["enhanced"] > 0  else "SHORT"
                if not self.position[0] or self.position[0] != signal_side:
                    self.trigger_orders[signal_idx] = True
                    return True
        return False

    async def on_tick(self, tick: KlineTick):
        print("---- tick -----", tick)
        print("---- hist -----", self.hist.tail(2).to_json())

        open_order_condition = await self.check_signal()


        if self.opts.test and not self.test_trigger_once:
            # 仅在test时触发一次
            # open_order_condition = True
            self.test_trigger_once = True
            open_order_condition = False
        elif self.opts.test:
            open_order_condition = False

        if open_order_condition:
            quantity = qunatity_at_least(10, tick.k.c, self.symbol_info.quantity_precision)
            await self.engine.open_order({"side": "SELL", "quantity": str(quantity)})

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


    def create_order(self, signal_kline_index):
        pass

    def order_hint(self, signal_kline_index):


        signal = self.enhanced.loc[signal_kline_index]["enhanced"]
        if signal == 0:
            return

        dtkline = (
            pd.to_datetime(signal_kline_index)
            .tz_localize("UTC")
            .tz_convert("Asia/Shanghai")
        )
        dt = datetime.now().astimezone(timezone(timedelta(hours=8)))
        if dt - dtkline > timedelta(minutes=30):
            hist_signal_str = "【非即时】"
        dtkline_str = dtkline.strftime("%Y-%m-%d %H:%M:%SZ+8")
        price = self.hist.loc[signal_kline_index]["c"]
        stop_loss = 10
        if signal > 0:
            buy_sell = "买入"
            side = "【多】"
            stop_loss_price = self.enhanced.loc[signal_kline_index]["ma2min"]
            order_size = stop_loss / (price - stop_loss_price) * price
            take_profit_price_1 = price + price - stop_loss_price
            take_profit_price_2 = price + (price - stop_loss_price) * 2
        else:
            buy_sell = "卖出"
            side = "【空】"
            stop_loss_price = self.enhanced.loc[signal_kline_index]["ma2max"]
            order_size = stop_loss / (stop_loss_price - price) * price
            take_profit_price_1 = price - (stop_loss_price - price)
            take_profit_price_2 = price - (stop_loss_price - price) * 2

        order_hint_str = f"{hist_signal_str}{side}{self.symbol} K线时间{dtkline_str} 以价格{price:.2f} {buy_sell} {order_size:.2f}USDT. 止损价 {stop_loss_price:.2f}. 1:1止盈价 {take_profit_price_1:.2f}  1:2止盈价 {take_profit_price_2:.2f}. "

        return  order_hint_str

    def _test_create_order(self, *args, **kwargs):
        return self.create_order(*args, **kwargs)

    def post_update_hist(self):
        self.update_indicators()
        signal_idx, is_new = self.get_signal_idx()
        if signal_idx:
            self.notice_signal(signal_idx)

    def get_signal_idx(self):
        """
        hist signal 的 index 是 datetime
        """
        signal_idx = None
        is_new = True
        is_old = False

        if not self._last_signal_idx:
            # 从未发过信号
            if self.is_last_hist_kline_closed():
                signal_df = self.enhanced
            else:
                signal_df = self.enhanced.iloc[:1]

            signal_df = self.enhanced[self.enhanced.enhanced != 0]

            if not signal_df.empty:
                self._last_signal_idx = signal_df.iloc[-1].name
                return signal_df.iloc[-1].name, is_old
        else:
            if self.is_last_hist_kline_closed():
                signal_series = self.enhanced.iloc[-1]
            else:
                signal_series = self.enhanced.iloc[-2]
            if (
                signal_series.enhanced != 0
                and self._last_signal_idx != signal_series.name
            ):
                self._last_signal_idx = signal_series.name
                return signal_series.name, is_new
        return signal_idx, is_old

    def notice_signal(self, signal_idx):

        # create bot
        tg_token = SecretKeys.get("TELEGRAM_BOT_TOKEN")
        chat_id = SecretKeys.get("TG_CHAT_ID_ORDER")
        if not self.bot:
            self.bot = get_bot(tg_token, self.engine.opts.proxy_url)

        test_str = "" if not self.engine.opts.test else "[测试]:"
        order_hint_str = self.order_hint(signal_idx)
        if self.engine.opts.test:
            print(order_hint_str)
            self.hist.to_csv("tmp_hist_%s.csv" % self.symbol)
            self.enhanced.to_csv("tmp_signals_%s.csv" % self.symbol)
        else:
            print(order_hint_str)
            dt = datetime.now().astimezone(timezone(timedelta(hours=8)))
            dtstr = dt.strftime("%Y-%m-%d %H:%M:%SZ+8")
            asyncio.get_event_loop().create_task(
                self.bot.send_message(
                    chat_id=chat_id,
                    text="%s%s -- NMACD_RSI策略 %s" % (test_str, order_hint_str, dtstr),
                )
            )

    def pre_open_order(self, order):
        print("---open order ----")


def main(symbol, test=True):
    process_timeout_ms = int(os.getenv("PROCESS_TIMEOUT_MS", 10 * 1000))
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
            process_timeout_ms=process_timeout_ms,
            test=test,
        ),
    )
    asyncio.run(engine.run())


if __name__ == "__main__":
    import sys

    symbol = sys.argv[1] if len(sys.argv) > 1 else "AUCTIONUSDT"
    test = False if len(sys.argv) > 2 and sys.argv[2] == "product" else True
    main(symbol, test)
