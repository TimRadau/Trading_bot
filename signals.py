import pandas as pd
from binance.client import Client
import ta
import numpy as np

def get_signal(coin: str, mode: str):
    try:
        symbol = coin.upper() + "USDT"
        client = Client()  # Public API ohne Key

        # Hole letzte 200 Stundenkerzen
        klines = client.get_klines(symbol=symbol, interval="1h", limit=200)
        df = pd.DataFrame(klines, columns=[
            'timestamp','open','high','low','close','volume','close_time','qav',
            'num_trades','taker_base_vol','taker_quote_vol','ignore'
        ])
        df["close"] = df["close"].astype(float)

        # --- Indikatoren ---
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
        macd = ta.trend.MACD(df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["sma20"] = ta.trend.SMAIndicator(df["close"], window=20).sma_indicator()
        df["sma50"] = ta.trend.SMAIndicator(df["close"], window=50).sma_indicator()

        latest = df.iloc[-1]
        rsi = latest["rsi"]
        macd_val = latest["macd"]
        macd_signal = latest["macd_signal"]
        price = latest["close"]
        sma20 = latest["sma20"]
        sma50 = latest["sma50"]

        # --- Trend-Analyse ---
        recent_prices = df["close"].tail(10).values
        x = np.arange(len(recent_prices))
        slope = np.polyfit(x, recent_prices, 1)[0]

        if slope > 0 and sma20 > sma50:
            trend = "📈 Aufwärtstrend"
        elif slope < 0 and sma20 < sma50:
            trend = "📉 Abwärtstrend"
        else:
            trend = "➡️ Seitwärts"

        # --- Punktesystem ---
        score = 0
        total_factors = 3

        # RSI
        if rsi < 45:
            score += 1
        elif rsi > 55:
            score -= 1

        # MACD
        if macd_val > macd_signal:
            score += 1
        elif macd_val < macd_signal:
            score -= 1

        # SMA20
        if price > sma20:
            score += 1
        elif price < sma20:
            score -= 1

        # --- Dynamische Confidence ---
        rsi_strength = abs(rsi - 50) / 50  # wie weit entfernt vom neutralen Bereich
        macd_strength = abs(macd_val - macd_signal)
        price_gap = abs(price - sma20) / price

        confidence_raw = (
            0.4 * rsi_strength +
            0.4 * (macd_strength / max(1e-6, abs(macd_signal))) +
            0.2 * price_gap
        )
        confidence = int(min(confidence_raw * 100, 100))

        # --- Signalentscheidung ---
        if mode == "safe":
            if score >= 3:
                signal = "BUY"
            elif score <= -3:
                signal = "SELL"
            else:
                signal = "HOLD"
        elif mode == "balanced":
            if score >= 2:
                signal = "BUY"
            elif score <= -2:
                signal = "SELL"
            else:
                signal = "HOLD"
        else:  # aggressive
            if score > 0:
                signal = "BUY"
            elif score < 0:
                signal = "SELL"
            else:
                signal = "HOLD"

        # --- Formatierte Ausgabe ---
        result = (
            f"📈 *Signal für {coin.upper()}*\n\n"
            f"💰 Preis: `{price:.2f} USDT`\n"
            f"📊 RSI: `{rsi:.2f}`\n"
            f"📉 MACD: `{macd_val:.4f}` | Signal: `{macd_signal:.4f}`\n"
            f"📏 SMA20: `{sma20:.2f}` | SMA50: `{sma50:.2f}`\n"
            f"📊 Trend: {trend}\n"
            f"🎯 Confidence: `{confidence}%`\n\n"
            f"➡️ *Empfehlung:* {signal}"
        )

        return result, "Markdown"

    except Exception as e:
        return f"⚠️ Fehler beim Abrufen der Daten für {coin.upper()}: {e}", "Markdown"
