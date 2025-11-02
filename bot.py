import logging
import os
from telegram import BotCommand, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv
from database import *
from commands import *

# DB initialisieren
init_db()

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
main_menu = [["/start", "/signal", "/help"], ["/cancel"]]
reply_markup_main = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)


# --- Commands-Menü setzen ---
async def set_commands(application):
    commands = [
        BotCommand("start", "Starte den Bot"),
        BotCommand("signal", "Hole ein Signal für einen Coin"),
        BotCommand("help", "Erklärung der Indikatoren"),
        BotCommand("cancel", "Abbrechen"),
        BotCommand("compare", "Vergleiche zwei Coins"),
        BotCommand("referral", "Lade Freunde ein"),
        BotCommand("buy", "kaufe Premium")

    ]
    await application.bot.set_my_commands(commands)





# --- Main ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.post_init = set_commands

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("signal", signal)],
        states={ASK_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_coin)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_mode_callback))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("compare", compare_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("buy", buy_premium))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))



    logging.info("🤖 Bot läuft ...")
    app.run_polling()

if __name__ == "__main__":
    main()
