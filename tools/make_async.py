import asyncio

def make_async(fun):
    if asyncio.iscoroutinefunction(fun):
        return fun
    else:
        async def async_fun(*args, **kwargs):
            return fun(*args, **kwargs)
        return async_fun