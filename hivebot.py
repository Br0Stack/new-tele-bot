from telegram.ext import Application, CommandHandler, MessageHandler, filters
import os
from pymongo import MongoClient
import asyncio

# MongoDB connection
client = MongoClient("mongodb+srv://Spenceg85:Gooddog400@cluster0.1fybtbs.mongodb.net/")
db = client.hivedb

# Carrier rate calculation function
def calculate_carrier_rate(load):
    # Include the rate calculation logic here
    # You can fetch data from your MongoDB and apply the formula
    # Return a string with the calculated rate or related information
    return "Calculated rate: ..."

async def start_command(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Hello, welcome to Hive-Bot. How can I help you today?')

async def text_message(update, context):
    if update.message and update.message.text:
        user_message = update.message.text
        
        # Example condition to check if the message is about rate calculation or quote request
        if "rate" in user_message:
            # Fetch necessary data from the database
            # For example, load data based on some criteria from the user message
            load = {}  # Replace with actual data fetching logic
            response = calculate_carrier_rate(load)
        else:
            response = 'I understood your message: ' + user_message
        
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    else:
        # Handle non-text updates or messages without text here
        pass

if __name__ == '__main__':
    application = Application.builder().token(os.environ["TELEGRAM_API_KEY"]).build()

    # Handlers
    start_command_handler = CommandHandler('start', start_command)
    text_message_handler = MessageHandler(filters.TEXT, text_message)

    # Adding handlers to the application
    application.add_handler(start_command_handler)
    application.add_handler(text_message_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()