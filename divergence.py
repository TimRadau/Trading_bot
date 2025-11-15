import pandas as pd
from binance.client import Client
import numpy as np
import ta


def detect_divergence(prices, rsi_values):
    """
    Erkennt Bullish / Bearish Divergenzen anhand der letzten 5 Pivot Points.
    Gibt zurück:
    - "bullish"
    - "bearish"
    - None
    """

    # Pivot-Lows / Pivot-Highs erkennen
    window = 5
    price_low_idx = prices.rolling(window, center=True).apply(lambda x: x[window // 2] == x.min(), raw=True)
    price_high_idx = prices.rolling(window, center=True).apply(lambda x: x[window // 2] == x.max(), raw=True)

    rsi_low_idx = rsi_values.rolling(window, center=True).apply(lambda x: x[window // 2] == x.min(), raw=True)
    rsi_high_idx = rsi_values.rolling(window, center=True).apply(lambda x: x[window // 2] == x.max(), raw=True)

    # Bullish Divergenz:
    # Preis macht tieferes Tief, RSI macht höheres Tief
    try:
        price_pivots = prices[price_low_idx == 1].tail(2)
        rsi_pivots = rsi_values[rsi_low_idx == 1].tail(2)

        if len(price_pivots) == 2 and len(rsi_pivots) == 2:
            if price_pivots.iloc[-1] < price_pivots.iloc[-2] and rsi_pivots.iloc[-1] > rsi_pivots.iloc[-2]:
                return "bullish"
    except:
        pass

    # Bearish Divergenz:
    # Preis macht höheres Hoch, RSI macht tieferes Hoch
    try:
        price_pivots_high = prices[price_high_idx == 1].tail(2)
        rsi_pivots_high = rsi_values[rsi_high_idx == 1].tail(2)

        if len(price_pivots_high) == 2 and len(rsi_pivots_high) == 2:
            if price_pivots_high.iloc[-1] > price_pivots_high.iloc[-2] and rsi_pivots_high.iloc[-1] < rsi_pivots_high.iloc[-2]:
                return "bearish"
    except:
        pass

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
            signal = "HOLD (leicht bullish)"
            confidence = 40

        # Leicht bearish
        elif macd_turns_bearish:
            signal = "HOLD (leicht bearish)"
            confidence = 40

        # === AUSGABE FORMAT ===
        result = (
            f"📈 *Trend-Reversal Signal für {coin.upper()}*\n\n"
            f"💰 Preis: `{price:.2f} USDT`\n"
            f"📊 RSI: `{rsi:.2f}`\n"
            f"📉 MACD: `{macd_val:.4f}` | Signal: `{macd_signal:.4f}`\n"
            f"🔍 Divergenz: `{divergence or 'Keine'}`\n"
            f"📉 MACD Trend: `{'Bullish' if macd_turns_bullish else 'Bearish'}`\n"
            f"🎯 Confidence: `{confidence}%`\n\n"
            f"➡️ *Empfehlung: {signal}*"
        )

        return result, "Markdown"

    except Exception as e:
        return f"Fehler: {str(e)}", "Markdown"

