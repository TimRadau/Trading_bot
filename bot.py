import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv
from signals import get_signal  # Funktion jetzt mit modus parameter

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# --- .env laden ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN nicht gefunden! Stelle sicher, dass er in der .env-Datei steht.")

# --- Zustände ---
ASK_COIN = 1

# --- Hauptmenü (ReplyKeyboard) ---
main_menu = [["/start", "/signal"], ["/cancel"]]
reply_markup_main = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 Willkommen beim Trading-Signale-Bot!\n\n"
        "⚠️ *Disclaimer:* Diese Signale basieren ausschließlich auf Indikatoren "
        "und stellen *keine Finanzberatung* dar.\n\n"
        "Verwende /signal, um ein Signal für einen Coin zu erhalten."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup_main)

# --- /signal ---
async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 Für welchen Coin möchtest du ein Signal? (z. B. BTC, SOL, ETH)",
        reply_markup=reply_markup_main
    )
    return ASK_COIN

# --- Coin-Eingabe ---
async def handle_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin = update.message.text.strip().upper()
    context.user_data["coin"] = coin

    # Inline-Buttons für Modus-Auswahl
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

    return ConversationHandler.END  # CallbackQueryHandler übernimmt jetzt


# --- Callback für Modus-Buttons ---
async def handle_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Telegram "acknowledge" Klick
    mode = query.data
    coin = context.user_data.get("coin")

    if not coin:
        await query.edit_message_text("❌ Fehler: Kein Coin ausgewählt.")
        return

    # Signal abrufen
    signal_text, parse_mode = get_signal(coin, mode)

    # InlineButtons aus der ursprünglichen Nachricht entfernen
    await query.edit_message_text(signal_text, parse_mode=parse_mode)

    # --- Hauptmenü wieder anzeigen ---
    reply_markup_main = ReplyKeyboardMarkup(
        [["/start", "/buy", "/balance", "/referral"]],
        resize_keyboard=True
    )



# --- /cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Abgebrochen.", reply_markup=reply_markup_main)
    return ConversationHandler.END

# --- Commands-Menü setzen ---
async def set_commands(application):
    commands = [
        BotCommand("start", "Starte den Bot"),
        BotCommand("signal", "Hole ein Signal für einen Coin"),
        BotCommand("cancel", "Abbrechen")
    ]
    await application.bot.set_my_commands(commands)

# --- Main ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands-Menü ohne asyncio.run(), direkt via post_init
    app.post_init = set_commands

    # ConversationHandler für Coin-Eingabe
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("signal", signal)],
        states={
            ASK_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_coin)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Handler registrieren
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_mode_callback))
    app.add_handler(CommandHandler("cancel", cancel))

    logging.info("🤖 Bot läuft ...")
    app.run_polling()

if __name__ == "__main__":
    main()
