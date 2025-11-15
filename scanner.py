import pandas as pd
from binance.client import Client
import numpy as np
import ta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOP_COINS_LIMIT = 50  # nur Top 50 Coins nach Volumen
KLINES_LIMIT = 100    # 100 Kerzen pro Coin
INTERVAL = Client.KLINE_INTERVAL_4HOUR



async def coin_scanner_top3():
    client = Client()  # Public API

    # 1. Alle USDT-Paare abrufen
    tickers = client.get_ticker()
    usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]

    # nach 24h Volumen sortieren, Top 50
    top_coins = sorted(usdt_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)[:TOP_COINS_LIMIT]
    results = []

    for t in top_coins:
        symbol = t['symbol']
        try:
            # 2. Daten holen
            klines = client.get_klines(symbol=symbol, interval=INTERVAL, limit=KLINES_LIMIT)
            df = pd.DataFrame(klines, columns=[
                "time", "open", "high", "low", "close", "volume",
                "_", "_", "_", "_", "_", "_"
            ])
            df["close"] = df["close"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)

            # 3. RSI + MACD
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            macd = ta.trend.MACD(df['close'])
            df['macd'] = macd.macd()
            df['signal'] = macd.macd_signal()

            price = df['close'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            macd_val = df['macd'].iloc[-1]
            macd_signal = df['signal'].iloc[-1]

            # Support / Resistance
            support = df['low'].min()
            resistance = df['high'].max()

            # 4. Score Berechnung
            score = 0
            # Bullish Divergence
            lows = df['low'].tail(10)
            rsi_lows = df['rsi'].tail(10)
            if len(lows) >= 2 and lows.iloc[-1] < lows.iloc[-2] and rsi_lows.iloc[-1] > rsi_lows.iloc[-2]:
                score += 50  # Divergenz stark gewichtet
            # MACD positiv
            if macd_val > macd_signal:
                score += 30
            # RSI niedrig → oversold
            if rsi < 40:
                score += 20
            # Score max = 100

            results.append({
                'coin': symbol.replace('USDT',''),
                'price': price,
                'rsi': rsi,
                'macd': macd_val,
                'macd_signal': macd_signal,
                'support': support,
                'resistance': resistance,
                'score': score
            })

        except Exception:
            continue  # Fehler überspringen

    # 5. Top 3 nach Score
    top3 = sorted(results, key=lambda x: x['score'], reverse=True)[:3]

    # 6. Telegram-Output mit allen Indikatoren
    msg = "🔥 Top 3 Coins für Bullish Reversal:\n\n"
    for i, c in enumerate(top3, start=1):
        msg += (
            f"{i}️⃣ {c['coin']}\n"
            f"💰 Preis: {c['price']:.2f} USDT\n"
            f"📊 RSI: {c['rsi']:.2f}\n"
            f"📉 MACD: {c['macd']:.4f} | Signal: {c['macd_signal']:.4f}\n"
            f"📏 Support: {c['support']:.2f} | Resistance: {c['resistance']:.2f}\n"
            f"🎯 Score: {c['score']:.0f}/100\n"
            f"📝 Empfehlung: {('starker Einstieg' if c['score']>=70 else 'möglicher Einstieg')}, möglicher Ausstieg: {c['resistance']:.2f} USDT\n\n"
        )

    return msg, "Markdown"
