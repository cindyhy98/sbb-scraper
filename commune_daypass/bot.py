import os
import re
import logging
import signal

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from datetime import datetime, timedelta
from scraper import get_availability, catch_abnormal_data
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the Telegram bot token from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

subscriptions = {}  # Store subscriptions: {chat_id: days_to_check}

# Helper function to escape special characters for Telegram MarkdownV2
def escape_markdown(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

# Helper function to send a reply with Markdown formatting
async def send_markdown_reply(update: Update, text: str):
    await update.message.reply_text(text, parse_mode="Markdown")

def validate_date(date_text):
    """Helper function to validate date input"""
    try:
        # Parse the input date
        entered_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        # Check if the entered date is strictly after today
        if entered_date > datetime.now().date():
            return True
        else:
            return False
    except ValueError:
        # If parsing fails, return False
        return False

# Helper function to format the data for Telegram
def format_for_telegram(data):
    def format_class_info(class_data):
        # Helper function to format class information for Telegram.
        if not class_data:
            return None
        availability = (
            "High Availability" if class_data['availability'] in ['A', 'D'] else "Limited Availability"
        )
        return f"CHF {int(class_data['price'] / 100)} | {availability}"

    message = ""

    for entry in data:
        travel_date = datetime.strptime(entry['travelDate'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d")
        message += f"🚆 *Travel Date*: {travel_date}\n"

        for key, train_data in entry['prices'].items():
        
            card_type = "No Discount Card" if key == "KEINE" else "With Half Fare"

            second_class_info = format_class_info(train_data.get('second'))
            first_class_info = format_class_info(train_data.get('first'))

            if second_class_info or first_class_info:
                message += f"*{card_type}*\n"
                if second_class_info:
                    message += f"  🎟️ *2nd Class*: {second_class_info}\n"
                if first_class_info:
                    message += f"  🛋️ *1st Class*: {first_class_info}\n"
                
        message += "----------------------------------------\n"
    return message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    start_text = "Welcome to SBB Day Pass Monitor Bot! 🚂\nUse /help to see all available commands."

    await send_markdown_reply(update, start_text)

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = help_text = (
        "Available commands:\n"
        "- `/start` - Receive a welcome message and introduction to the bot.\n"
        "- `/help` - Access this help guide detailing how to use the bot's features.\n"
        "- `/check <start date (YYYY-MM-DD)> <days to check>` - Check the price and availability for a specific range of dates.\n"
        "  For example: `/check 2024-12-25 10` will check from December 25, 2024, for 10 days.\n"
        "- `/monitor <days to check>` - Set a monitor for changes in price or availability starting today. The bot will notify you of any abnormalities.\n"
        "- `/stop_monitor` - Stop receiving updates and disable the monitoring feature.\n"
    )

    await send_markdown_reply(update, help_text)

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check prices and availability for a specific range of days."""
    if len(context.args) != 2:
        await send_markdown_reply(update, "Usage: /check <start date (YYYY-MM-DD)> <days to check>\nExample: /check 2024-12-25 10")
        return

    start_date = context.args[0]
    if not validate_date(start_date):
        await send_markdown_reply(update, "Invalid date format. Please enter date in YYYY-MM-DD format and make sure it is after today.")
        return

    try:
        days_to_check = int(context.args[1])
        result = get_availability(start_date, days_to_check)

        readable_output = format_for_telegram(result)

        if readable_output:
            await send_markdown_reply(update, readable_output)
        else:
            await send_markdown_reply(update, "Failed to fetch availability. Please try again later.")
    except ValueError:
        await send_markdown_reply(update, "Invalid input. Please provide a number.")
    except Exception as e:
        await send_markdown_reply(update, f"An error occurred: {e}")

# Monitor command
async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Monitor changes on prices and availability for the next n days."""
    if len(context.args) != 1:
        await send_markdown_reply(update, "Usage: /monitor <days>\nExample: /monitor 15")
        return

    chat_id = update.effective_message.chat_id
    days_to_check = int(context.args[0])
    try:
        subscriptions[chat_id] = days_to_check

        # Add a recurring job every 24 hours
        context.job_queue.run_repeating(
            send_updates,
            interval=timedelta(hours=24),
            first=timedelta(seconds=5),
            chat_id=chat_id,
            name=str(chat_id)
        )
        await send_markdown_reply(update, f"Monitoring started for the next {days_to_check} days! You will be notified of any changes.")
    except ValueError:
        await send_markdown_reply(update, "Invalid input. Please provide a number.")

async def send_updates(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch and process data, then send updates to the user."""
    chat_id = context.job.chat_id
    if chat_id not in subscriptions:
        return

    start_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    days_to_check = subscriptions[chat_id]
    result = catch_abnormal_data(get_availability(start_date, days_to_check))
    readable_output = format_for_telegram(result)

    await context.bot.send_message(chat_id=chat_id, text=f"🔔 *Update for Monitor*:\n{readable_output}", parse_mode="Markdown")

async def stop_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stops monitoring for the user."""
    chat_id = update.message.chat_id
    removed = remove_job_if_exists(str(chat_id), context)
    if removed:
        subscriptions.pop(chat_id, None)
        await send_markdown_reply(update, "Monitor stopped.")
    else:
        await send_markdown_reply(update, "No active monitor found.")

def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with the given name."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True

def stop_all_jobs(job_queue):
    """Remove all jobs from the job queue."""
    for job in job_queue.jobs():
        job.schedule_removal()
    logging.info("All monitoring jobs stopped.")

# Main function
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("check", check))
    application.add_handler(CommandHandler("monitor", monitor))
    application.add_handler(CommandHandler("stop_monitor", stop_monitor))

    # Graceful shutdown handling
    def graceful_shutdown(signal_number, frame):
        logging.info(f"Signal {signal_number} received. Stopping bot...")
        stop_all_jobs(application.job_queue)
        application.stop()
        logging.info("Bot stopped gracefully.")

    # Handle termination signals
    signal.signal(signal.SIGINT, graceful_shutdown)  # Ctrl+C
    signal.signal(signal.SIGTERM, graceful_shutdown)  # Termination signal

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()