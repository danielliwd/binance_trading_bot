import telegram
from functools import cache

pool_size = 10


@cache
def get_bot(token, proxy_url=None):
    req_kws = {
        "connection_pool_size": pool_size,
        "proxy_url": proxy_url,
    }
    if not proxy_url:
        del req_kws["proxy_url"]
    req_cli = telegram.request.HTTPXRequest(**req_kws)
    return telegram.Bot(token, get_updates_request=req_cli, request=req_cli)