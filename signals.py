import pandas as pd
from binance.client import Client
import ta

def get_signal(coin: str, mode: str):
    """
    coin: z.B. 'BTC'
    mode: 'safe', 'balanced', 'aggressive'
    """
    try:
        symbol = coin.upper() + "USDT"
        client = Client()  # Public API ohne Key

        # Hole die letzten 100 Stundenkerzen
        klines = client.get_klines(symbol=symbol, interval="1h", limit=100)
        df = pd.DataFrame(klines, columns=[
            'timestamp','open','high','low','close','volume','close_time','qav',
            'num_trades','taker_base_vol','taker_quote_vol','ignore'
        ])
        df["close"] = df["close"].astype(float)

        # --- Technische Indikatoren ---
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
        macd = ta.trend.MACD(df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["sma20"] = ta.trend.SMAIndicator(df["close"], window=20).sma_indicator()

        latest = df.iloc[-1]
        rsi = round(latest["rsi"], 2)
        macd_val = round(latest["macd"], 4)
        macd_signal = round(latest["macd_signal"], 4)
        price = round(latest["close"], 2)
        sma20 = round(latest["sma20"], 2)

        # --- Punktesystem ---
        score = 0

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

        # --- Auswertung je Modus ---
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
        elif mode == "aggressive":
            if score > 0:
                signal = "BUY"
            elif score < 0:
                signal = "SELL"
            else:
                signal = "HOLD"

        # --- Ausgabe ---
        result = (
            f"📈 *Signal für {coin.upper()}*\n\n"
            f"💰 Preis: `{price} USDT`\n"
            f"📊 RSI: `{rsi}`\n"
            f"📉 MACD: `{macd_val}` | Signal: `{macd_signal}`\n"
            f"📏 SMA20: `{sma20}`\n\n"
            f"➡️ *Empfehlung:* {signal}"
        )

        return result, "Markdown"

    except Exception as e:
        return f"⚠️ Fehler beim Abrufen der Daten für {coin.upper()}: {e}", "Markdown"
