from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, ContextTypes
from signals import get_signal  # Funktion jetzt mit modus parameter
from database import *
import random, string
from bot import ASK_COIN, ASK_REVERSAL, ASK_RESISTANCE, reply_markup_main
from telegram import LabeledPrice, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, PreCheckoutQueryHandler
import os
from divergence import get_reversal_signal
from resistance import get_support_resistance
from scanner import coin_scanner_top3


import logging
# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)



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
        "👋 Welcome to the *Trading Signals Bot!*\n\n"
        "⚠️ *Disclaimer:* These signals rely solely on technical indicators "
        "and do *not constitute financial advice*.\n\n"
        "Use /signal to receive a signal for a coin.\n"
        "Use /help to learn more about the indicators."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup_main)



# --- /help ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "ℹ️ *Explanation of the key indicators:*\n\n"
        "📊 *RSI (Relative Strength Index)* – Measures whether a coin is overbought (>70) or oversold (<30).\n"
        "📉 *MACD (Moving Average Convergence Divergence)* – Shows trend reversals: "
        "A bullish crossover (MACD > signal) is considered a buy signal.\n"
        "📏 *SMA (Simple Moving Average)* – Average price over a period. "
        "If the current price is above the SMA, it indicates an uptrend.\n"
        "🎯 *Confidence* – Shows how strongly the indicators align (0–100 %).\n"
        "📈 *Trend* – Detects whether the market is currently rising, falling, or moving sideways."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=reply_markup_main)

# --- /signal ---
async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 Which coin would you like a signal for? (e.g. BTC, SOL, ETH)",
        reply_markup=reply_markup_main
    )
    return ASK_COIN

# --- /reversal ---
async def reversal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 Which coin would you like a signal for? (e.g. BTC, SOL, ETH)",
        reply_markup=reply_markup_main
    )
    return ASK_REVERSAL


async def handle_reversal_coin(update, context):
    coin = update.message.text.strip()

    # Deine eigentliche Analysefunktion
    result, mode = get_reversal_signal(coin)

    await update.message.reply_text(result, parse_mode=mode)

    return ConversationHandler.END

# --- /resistance ---
async def resistance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 Which coin would you like a signal for? (e.g. BTC, SOL, ETH)",
        reply_markup=reply_markup_main
    )
    return ASK_RESISTANCE


async def handle_resistance_coin(update, context):
    coin = update.message.text.strip()

    # Deine eigentliche Analysefunktion
    result, mode = get_support_resistance(coin)

    await update.message.reply_text(result, parse_mode=mode)

    return ConversationHandler.END


# --- /scan ---

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await coin_scanner_top3()
    await update.message.reply_text(msg[0], parse_mode=msg[1])


# --- /compare ---
async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    premium = get_premium(user_id)

    if not premium["is_premium"]:
        await update.message.reply_text("❌ You need Premium to use this feature.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("❌ Please provide exactly two coins. Example:\n/compare BTC ETH")
        return

    coin1, coin2 = context.args[0].upper(), context.args[1].upper()

    # Verwende den 'balanced'-Modus standardmäßig
    text1, _ = get_signal(coin1, "balanced")
    text2, _ = get_signal(coin2, "balanced")

    # Extrahiere die Empfehlung & Confidence aus dem Text
    import re

    def extract_values(text):
        match_signal = re.search(r"\*Recommendation:\* ([^\n]+)", text)
        match_conf = re.search(r"Confidence: `(\d+)%`", text)
        signal = match_signal.group(1) if match_signal else "?"
        confidence = int(match_conf.group(1)) if match_conf else 0
        return signal, confidence

    sig1, conf1 = extract_values(text1)
    sig2, conf2 = extract_values(text2)

    # Bewertung wer stärker ist
    if conf1 > conf2:
        stronger = f"{coin1} is stronger."
    elif conf2 > conf1:
        stronger = f"{coin2} is stronger."
    else:
        stronger = "Both equally strong."

    response = (
        f"📊 *Comparison Analysis*\n\n"
        f"{coin1}: *{sig1}* ({conf1}%)\n"
        f"{coin2}: *{sig2}* ({conf2}%)\n\n"
        f"➡️ *Recommendation:* {stronger}"
    )

    await update.message.reply_text(response, parse_mode="Markdown")


# --- Coin-Eingabe ---
async def handle_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin = update.message.text.strip().upper()
    context.user_data["coin"] = coin
    user_id = update.effective_user.id
    premium = get_premium(user_id)
    if not premium["is_premium"]:
        await update.message.reply_text("You need Premium to unlock Balanced and Aggressive modes.")
        keyboard = [
            [InlineKeyboardButton("Safe", callback_data="safe")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("Safe", callback_data="safe")],
            [InlineKeyboardButton("Balanced", callback_data="balanced")],
            [InlineKeyboardButton("Aggressive", callback_data="aggressive")]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚙️ Select the mode for the signal calculation:",
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
        await query.edit_message_text("❌ Error: No coin selected.")
        return

    signal_text, parse_mode = get_signal(coin, mode)
    await query.edit_message_text(signal_text, parse_mode=parse_mode)

# --- /cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.", reply_markup=reply_markup_main)
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
            link = f"insert Binance link here"
            msg = f"🎉 You have {invites_count} invitations!\nHere is your premium link:\n{link}"
        else:
            msg = (
                f"🔗 You currently have {invites_count} invitations.\n"
                "Invite at least 3 friends to unlock your link.\n"
                f"Invite friends using this link: {ref_link}"
            )

        await update.message.reply_text(msg, reply_markup=reply_markup_main)



## KAUFEN KAUFEN KAUFEN

# --- 1. Befehl zum Starten des Kaufs ---
async def buy_premium(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    title = "Activate Premium"
    description = "Get access to premium features of your bot."
    payload = "premium_upgrade"        # internal identifier
    currency = "XTR"                   # Telegram Stars
    prices = [LabeledPrice("Premium Access", 1)]  # 500 Stars


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
    await update.message.reply_text("✅ Payment received! Your premium is now active.")




# --- Support and Terms ---

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = (
        "📞 *Support*\n\n"
        "For support, please send a message to: @Tim9831\n"
        f"Your User ID is: `{user_id}`\n\n"
        "Please provide this User ID when contacting support."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")




async def terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📜 *Terms & Conditions*\n\n"
        "Please read these terms carefully before using this bot.\n\n"

        "1️⃣ *No Financial Advice*\n"
        "The information, signals, analyses, indicators, and recommendations provided by this bot "
        "*do not constitute financial advice, investment advice, or a buy/sell recommendation*. "
        "All content is solely for *informational and educational purposes*.\n\n"

        "2️⃣ *Use of Data & Indicators*\n"
        "The signals rely on publicly accessible market prices, technical indicators "
        "(e.g. RSI, MACD, MA, volume analyses), and data from third parties. "
        "This data may be incomplete, delayed, or inaccurate. "
        "There is *no guarantee of accuracy or timeliness*.\n\n"

        "3️⃣ *Third-Party APIs (e.g. Binance)*\n"
        "This bot uses data from third-party APIs. "
        "The bot is *not affiliated* with Binance or any other exchange. "
        "All API data is subject to their terms of use. "
        "Third parties can change, restrict, or disable their APIs at any time. "
        "The operator assumes no responsibility for outages or discrepancies.\n\n"

        "4️⃣ *No Profit Guarantee*\n"
        "Cryptocurrencies are highly volatile and involve considerable risk. "
        "There is *no guarantee* of profits, price developments, or successful trades. "
        "Past performance is not indicative of future results.\n\n"

        "5️⃣ *Personal Responsibility*\n"
        "You always act *at your own risk*. "
        "You are responsible for conducting your own research (DYOR) "
        "and making informed decisions.\n\n"

        "6️⃣ *Limitation of Liability*\n"
        "The operator of this bot accepts *no liability* for losses, damages, or "
        "other consequences arising from the use of the signals, data, or functions. "
        "Use is entirely at your own risk.\n\n"

        "7️⃣ *Technical Risks*\n"
        "The operator is not liable for:\n"
        "- Server outages\n"
        "- API failures or delays\n"
        "- Incorrect or incomplete data\n"
        "- Bot malfunctions\n"
        "- Issues caused by Telegram itself\n"
        "There is no entitlement to constant availability or functionality.\n\n"

        "8️⃣ *Use of the Bot*\n"
        "By using this bot you confirm that you are at least 18 years old "
        "and meet the legal requirements of your country for trading cryptocurrencies.\n\n"

        "9️⃣ *Payments & Services*\n"
        "For payments (e.g. premium features via Telegram Stars):\n"
        "- There is *no entitlement to specific signal performance*.\n"
        "- Services can be changed, expanded, or discontinued at any time.\n"
        "- There are *no refunds* unless required by law.\n\n"

        "🔟 *Data Protection*\n"
        "The bot stores only the data necessary for operation "
        "(e.g. Telegram user ID). No data is sold or shared with third parties.\n\n"

        "1️⃣1️⃣ *Changes to the Terms*\n"
        "The operator may update these terms at any time. Changes take effect "
        "immediately upon publication.\n\n"

        "💬 If you have questions, please use the /support command.\n\n"
        "By using this bot you fully agree to these terms."
    )

    await update.message.reply_text(msg, parse_mode='Markdown')
