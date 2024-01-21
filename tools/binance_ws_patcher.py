import logging
import aiohttp
from binance.streams import ThreadedApiManager, ReconnectingWebsocket, WSListenerState, BinanceSocketManager


async def start_listener(self, socket, path: str, callback):
    async with socket as s:
        while self._socket_running[path]:
            async for msg in s.ws:
                try:
                    callback(*msg)
                except Exception as e:
                    logging.exception(e)
    del self._socket_running[path]


async def connect(self):
    await self._before_connect()
    assert self._path
    ws_url = self._url + self._prefix + self._path
    logging.info("connecting %s", ws_url)
    # self._conn = ws.connect(ws_url, close_timeout=0.1)  # type: ignore
    kws = {}
    if self.proxy_url:
        kws["proxy"] = self.proxy_url

    self._conn = aiohttp.ClientSession().ws_connect(url=ws_url, **kws)  # type: ignore
    try:
        self.ws = await self._conn.__aenter__()
        self.ws.fail_connection = lambda: True
    except Exception as e:  # noqa
        print(e)
        print(self._conn)
        await self._reconnect()
        return
    self.ws_state = WSListenerState.STREAMING
    self._reconnects = 0
    await self._after_connect()

old_get_socket = BinanceSocketManager._get_socket

def BinanceSocketManager_get_socket(self, *args, **kwargs):
    sock = old_get_socket(self, *args, **kwargs)
    sock.proxy_url = self.proxy_url
    return sock

def monkey_patch():
    ThreadedApiManager.start_listener = start_listener
    ReconnectingWebsocket.connect = connect
    BinanceSocketManager._get_socket = BinanceSocketManager_get_socket
