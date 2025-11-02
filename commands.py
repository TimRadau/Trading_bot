from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, ContextTypes
from signals import get_signal  # Funktion jetzt mit modus parameter
from database import *
import random, string
from bot import ASK_COIN, reply_markup_main
from telegram import LabeledPrice, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, PreCheckoutQueryHandler
import os





# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Referral-Code aus /start Parameter (falls vorhanden)
    ref_code = None
    if context.args:
        ref_code = context.args[0]  # z. B. REF_ABC123

    user_id = update.effective_user.id
    username = update.effective_user.username
    user = get_user(user_id)

    # User existiert noch nicht -> anlegen
    if not user:
        invited_by = None
        if ref_code:
            inviter = get_user_by_referral(ref_code)
            if inviter:
                invited_by = inviter['referral_code']  # oder inviter['telegram_id'] für Zähler
        add_user(user_id, username, invited_by)
        user = get_user(user_id)

        # Wenn eingeladen -> Referral-Zähler erhöhen
        if invited_by:
            increment_referral(invited_by)

    # normale Begrüßung
    welcome_text = (
        "👋 Willkommen beim *Trading-Signale-Bot!*\n\n"
        "⚠️ *Disclaimer:* Diese Signale basieren ausschließlich auf technischen Indikatoren "
        "und stellen *keine Finanzberatung* dar.\n\n"
        "Nutze /signal, um ein Signal für einen Coin zu erhalten.\n"
        "Verwende /help, um mehr über die Indikatoren zu erfahren."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup_main)



# --- /help ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "ℹ️ *Erklärung der wichtigsten Indikatoren:*\n\n"
        "📊 *RSI (Relative Strength Index)* – Misst, ob ein Coin überkauft (>70) oder überverkauft (<30) ist.\n"
        "📉 *MACD (Moving Average Convergence Divergence)* – Zeigt Trendwenden: "
        "Ein Bullish Crossover (MACD > Signal) gilt als Kaufsignal.\n"
        "📏 *SMA (Simple Moving Average)* – Durchschnittspreis über einen Zeitraum. "
        "Wenn der aktuelle Preis über der SMA liegt, spricht das für einen Aufwärtstrend.\n"
        "🎯 *Confidence* – Zeigt, wie stark die Indikatoren übereinstimmen (0–100 %).\n"
        "📈 *Trend* – Erkennt, ob der Markt aktuell steigt, fällt oder seitwärts läuft."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=reply_markup_main)

# --- /signal ---
async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 Für welchen Coin möchtest du ein Signal? (z. B. BTC, SOL, ETH)",
        reply_markup=reply_markup_main
    )
    return ASK_COIN

# --- /compare ---
async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("❌ Bitte gib genau zwei Coins an. Beispiel:\n/compare BTC ETH")
        return

    coin1, coin2 = context.args[0].upper(), context.args[1].upper()

    # Verwende den 'balanced'-Modus standardmäßig
    text1, _ = get_signal(coin1, "balanced")
    text2, _ = get_signal(coin2, "balanced")

    # Extrahiere die Empfehlung & Confidence aus dem Text
    import re

    def extract_values(text):
        match_signal = re.search(r"Empfehlung:\* (\w+)", text)
        match_conf = re.search(r"Confidence: `(\d+)%`", text)
        signal = match_signal.group(1) if match_signal else "?"
        confidence = int(match_conf.group(1)) if match_conf else 0
        return signal, confidence

    sig1, conf1 = extract_values(text1)
    sig2, conf2 = extract_values(text2)

    # Bewertung wer stärker ist
    if conf1 > conf2:
        stronger = f"{coin1} stärker."
    elif conf2 > conf1:
        stronger = f"{coin2} stärker."
    else:
        stronger = "Beide gleich stark."

    response = (
        f"📊 *Vergleichsanalyse*\n\n"
        f"{coin1}: *{sig1}* ({conf1}%)\n"
        f"{coin2}: *{sig2}* ({conf2}%)\n\n"
        f"➡️ *Empfehlung:* {stronger}"
    )

    await update.message.reply_text(response, parse_mode="Markdown")


# --- Coin-Eingabe ---
async def handle_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin = update.message.text.strip().upper()
    context.user_data["coin"] = coin

    keyboard = [
        [InlineKeyboardButton("Safe", callback_data="safe")],
        [InlineKeyboardButton("Balanced", callback_data="balanced")],
        [InlineKeyboardButton("Aggressive", callback_data="aggressive")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚙️ Wähle den Modus für die Signalberechnung:",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

# --- Callback für Modus-Buttons ---
async def handle_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mode = query.data
    coin = context.user_data.get("coin")

    if not coin:
        await query.edit_message_text("❌ Fehler: Kein Coin ausgewählt.")
        return

    signal_text, parse_mode = get_signal(coin, mode)
    await query.edit_message_text(signal_text, parse_mode=parse_mode)

# --- /cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Abgebrochen.", reply_markup=reply_markup_main)
    return ConversationHandler.END




def generate_ref_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# --- Referral ---
async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    # User noch nicht in DB -> anlegen
    if not user:
        ref_code = generate_ref_code()
        invited_by = None
        if context.args:
            inviter_code = context.args[0]
            # inviter suchen
            inviter = get_user_by_referral(inviter_code)  # neue Hilfsfunktion
            if inviter:
                invited_by = inviter['referral_code']  # oder 'telegram_id', je nach DB-Logik
        add_user(user_id, update.effective_user.username, invited_by)
        user = get_user(user_id)

    ref_code = user['referral_code']
    invites_count = user['referrals_count']
    ref_link = f"https://t.me/Trading_signals_pr_bot?start={ref_code}"
    if invites_count >= 3:
        link = f"hier binance link einfügen"
        msg = f"🎉 Du hast {invites_count} Einladungen!\nHier ist dein Premium-Link:\n{link}"
    else:
        msg = f"🔗 Du hast bisher {invites_count} Einladungen.\nLade mindestens 3 Freunde ein, um deinen Link freizuschalten.\n Lade freunde ein mit dem Link: {ref_link}"

    await update.message.reply_text(msg, reply_markup=reply_markup_main)


## KAUFEN KAUFEN KAUFEN

# --- 1. Befehl zum Starten des Kaufs ---
async def buy_premium(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    title = "Premium freischalten"
    description = "Erhalte Zugriff auf Premium-Features deines Bots."
    payload = "premium_upgrade"        # interne Kennung
    currency = "XTR"                   # Telegram Stars
    prices = [LabeledPrice("Premium Zugang", 1)]  # 500 Stars

    await context.bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",  # leer lassen bei digitalen Gütern
        currency=currency,
        prices=prices,
        start_parameter="premium-stars"
    )


# --- 2. Pre-Checkout bestätigen ---
async def precheckout(update: Update, context: CallbackContext):
    query = update.pre_checkout_query
    await query.answer(ok=True)


# --- 3. Nach erfolgreicher Zahlung ---
async def successful_payment(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    set_premium(user_id, True)  # DB-Spalte 'ispremium' auf "ja"
    await update.message.reply_text("✅ Zahlung erhalten! Dein Premium ist jetzt aktiv.")
