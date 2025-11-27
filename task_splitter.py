import asyncio

from scanner import coin_scanner_top3
from signals import get_signal
from divergence import get_reversal_signal
from resistance import get_support_resistance


async def run_blocking(func, *args, **kwargs):
    """
    Execute a synchronous function in a background thread so the
    asyncio event loop stays responsive.
    """
    return await asyncio.to_thread(func, *args, **kwargs)


async def async_scan_top3():
    return await run_blocking(coin_scanner_top3)


async def async_signal(coin: str, mode: str):
    return await run_blocking(get_signal, coin, mode)


async def async_reversal(coin: str):
    return await run_blocking(get_reversal_signal, coin)


async def async_support_resistance(coin: str):
    return await run_blocking(get_support_resistance, coin)
