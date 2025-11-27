import logging
import os
from telegram import BotCommand
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
    raise ValueError("BOT_TOKEN nicht gefunden! Stelle sicher, dass er in der .env-Datei steht.")

# --- Zustände ---
ASK_COIN = 1
ASK_REVERSAL = 2
ASK_RESISTANCE = 3


# --- Commands-Menü setzen ---
async def set_commands(application):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Explanation of indicators"),
        BotCommand("signal", "Get a trading signal for a coin"),
        BotCommand("reversal", "Detect market reversal points"),
        BotCommand("resistance", "Find support & resistance levels"),
        BotCommand("scan", "Scan for top coins likely to rise next"),
        BotCommand("compare", "Compare two coins"),
        BotCommand("referral", "Invite friends and earn rewards"),
        BotCommand("buy", "Purchase Premium access"),
        #BotCommand("stars", "Show earned Telegram Stars"),
        BotCommand("support", "Contact support"),
        BotCommand("terms", "Terms and Conditions"),
        BotCommand("cancel", "Cancel the current action")
    ]
    await application.bot.set_my_commands(commands)





# --- Main ---
def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )
    app.post_init = set_commands

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("signal", signal)],
        states={ASK_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_coin)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_handler_reversal = ConversationHandler(
        entry_points=[CommandHandler("reversal", reversal)],
        states={ASK_REVERSAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reversal_coin)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_handler_resistance = ConversationHandler(
        entry_points=[CommandHandler("resistance", resistance)],
        states={ASK_RESISTANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_resistance_coin)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(conv_handler)
    app.add_handler(conv_handler_reversal)
    app.add_handler(conv_handler_resistance)
    app.add_handler(CallbackQueryHandler(handle_mode_callback))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("compare", compare_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("buy", buy_premium))
    app.add_handler(CommandHandler("reversal", reversal))
    app.add_handler(CommandHandler("resistance", resistance))
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("stars", stars))
    app.add_handler(CommandHandler("terms", terms))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(CommandHandler("support", support))



    logging.info("🤖 Bot läuft ...")
    app.run_polling()

if __name__ == "__main__":
    main()
