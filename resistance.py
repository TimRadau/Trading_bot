import pandas as pd
from binance.client import Client
import numpy as np

def get_support_resistance(coin: str):
    symbol = coin.upper() + "USDT"
    client = Client()  # Public API ohne Key

    # Holen von 200 Kerzen 4H-Chart
    klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_4HOUR, limit=200)
    df = pd.DataFrame(klines, columns=[
        "time", "open", "high", "low", "close", "volume",
        "_", "_", "_", "_", "_", "_"
    ])
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)

    # Lokale Hochs/Lows erkennen
    window = 5
    df['local_high'] = df['high'][(df['high'].shift(2) < df['high'].shift(1)) &
                                  (df['high'].shift(1) < df['high']) &
                                  (df['high'].shift(-1) < df['high']) &
                                  (df['high'].shift(-2) < df['high'])]

    df['local_low'] = df['low'][(df['low'].shift(2) > df['low'].shift(1)) &
                                (df['low'].shift(1) > df['low']) &
                                (df['low'].shift(-1) > df['low']) &
                                (df['low'].shift(-2) > df['low'])]

    # Letzte Support/Resistance bestimmen
    support = df['local_low'].dropna().tail(1).values[0] if not df['local_low'].dropna().empty else None
    resistance = df['local_high'].dropna().tail(1).values[0] if not df['local_high'].dropna().empty else None
    price = df['close'].iloc[-1]

    # Entfernung zum Support/Resistance
    support_dist = (price - support) if support else None
    resistance_dist = (resistance - price) if resistance else None

    # Einschätzung
    if support and support_dist is not None:
        if support_dist/price < 0.01:  # <1% entfernt
            support_msg = "Preis sehr nah am Support → möglicher Bounce"
        else:
            support_msg = f"Abstand zum Support: {support_dist:.2f} USDT"
    else:
        support_msg = "Kein Support gefunden"

    if resistance and resistance_dist is not None:
        if resistance_dist/price < 0.01:
            resistance_msg = "Preis sehr nah an Resistance → mögliches Ende des Aufwärtstrends"
        else:
            resistance_msg = f"Abstand zur Resistance: {resistance_dist:.2f} USDT"
    else:
        resistance_msg = "Keine Resistance gefunden"

    # Ausgabe
    result = (
        f"📈 *Support/Resistance für {coin.upper()}*\n\n"
        f"💰 Aktueller Preis: `{price:.2f} USDT`\n"
        f"📏 Support: `{support}`\n"
        f"📏 Resistance: `{resistance}`\n"
        f"📝 Einschätzung:\n"
        f"{support_msg}\n"
        f"{resistance_msg}"
    )

    return result, "Markdown"
