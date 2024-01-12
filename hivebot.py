from telegram import ForceReply, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, ContextTypes, CommandHandler, ConversationHandler, MessageHandler, filters
import os
import requests
import logging
from pymongo import MongoClient
import asyncio

FMCSA_API_KEY = os.environ['FMCSA_API_KEY']  # FMCSA webKey
MONGO_CLIENT = os.environ['MONGO_CLIENT']  # MongoDB connection string

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# MongoDB connection
client = MongoClient(MONGO_CLIENT)
db = client.hivedb

# Define states for the conversation
# CHOOSING, TYPING_REPLY = range(2)
NUMBER, VERIFY, CONFIRM_COMPANY, REENTER_NUMBER = range(4)

# Define command handlers. These usually take the two arguments update and context
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Hi, welcome to Hive-Bot! Please enter your MC or DOT number to get started.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return NUMBER

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")
    
async def received_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    number = update.message.text
    context.user_data['number'] = number
    
   # Attempt to verify the MC/DOT number
    response = await verify_number(number)
    if response and response['status'] == 'verified':
        companyName = response['data']['carrier']['legalName'] or response['data']['carrier']['dbaName']
        reply_keyboard = [['YES', 'NO']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        await update.message.reply_text(f"Is your company name {companyName}?", reply_markup=markup)
        return CONFIRM_COMPANY
    if response and response['status'] == 'verified':
        await update.message.reply_text("Your MC/DOT was successfully verified. Hive Bot features fully activated.")
        # Store the MC/DOT and user in the hive database
        try:  
            db.users.update_one({'chat_id': update.effective_chat.id}, {'$set': {'mc_dot_number': number, 'fmcsa_data': response}}, upsert=True)
        except Exception as e:
            logger.error(f"Database error: {e}")
    elif response and response['status'] == 'ask':
        companyName = response[0]['legalName'] or response[0]['dbaName']
        reply_keyboard = [['YES', 'NO']]
        markup = ReplyKeyboardMarkup(reply_keyboard, input_field_placeholder="Is your company name {companyName}?", one_time_keyboard=True)
        await update.message.reply_text(f"Is your company name {companyName}?", markup)
        if update.message.text == 'YES':
            await update.message.reply_text("Your MC/DOT was successfully verified. You can now use Hive Bot.")
            # Store the MC/DOT and user in the hive database
            try:  
                db.users.update_one({'chat_id': update.effective_chat.id}, {'$set': {'mc_dot_number': number, 'fmcsa_data': response}}, upsert=True)
            except Exception as e:
                logger.error(f"Database error: {e}")
        else: 
            await update.message.reply_text("Please re-enter your MC/DOT number.")
    elif response and response['status'] == 'not_verified':
        await update.message.reply_text("Your MC/DOT number could not be authorized. Please try again or contact support.")
    else:
        await update.message.reply_text("I couldn't find any MC/DOT info for that number. Please try again or contact support.")
    return ConversationHandler.END

async def confirm_company(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_response = update.message.text
    if user_response == 'YES':
        await update.message.reply_text("Your MC/DOT was successfully verified. You can now use Hive Bot.")
        # Store the MC/DOT and user in the hive database
        # ... [Database storing logic]
        return VERIFY  # Or any other state to continue the conversation
    elif user_response == 'NO':
        await update.message.reply_text("Please re-enter your MC/DOT number.")
        return REENTER_NUMBER

async def reenter_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Enter your MC or DOT number:", reply_markup=ReplyKeyboardRemove())
    return NUMBER

async def verify_number(number: str) -> dict:
    """Verify the MC or DOT number."""
    # First, try with DOT number
    response = await verify_dot(number)
    if response['status'] == 'verified':
        return response
    elif response['status'] == 'not_verified':
    # If DOT fails, try with MC number
        response = await verify_mc(number)
        return response
    else:
        return {'status': 'error', 'message': 'Error verifying MC/DOT number.'}

# async def save_mc_dot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Save the MC or DOT number to the database."""
#     user_data = context.user_data
#     choice = user_data['choice']
#     number = update.message.text
        
#     try:
#             # Verify the MC/DOT number
#             response = await verify_mc_dot(number) 
#             print(response)
#             # requests.get("https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{user_message}?webKey={}")
#             if response and response['status']== 'verified':
#                 dbaName = response['data']['carrier']['legalName'] or response['data']['carrier']['dbaName']
#                 await update.message.reply_text(f"Is your company name {dbaName}? If not, please re-enter your MC/DOT number.")
#                 await context.bot.send_message(chat_id=update.effective_chat.id, text='Your MC/DOT number has been verified. You can now use Hive Bot.')
#             else:
#                 await context.bot.send_message(chat_id=update.effective_chat.id, text='Your MC/DOT number could not be verified. Please try again or contact support.')
#     except Exception as e:
#             logger.error(f"Database error: {e}")
#             await update.message.reply_text("Sorry, there was an error verifying user details.")           
#             return ConversationHandler.END


def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancels and ends the conversation."""
        update.message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardMarkup(one_time_keyboard=True))
        return ConversationHandler.END
    
# async def start_command(update, context):
#     await context.bot.send_message(chat_id=update.effective_chat.id, text='Hello, welcome to Hive-Bot. Please provide your MC or DOT number to get started. Type /list to see a list of all commands that hive-bot can perform.')

async def verify_dot(user_message):
    dot_number = user_message # request.json['mc_dot_number']
    # Make the API call to FMCSA lookup API
    response = requests.get(f"https://mobile.fmcsa.dot.gov/qc/services/carriers/{dot_number}?webKey={FMCSA_API_KEY}")
    print(response.json())
    details = response.json()['content']
    # Check the conditions
    if details and details['carrier']['allowedToOperate'].upper() in ['Y', 'YES']:
        return {'status': 'verified', 'message': 'MC/DOT number verified.', 'data': details}
    else:
        return {'status': 'not_verified', 'message': 'DOT info not found. Please re-enter an MC or DOT number.'} 
    
async def verify_mc(user_message):
    mc_number = user_message # request.json['mc_dot_number']
    # Make the API call to FMCSA lookup API
    response = requests.get(f"https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{mc_number}?webKey={FMCSA_API_KEY}")
    print(response.json())
    if response.status_code == 200 and response.json()["content"]:
        # Check the conditions
        if response.json()['content'][0]:
            return {'status': 'ask', 'message': 'MC/DOT number verified.', 'data': response.json()["content"]}
        else:
            return {'status': 'not_verified', 'message': 'MC info not found. Please re-enter an MC or DOT number.'}

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
    return historic_rate_aggregated

def calculate_carrier_rate(distance, weight, base_rate, consignee_city, consignee_state, shipper_city, shipper_state):
    # Constants for rate calculation (customize these as needed)
    distance_rate_per_mile = 1.5  # example rate per mile
    weight_rate_per_pound = 0.05  # example rate per pound

    # Calculate the distance and weight components of the rate
    distance_cost = distance * distance_rate_per_mile
    weight_cost = weight * weight_rate_per_pound

    # Sum up all components to get the total rate
    total_rate = base_rate + distance_cost + weight_cost

    return total_rate

async def text_message(update, context):
    chat_id = update.effective_chat.id
    if update.message and update.message.text:
        user_message = update.message.text.lower()
    else:
        user_message = update.message.lower()

    # # Check if the message is an MC or DOT number
    # if user_message.isdigit():
    # # Make an API call to verify the MC/DOT number
    #     response = verify_mc_dot(user_message) 
    #     # requests.get("https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{user_message}?webKey={}")
    #     if response['status']== 'verified':
    # # Store the MC/DOT number in the database
    #         db.users.update_one({'chat_id': chat_id}, {'$set': {'mc_dot_number': user_message, 'fmcsa_data': response}}, upsert=True)
    #         # Is your company name {dbaName}? If not, please re-enter your MC/DOT number.
    #         await context.bot.send_message(chat_id=chat_id, text='Your MC/DOT number has been verified. You can now use Hive Bot.')
    #     else:
    #         await context.bot.send_message(chat_id=chat_id, text='Your MC/DOT number could not be verified. Please try again or contact support.')
    #     return
    
    if update.message and update.message.text:
        user_message = update.message.text.lower()
        
        # Example condition to check if the message is about rate calculation or quote request
        if "rate" in user_message:
            # Parse the message for distance, weight, and base rate
            # For simplicity, let's assume the user inputs text in a specific format like 'distance: 100, weight: 2000, base rate: 100'
            # In a real-world scenario, you might want to use more sophisticated parsing or NLP techniques
            distance = None
            shipper_city = None
            shipper_state = None
            consignee_city = None
            consignee_state = None
            weight = None

            for part in user_message.split(','):
                if 'distance:' in part:
                    distance = float(part.split(':')[1].strip())
                elif 'weight:' in part:
                    weight = float(part.split(':')[1].strip())
                elif 'shipper city:' in part:
                    shipper_city = part.split(':')[1].strip()
                elif 'shipper state:' in part:
                    shipper_state = part.split(':')[1].strip()
                elif 'consignee city:' in part:
                    consignee_city = part.split(':')[1].strip()
                elif 'consignee state:' in part:
                    consignee_state = part.split(':')[1].strip()
                    
                    # Check for missing information and prompt the user
                    missing_info = []
                if distance is None:
                    missing_info.append("distance")
                if weight is None:
                    missing_info.append("weight")
                if consignee_city is None:
                    missing_info.append("consignee city")
                if consignee_state is None:
                    missing_info.append("consignee state")
                if shipper_city is None:
                    missing_info.append("shipper city")
                if shipper_state is None:
                    missing_info.append("shipper state")

                if missing_info:
                    response = f"Please provide the following missing information: {', '.join(missing_info)}."
                else:
                    # Calculate the rate
                    rate = calculate_carrier_rate(distance, weight, consignee_city, consignee_state, shipper_city, shipper_state)
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
    # Conversation handler setup
    conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start_command)],
    states={
        NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_number)],
        CONFIRM_COMPANY: [MessageHandler(filters.Regex('^(YES|NO)$'), confirm_company)],
        REENTER_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, reenter_number)],
        # CHOOSING: [MessageHandler(filters.Regex('^(YES|NO)$'), received_number)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

#     conv_handler = ConversationHandler(
#     entry_points=[CommandHandler('start', start_command)],
#     states={
#         CHOOSING: [MessageHandler(filters.Regex('^(MC|DOT)$'), received_number)],
#         TYPING_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_mc_dot)],
#     },
#     fallbacks=[CommandHandler('cancel', cancel)],
# )
    application.add_handler(conv_handler)

    # Adding handlers to the application
    application.add_handler(start_command_handler)
    application.add_handler(text_message_handler)

    # Run the bot and Flask app
    asyncio.get_event_loop().create_task(application.run_polling())

    #  # Run the bot until the user presses Ctrl-C
    application.run_polling()