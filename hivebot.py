from telegram.ext import Application, CommandHandler, MessageHandler, filters
import os
from pymongo import MongoClient
import asyncio

# MongoDB connection
client = MongoClient("mongodb+srv://Spenceg85:Gooddog400@cluster0.1fybtbs.mongodb.net/")
db = client.hivedb

# Carrier rate calculation function
def calculate_carrier_rate(load):
    start_date = load["start_date"]
    end_date = load["end_date"]
    
    # Example aggregation pipeline to calculate the rate
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
    # Include the rate calculation logic here
    # You can fetch data from your MongoDB and apply the formula
    historic_rate_aggregated = db.hive_cx_data.aggregate(pipeline)
    # Return a string with the calculated rate or related information
    return "Calculated rate: ..."

def calculate_carrier_rate(distance, weight, base_rate):
    # Constants for rate calculation (customize these as needed)
    distance_rate_per_mile = 1.5  # example rate per mile
    weight_rate_per_pound = 0.05  # example rate per pound

    # Calculate the distance and weight components of the rate
    distance_cost = distance * distance_rate_per_mile
    weight_cost = weight * weight_rate_per_pound

    # Sum up all components to get the total rate
    total_rate = base_rate + distance_cost + weight_cost

    return total_rate

async def start_command(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Hello, welcome to Hive-Bot. Please provide your MC or DOT number to get started. Type /list to see a list of all commands that hive-bot can perform.')

async def text_message(update, context):
    if update.message and update.message.text:
        user_message = update.message.text.lower()
        
        # Example condition to check if the message is about rate calculation or quote request
        if "rate" in user_message:
            # Parse the message for distance, weight, and base rate
            # For simplicity, let's assume the user inputs text in a specific format like 'distance: 100, weight: 2000, base rate: 100'
            # In a real-world scenario, you might want to use more sophisticated parsing or NLP techniques
            distance = None
            weight = None
            base_rate = None

    for part in user_message.split(','):
        if 'distance:' in part:
            distance = float(part.split(':')[1].strip())
        elif 'weight:' in part:
            weight = float(part.split(':')[1].strip())
        elif 'base rate:' in part:
            base_rate = float(part.split(':')[1].strip())
            # Check for missing information and prompt the user
    missing_info = []
    if distance is None:
        missing_info.append("distance")
    if weight is None:
        missing_info.append("weight")
    if base_rate is None:
        missing_info.append("base rate")

    if missing_info:
        response = f"Please provide the following missing information: {', '.join(missing_info)}."
    else:
        # Calculate the rate
        rate = calculate_carrier_rate(distance, weight, base_rate)
        response = f"Calculated Rate: ${rate:.2f}"
        
        # Fetch necessary data from the database
        # For example, load data based on some criteria from the user message
        load = {}  # Replace with actual data fetching logic
        response += ' Based on the load details you provided and historical load rates for similar loads, this should be a fair price for this load: ' + calculate_carrier_rate(load) + ' Is there anything else I can help you with?'
        
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

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