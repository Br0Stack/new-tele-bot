from telegram.ext import Application, CommandHandler, MessageHandler, filters
import os
from pymongo import MongoClient
import asyncio

# MongoDB connection
client = MongoClient("mongodb+srv://Spenceg85:Gooddog400@cluster0.1fybtbs.mongodb.net/")
db = client.hivedb
pipeline = [
    # Match stage to filter data (if needed, based on some criteria)
    {
        "$match": {
            "date": {"$gte": start_date, "$lte": end_date}  # Example date range
        }
    },
    # Group by relevant fields
    {
        "$group": {
            "_id": {
                "shipperCity": "$Shipper city",
                "shipperState": "$Shipper state",
                "consigneeCity": "$Consignee city",
                "consigneeState": "$Consignee state",
                "trailerType": "$Trailer type"
            },
            "averageRate": {"$avg": "$Total charges from the customer"},
            "averageWeight": {"$avg": "$Weight"},
            # Add more averages or sums as needed
        }
    },
    # Sort by some field if needed
    {
        "$sort": {"_id": 1}
    }
]

# Carrier rate calculation function
def calculate_carrier_rate(load):
    # Include the rate calculation logic here
    # You can fetch data from your MongoDB and apply the formula
    historic_rate_aggregated = db.hive_cx_data.aggregate(pipeline)
    # Return a string with the calculated rate or related information
    return "Calculated rate: ..."

def calculate_basic_rate(distance, weight, base_rate):
    # Constants for rate calculation (customize these as needed)
    distance_rate_per_mile = 1.5  # example rate per mile
    weight_rate_per_pound = 0.05  # example rate per pound

    # Calculate the distance and weight components of the rate
    distance_cost = distance * distance_rate_per_mile
    weight_cost = weight * weight_rate_per_pound

    # Sum up all components to get the total rate
    total_rate = base_rate + distance_cost + weight_cost

    return total_rate

# Example usage
distance = 100  # in miles
weight = 2000  # in pounds
base_rate = 100  # base rate in dollars

rate = calculate_basic_rate(distance, weight, base_rate)

async def start_command(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Hello, welcome to Hive-Bot. Please provide your MC or DOT number to get started. Type /list to see a list of all commands that hive-bot can perform.')

async def text_message(update, context):
    if update.message and update.message.text:
        user_message = update.message.text
        
        # Example condition to check if the message is about rate calculation or quote request
        if "rate" in user_message:
            # Fetch necessary data from the database
            # For example, load data based on some criteria from the user message
            load = {}  # Replace with actual data fetching logic
            response = calculate_carrier_rate(load)
        else
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