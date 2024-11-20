from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
from scraper import get_availability  # Import the scraper

# telegram bot token
TELEGRAM_BOT_TOKEN = '7691532037:AAEoKmT7j1qHBWND_3Xh0rhZwC7goGu6Y34'

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to SBB Day Pass Monitor Bot! 🚂\n"
        "Use /monitor <days> to monitor day pass availabilities."
    )

# Monitor command
async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /monitor <days>\nExample: /monitor 15")
        return

    try:
        days_to_check = int(context.args[0])
        start_date = datetime.now().strftime("%Y-%m-%d")
        result = get_availability(start_date, days_to_check)
        
        if result:
            response_text = "Day Pass Availability:\n\n"
            for key, value in result["prices"].items():
                price = value['price']
                availability = value['availability']
                response_text += f"ID: {key}\nPrice: {price / 100:.2f} CHF\nAvailability: {availability}\n\n"
            await update.message.reply_text(response_text)
        else:
            await update.message.reply_text("Failed to fetch availability. Please try again later.")
    except ValueError:
        await update.message.reply_text("Invalid input. Please provide a number.")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

# Main function
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("monitor", monitor))

    # Start the Bot
    application.run_polling()

if __name__ == "__main__":
    main()
