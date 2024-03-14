from enum import Enum
from telegram import Update, ForceReply, ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
import logging
from pymongo import MongoClient
import os
import re

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY")
FMCSA_API_KEY = os.getenv("FMCSA_API_KEY")
MONGO_CLIENT = os.getenv("MONGO_CLIENT")

# MongoDB setup
client = MongoClient(MONGO_CLIENT)
db = client['hivedb']

# Conversation states
(START, AWAITING_MC_DOT, VERIFY, RATE_QUOTE, AWAITING_RATE_INFO, END) = range(6)

# Helper functions
def get_lookup_url(number, lookup_type):
    base_url = 'https://mobile.fmcsa.dot.gov/qc/services/carriers/'
    if lookup_type == "DOT":
        return f"{base_url}{number}?webKey={FMCSA_API_KEY}"
    else:
        return f"{base_url}docket-number/{number}?webKey={FMCSA_API_KEY}"

def validate_mc_dot_number(number):
    """Simulate MC/DOT number validation"""
    # This function should implement actual validation logic
    return True

def calculate_rate_quote(load_criteria):
    """Calculate rate quote based on load criteria"""
    # Placeholder for rate calculation logic
    return "$1000.00"

def extract_load_criteria(message):
    """Extract load criteria from user message"""
    # Placeholder for extraction logic
    return {}

# Command handlers
async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Hi! Please enter your MC or DOT number to get started.', reply_markup=ReplyKeyboardRemove())
    return AWAITING_MC_DOT

async def rate_quote(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Please provide details about the load for a rate quote.', reply_markup=ReplyKeyboardRemove())
    return AWAITING_RATE_INFO

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Message handlers
async def mc_dot_received(update: Update, context: CallbackContext) -> int:
    number = update.message.text
    if validate_mc_dot_number(number):
        await update.message.reply_text('MC/DOT number validated. You can now request a rate quote with /rate_quote.', reply_markup=ReplyKeyboardRemove())
        return END
    else:
        await update.message.reply_text('Invalid MC/DOT number, please try again.', reply_markup=ReplyKeyboardRemove())
        return AWAITING_MC_DOT

async def rate_info_received(update: Update, context: CallbackContext) -> int:
    message = update.message.text
    load_criteria = extract_load_criteria(message)
    rate = calculate_rate_quote(load_criteria)
    await update.message.reply_text(f'Estimated rate: {rate}', reply_markup=ReplyKeyboardRemove())
    return END

# Error handler
def error(update: Update, context: CallbackContext):
    logger.warning(f'Update "{update}" caused error "{context.error}"')

if __name__ == '__main__':
    application = Application.builder().token(TELEGRAM_API_KEY).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            AWAITING_MC_DOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, mc_dot_received)],
            AWAITING_RATE_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, rate_info_received)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_error_handler(error)

    application.run_polling()

# ----------------------

class ConversationState(Enum):
    START = 1
    COLLECTING_RATE_INFO = 2
    CALCULATING_RATE = 3
    COMPLETED = 4

async def chat_with_gpt_for_rate_info(chat_id, user_message, user_data):
    try:
        state = user_data.get("state", ConversationState.START)

        if state == ConversationState.START:
            # Handle initial conversation logic
            # ...

            # Update state to COLLECTING_RATE_INFO
            user_data["state"] = ConversationState.COLLECTING_RATE_INFO

        # ...

        elif state == ConversationState.COLLECTING_RATE_INFO:
            # Handle collecting rate info logic
            # ...
            
            
            # Check if the user has provided all the necessary rate info
            next_key = next_key_to_collect(user_data)
            if next_key:
                await Bot.bot.send_message(chat_id=chat_id, text=f"Please provide the {next_key}.")
                return ConversationState.COLLECTING_RATE_INFO
            else:
                # All rate info collected, calculate the rate
                await Bot.bot.send_message(chat_id=chat_id, text="Calculating rate quote...")
                user_data["state"] = ConversationState.CALCULATING_RATE

        elif state == ConversationState.CALCULATING_RATE:
        # Handle calculating rate logic
        # ...

        # Update state to COMPLETED
            user_data["state"] = ConversationState.COMPLETED

        elif state == ConversationState.COMPLETED:
        # Handle completed conversation logic
        # ...

        # Reset state to START for a new conversation
            user_data["state"] = ConversationState.START

        else:
        # Handle unknown state
            return "Unknown conversation state."

        # Return the bot's response message
        return "ok"

    except Exception as e:
        logger.error(f"Error in chat_with_gpt_for_rate_info: {e}")
        return "Sorry, I couldn't process that due to an error."

def next_key_to_collect(rate_info):
    required_keys = ["Bill distance", "Weight", "Equipment type", "Shipper city", "Shipper state", "Consignee city", "Consignee state", "Hazmat", "Extra stops", "Driver assistance", "Storage days", "Toll charges"]
    formatted_keys = [key.split()[0].capitalize() + " " + key.split()[1].lower() if len(key.split()) > 1 else key.capitalize() for key in required_keys]
    required_keys = formatted_keys
    formatted_keys = [key.split()[0].capitalize() + " " + key.split()[1].lower() if len(key.split()) > 1 else key.capitalize() for key in required_keys]
    for key in formatted_keys:
        if key not in rate_info:
            return key
    return None
    # distance_pattern = r"\b(?:distance\s*[:=]?\s*|)(\d+)\s*(?:miles?|mi\b)"
    # shipper_zip_pattern = r"\b(?:shipper(?:'s)?\s(?:zip(?:\scode)?|code)\s*[:=]?\s*|)(\d{5})\b" 
    # consignee_zip_pattern = r"\b(?:consignee(?:'s)?\s(?:zip(?:\scode)?|code)\s*[:=]?\s*|)(\d{5})\b"
    #     driver_assist_pattern = r"\bdriver\s(?:assistance|assist|help|aid|support|service)\b"
    
    
