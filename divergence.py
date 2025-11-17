import pandas as pd
from binance.client import Client
import numpy as np
import ta


def detect_divergence(prices, rsi_values):
    """
    Detects bullish / bearish divergences by comparing the last two pivot highs/lows.
    Returns:
    - "bullish"
    - "bearish"
    - None
    """

    def local_lows(series):
        cond = (
            (series.shift(2) > series.shift(1)) &
            (series.shift(1) > series) &
            (series.shift(-1) > series) &
            (series.shift(-2) > series)
        )
        return series[cond].dropna()

    def local_highs(series):
        cond = (
            (series.shift(2) < series.shift(1)) &
            (series.shift(1) < series) &
            (series.shift(-1) < series) &
            (series.shift(-2) < series)
        )
        return series[cond].dropna()

    price_lows = local_lows(prices)
    rsi_lows = local_lows(rsi_values)
    price_highs = local_highs(prices)
    rsi_highs = local_highs(rsi_values)

    # Bullish: price makes lower low, RSI makes higher low
    if len(price_lows) >= 2 and len(rsi_lows) >= 2:
        price_pivots = price_lows.tail(2)
        rsi_pivots = rsi_lows.tail(2)
        if price_pivots.iloc[-1] < price_pivots.iloc[-2] and rsi_pivots.iloc[-1] > rsi_pivots.iloc[-2]:
            return "bullish"

    # Bearish: price makes higher high, RSI makes lower high
    if len(price_highs) >= 2 and len(rsi_highs) >= 2:
        price_pivots_high = price_highs.tail(2)
        rsi_pivots_high = rsi_highs.tail(2)
        if price_pivots_high.iloc[-1] > price_pivots_high.iloc[-2] and rsi_pivots_high.iloc[-1] < rsi_pivots_high.iloc[-2]:
            return "bearish"

    return None


def get_reversal_signal(coin: str):
    try:
        symbol = coin.upper() + "USDT"
        client = Client()

        # 4H Klines holen
        klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_4HOUR, limit=200)

        df = pd.DataFrame(klines, columns=[
            "time", "open", "high", "low", "close", "volume",
            "_", "_", "_", "_", "_", "_"
        ])

        df["close"] = df["close"].astype(float)

        # === INDICATORS ===
        df["rsi"] = ta.momentum.rsi(df["close"], window=14)

        macd = ta.trend.MACD(df["close"])
        df["macd"] = macd.macd()
        df["signal"] = macd.macd_signal()

        price = df["close"].iloc[-1]
        rsi = df["rsi"].iloc[-1]
        macd_val = df["macd"].iloc[-1]
        macd_signal = df["signal"].iloc[-1]

        # === DIVERGENZ CHECK ===
        divergence = detect_divergence(df["close"], df["rsi"])

        # === MACD TREND ===
        macd_turns_bullish = macd_val > macd_signal
        macd_turns_bearish = macd_val < macd_signal

        # === ERMITTLUNG DES SIGNALS ===

        signal = "HOLD"
        confidence = 10

        # Bullish Reversal
        if divergence == "bullish" and macd_turns_bullish:
            signal = "BUY"
            confidence = 85

        # Bearish Reversal
        elif divergence == "bearish" and macd_turns_bearish:
            signal = "SELL"
            confidence = 85

        # Leicht bullish
        elif macd_turns_bullish:
            signal = "HOLD (slightly bullish)"
            confidence = 40

        # Leicht bearish
        elif macd_turns_bearish:
            signal = "HOLD (slightly bearish)"
            confidence = 40

        # === AUSGABE FORMAT ===
        result = (
            f"📈 *Trend Reversal Signal for {coin.upper()}*\n\n"
            f"💰 Price: `{price:.2f} USDT`\n"
            f"📊 RSI: `{rsi:.2f}`\n"
            f"📉 MACD: `{macd_val:.4f}` | Signal: `{macd_signal:.4f}`\n"
            f"🔍 Divergence: `{divergence or 'None'}`\n"
            f"📉 MACD Trend: `{'Bullish' if macd_turns_bullish else 'Bearish'}`\n"
            f"🎯 Confidence: `{confidence}%`\n\n"
            f"➡️ *Recommendation: {signal}*"
        )

        return result, "Markdown"

    except Exception as e:
        return f"Error: {str(e)}", "Markdown"
