from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CallbackContext, CommandHandler, ConversationHandler, MessageHandler, filters
from pymongo import MongoClient
import requests
import asyncio
import os
import logging
import json
from openai import OpenAI
from telegram.ext import ConversationHandler
import re

# States definition
START, ENTER_NUMBER, VERIFY_NUMBER, AWAITING_RATE_COMMAND, INITIALIZE_RATE_QUOTE, COLLECTING_RATE_INFO, CALCULATING_RATE_QUOTE = range(7)

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
FMCSA_API_KEY = os.environ['FMCSA_API_KEY']
MONGO_CLIENT = os.environ['MONGO_CLIENT']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
MAX_TOKENS_LIMIT = 350

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB setup
client = MongoClient(MONGO_CLIENT)
db = client['hivedb']
hiveData = db['hive-cx-data']

async def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation and asks for MC/DOT number."""
    await update.message.reply_text(
        "Hi, welcome to our Hive-Bot! Please enter your MC or DOT number to get started.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ENTER_NUMBER

async def enter_number(update: Update, context: CallbackContext) -> int:
    # This function now combines logic for entering and verifying MC/DOT number directly.
    number = update.message.text.strip()
    context.user_data['number'] = number
    response = await verify_number(number)  # Assume this is an asynchronous call to an external verification service
    print(response)
    if response and response['status'] == 'verified':
        # Proceed to confirm company name
        await ask_company_confirmation(update, context, response)
    else:
        # Handle non-verification outcomes
        await handle_verification_failure(update, response)
    return VERIFY_NUMBER

async def ask_company_confirmation(update: Update, context: CallbackContext, response):
    # Logic for confirming company name extracted to a separate function for clarity
    companyName = response['data'].get('carrier', {}).get('legalName') or response['data'].get('carrier', {}).get('dbaName', 'your company')
    reply_keyboard = [['YES', 'NO']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    await update.message.reply_text(f"Is {companyName} your company?", reply_markup=markup)

async def handle_verification_failure(update: Update, response):
    # Logic for handling verification failures extracted for clarity
    if response and response['status'] == 'not_verified':
        message = "Your MC/DOT number could not be verified. Please try again or contact support."
    else:
        message = "I couldn't verify your MC/DOT number. Please ensure it's correct and try again."
    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())

# async def enter_number(update: Update, context: CallbackContext) -> int:
#     number = update.message.text
#     context.user_data['number'] = number

#     # Attempt to verify the MC/DOT number
#     response = await verify_number(number)
#     if response and response['status'] == 'verified':
#         companyName = response['data']['carrier']['legalName'] or response['data']['carrier']['dbaName']
#         reply_keyboard = [['YES', 'NO']]
#         markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
#         await update.message.reply_text(f"Is your company name {companyName}?", reply_markup=markup)
#         return VERIFY_NUMBER
#     elif response and response['status'] == 'ask':
#         companyName = response[0]['legalName'] or response[0]['dbaName']
#         reply_keyboard = [['YES', 'NO']]
#         markup = ReplyKeyboardMarkup(reply_keyboard, input_field_placeholder=f"Is your company name {companyName}?", one_time_keyboard=True)
#         await update.message.reply_text(f"Is your company name {companyName}?", markup)
#         if update.message.text == 'YES':
#             await update.message.reply_text("Your MC/DOT was successfully verified. You can now use Hive Bot.")
#             # Store the MC/DOT and user in the hive database
#             try:  
#                 db.users.update_one({'chat_id': update.effective_chat.id}, {'$set': {'mc_dot_number': number, 'fmcsa_data': response}}, upsert=True)
#             except Exception as e:
#                 logger.error(f"Database error: {e}")
#         else: 
#             await update.message.reply_text("Please re-enter your MC/DOT number.")
#             return ENTER_NUMBER
#     elif response and response['status'] == 'not_verified':
#         await update.message.reply_text("Your MC/DOT number could not be authorized. Please try again or contact support.")
#         return ENTER_NUMBER
#     else:
#         await update.message.reply_text("I couldn't find any MC/DOT info for that number. Please try again or contact support.")
#         return ENTER_NUMBER

async def confirm_company(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text.strip().upper()
    if user_response == 'YES':
        await update.message.reply_text("MC/DOT verified successfully. Send '/rate' to request a rate quote.", reply_markup=ReplyKeyboardRemove())
        return AWAITING_RATE_COMMAND
    else:
        await update.message.reply_text("Please re-enter your MC/DOT number.", reply_markup=ReplyKeyboardRemove())
        return ENTER_NUMBER

# async def confirm_company(update: Update, context: CallbackContext) -> int:
#     user_response = update.message.text
#     if user_response == 'YES':
#         await update.message.reply_text("Your MC/DOT was successfully verified. You can now request a rate quote.", reply_markup=ReplyKeyboardRemove())
#         return AWAITING_RATE_COMMAND  # Transition to a state ready for rate quotes
#     elif user_response == 'NO':
#         await update.message.reply_text("Please re-enter your MC/DOT number.", reply_markup=ReplyKeyboardRemove())
#         return ENTER_NUMBER

# async def reenter_number(update: Update, context: CallbackContext) -> int:
#     number = update.message.text
#     context.user_data['number'] = number

#     response = await verify_number(number)
#     if response and response['status'] in ['verified', 'ask']:
#         # Reuse the code to ask for company confirmation
#         companyName = response.get('data', {}).get('carrier', {}).get('legalName') or \
#                       response.get('data', {}).get('carrier', {}).get('dbaName')
#         reply_keyboard = [['YES', 'NO']]
#         markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
#         await update.message.reply_text(f"Is your company name {companyName}?", reply_markup=markup)
#         return CONFIRM_COMPANY
#     else:
#         # Handle non-verified or error cases
#         await update.message.reply_text("I couldn't find any MC/DOT info for that number. Please try again or contact support.")
#         return ENTER_NUMBER

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

async def verify_mc(user_message, context):
    mc_number = user_message # request.json['mc_dot_number']
    # Make the API call to FMCSA lookup API
    response = requests.get(f"https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{mc_number}?webKey={FMCSA_API_KEY}")
    print(response.json())
    if response.status_code == 200 and response.json()["content"]:
        # Check the conditions
        if response.json()['content'][0]:
            context.user_data['verified'] = True
            return {'status': 'ask', 'message': 'MC/DOT number verified.', 'data': response.json()["content"]}
        else:
            return {'status': 'not_verified', 'message': 'MC info not found. Please re-enter an MC or DOT number.'}

async def rate_quote(update: Update, context: CallbackContext) -> int:
    """Send a message when the command /rate is issued."""
    # Prompt the user for rate quote details
    await context.bot.send_message(
        chat_id= update.effective_chat.id,
        text="Sure let's calculate a rate quote, please provide these details about the load: both the shipper and consignee's zip codes, distance, weight, equipment type, hazmat(yes/no), number of extra stops, and driver assistance (yes/no).",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data['rate_quote_info'] = {}
    return INITIALIZE_RATE_QUOTE


async def collect_rate_info(update: Update, context: CallbackContext) -> int:
    # Collect and process rate information here
    extract_and_calculate_rate_quote(update, context)
    await update.message.reply_text("Calculating your rate based on the provided information...")
    return CALCULATING_RATE_QUOTE

# Mapping of equipment type names to codes
EQUIPMENT_NAME_TO_CODE = {
    'dry van': 'V',
    'van': 'V',
    'reefer': 'R',
    'flatbed': 'F',
    'power only': 'PO',
    'flatbed moffett': 'FM',
    'van moffett': 'VM',
    'reefer moffett': 'RM',
}
# EQUIPMENT_NAME_TO_CODE = {
#     'dry van': 'V',
#     'van': 'V',
#     'reefer': 'R',
#     'flatbed': 'F',
#     'power only': 'PO',
#     'flatbed moffett': 'FM',
#     'flatbed moff': 'FM',
#     'van moffett': 'VM',
#     'van moff': 'VM',
#     'reefer moffett': 'RM',
#     'reefer moff': 'RM'
# }

# Equipment type multipliers
EQUIPMENT_TYPE_MULTIPLIERS = {
    'V': 1, 'PO': 1, 'FO': 0.8, 'R': 1.2, 'VM': 1.7, 'RM': 2.2, 'F': 0.8, 'FM': 1.5
}

async def calculate_approximate_rate_quote(db, load_criteria: dict, update, context):
    try:
        distance_tolerance = 600
        weight_tolerance = 3000
        
        # Convert load criteria values to integers
        shipper_zip = str(load_criteria.get("Shipper zip", ""))
        consignee_zip = int(load_criteria.get("Consignee zip", 00000))
        bill_distance = int(load_criteria.get("Bill Distance", 0))
        weight = int(load_criteria.get("Weight", 0))
        hazmat_routing = load_criteria.get("Hazmat routing", "No")
        # extra_drops = int(load_criteria.get("Extra drops", 0))

        # Convert load criteria values to integers
        load_criteria["Shipper zip"] = str(load_criteria["Shipper zip"])  # Example conversion
        load_criteria["Consignee zip"] = int(load_criteria["Consignee zip"])  # Example conversion
        load_criteria["Bill Distance"] = int(load_criteria["Bill Distance"])  # Example conversion
        load_criteria["Weight"] = int(load_criteria["Weight"])  # Example conversion
        load_criteria["Hazmat routing"] = str(load_criteria["Hazmat routing"])  # Add Hazmat criteria
        # load_criteria["Extra drops"] = int(load_criteria["Extra drops"])  # Example conversion
        print("values pre pipeline --->", load_criteria)
        
        # pipeline = [
        #     {
        #     "$match": {
        #         'Shipper zip': load_criteria.get('Shipper zip', '00000'),
        #         'Consignee zip': load_criteria.get('Consignee zip', 00000),
        #         'Bill Distance': {
        #         '$gte': load_criteria.get('Bill Distance', 0) - distance_tolerance,
        #         '$lte': load_criteria.get('Bill Distance', 0) + distance_tolerance
        #         },
        #         'Weight': {
        #         '$gte': load_criteria.get('Weight', 0) - weight_tolerance,
        #         '$lte': load_criteria.get('Weight', 0) + weight_tolerance
        #         },
        #         # 'Hazmat routing': load_criteria.get('Hazmat routing', 'No'),
        #         'Extra drops': load_criteria.get('Extra drops', 0)
        #     }
        #     },
        #     {
        #     '$group': {
        #         '_id': None,
        #         'averageRate': {'$avg': '$Rate'}
        #     }
        #     }
        # ]
        aggregation_dict = {
                    'Shipper zip': load_criteria["Shipper zip"], 
                    'Bill Distance': {
                        '$gte': load_criteria["Bill Distance"] - distance_tolerance, 
                        '$lte': load_criteria["Bill Distance"] + distance_tolerance
                    }, 
                    'Consignee zip': load_criteria["Consignee zip"], 
                    'Weight': {
                        '$gte': load_criteria["Weight"] - weight_tolerance, 
                        '$lte': load_criteria["Weight"] + weight_tolerance
                    },
                    # "Extra drops": load_criteria["Extra drops"]
                }
        print("aggregation_dict", aggregation_dict)
        
        client = MongoClient('mongodb+srv://Spenceg85:Gooddog400@cluster0.1fybtbs.mongodb.net/')
        cursor = client['hivedb']['hive-cx-data'].aggregate([
            {
                '$match': {
                    'Shipper zip': load_criteria["Shipper zip"], 
                    'Bill Distance': {
                        '$gte': load_criteria["Bill Distance"] - distance_tolerance, 
                        '$lte': load_criteria["Bill Distance"] + distance_tolerance
                    }, 
                    'Consignee zip': load_criteria["Consignee zip"], 
                    'Weight': {
                        '$gte': load_criteria["Weight"] - weight_tolerance, 
                        '$lte': load_criteria["Weight"] + weight_tolerance
                    },
                    # "Extra drops": load_criteria["Extra drops"]
                }
            }, {
                '$group': {
                    '_id': None, 
                    'averageRate': {
                        '$avg': '$Rate'
                    }
                }
            }
        ])
        
        # Execute the aggregation pipeline
        client = db['hive-cx-data']
        result = list(cursor)  # Convert cursor to list
        print("aggy result", result)
        if result and 'averageRate' in result[0]:
            print("aggy result successful", result)
            average_rate = result[0]['averageRate']
            message = f"The estimated rate based on historically similar loads is: ${average_rate:.2f}"
        else:
            # Use the load criteria dictionary
            distance = load_criteria.get("Bill Distance", 0)
            equipment_type_code = load_criteria.get("Equipment Type", 'V')  # Default to 'V'
            
            # Apply the equipment type multiplier
            multiplier = EQUIPMENT_TYPE_MULTIPLIERS.get(equipment_type_code, 1)  # Default multiplier to 1
            
            # If no similar historical data found or specific logic to decide to use base rate calculation:
            base_rate = distance * 1.2 * multiplier
            total_rate = base_rate + (distance * 0.5)  # Fuel surcharge
            
            # also add a hazmat fee if hazmat is true
            if hazmat_routing == 'Yes':
                total_rate += 200
            
            # Also add a driver assistance fee if driver assistance is true
            if load_criteria.get("Driver assistance", 'No') == 'Yes':
                total_rate += 100
                
            # # Also add a toll fee if tolls are true
            # if load_criteria.get("Tolls", 'No') == 'Yes':
            #     total_rate += 50
            
            message = f"Based on my analysis and calculations of the information provided, the estimated rate is: ${total_rate:.2f}"
    except Exception as e:
        message = f"Sorry, I couldn't process that rate due to an error: {e}"

    return message

            
        # aggregation = hiveData.aggregate(pipeline)
        # result = list(aggregation)
    #     print("result", result)
    #     if result and 'averageRate' in result[0]:
    #         average_similar_rate = result[0]['averageRate']
    #         message = f"The estimated rate is: ${average_similar_rate:.2f}"
    #         return message
    #     else:
    #         return "No similar historical data found to calculate an approximate rate."
    # except Exception as e:
    #     return f"Sorry, I couldn't process that due to an error: {e}"

    
async def extract_initial_load_criteria(update, context):
    user_message = update.message.text.lower()

    # Default values
    load_criteria = {
        'Driver assistance': 'No',
        'Equipment type': 'V',
        'Hazmat routing': 'No'  # Set default value to 'No'
    }

    # Extract information with improved regex patterns
    regex_patterns = {
        'Shipper zip': r"\b(?:from\szip\scode|from\szip|shipper'?s?\szip)\s*(\d{5})",
        'Consignee zip': r"\b(?:to\szip\scode|to\szip|consignee'?s?\szip)\s*(\d{5})",
        'Bill Distance': r"\b(\d+)\s*miles", 
        'Weight': r"\b(\d+)\s*lbs",
        'Equipment type': r"(?i)\b(dry van|van|reefer|flatbed|power only|flatbed moffett|van moffett|reefer moffett)\b",
        'Hazmat routing': r"(?i)\b(hazmat|no hazmat)\b",
        'Driver assistance': r"(?i)\b(driver assist|no driver assist)\b"
    }

    for key, pattern in regex_patterns.items():
        match = re.search(pattern, user_message)
        if match:
            load_criteria[key] = int(match.group(1)) if key in ['Bill Distance', 'Weight'] else match.group(1)

    # Extract and map equipment type from user message
    for keyword, code in EQUIPMENT_NAME_TO_CODE.items():
        if keyword in user_message:
            load_criteria['Equipment type'] = code
            break

    # Determine driver assistance requirement
    if 'no driver assist' in user_message:
        load_criteria['Driver assistance'] = 'No'
    elif 'driver assist' in user_message:
        load_criteria['Driver assistance'] = 'Yes'

    # Determine hazmat routing
    if 'hazmat' in user_message:
        load_criteria['Hazmat routing'] = 'Yes'
    elif 'no hazmat' in user_message:
        load_criteria['Hazmat routing'] = 'No'

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"I understand your load criteria is: {load_criteria}, please wait while I run some advanced calculations and analysis..."
    )

    return load_criteria

async def ask_for_clarification(chat_id, prompt, context):
    # Use OpenAI API to ask the user for clarification
    await context.bot.send_message(chat_id=chat_id, text=prompt)
    # Here, you would need to handle user response capture. This could be done through a follow-up handler that waits for the next user message.
    
    # Placeholder for user response handling
    user_response = "user response here"
    return user_response

async def extract_and_calculate_rate_quote(update, context):
    user_message = update.message.text.strip()
    chat_id = update.effective_chat.id

    # Initial Extraction with Regex
    load_criteria = await extract_initial_load_criteria(update, context)
    # Check for missing or unclear information
    missing_fields = await check_missing_or_unclear_fields(load_criteria, update)

    # Conversational Clarification with OpenAI API
    if missing_fields:
        # Your logic to request more info for missing fields
        if 'rate_quote' not in context.user_data:
            await ask_for_clarification(chat_id, "Please provide more details.", context)
            context.user_data['rate_quote'] = True
            return INITIALIZE_RATE_QUOTE

    # Aggregation and Calculation
    rate_quote = await calculate_approximate_rate_quote(db, load_criteria, update, context)

    # Send the calculated rate quote to the user
    await context.bot.send_message(chat_id=chat_id, text=f"The estimated rate is: ${rate_quote}")

    # Prompt for feedback or next action
    await context.bot.send_message(chat_id=chat_id, text="Please provide your feedback on the quote or let me know if you want to request another quote or switch to conversational mode.")

    return ConversationHandler.END

async def check_missing_or_unclear_fields(load_criteria, update):
    # Identify fields that are missing or need clarification
    missing_fields = [field for field, value in load_criteria.items() if value is None]
    if missing_fields:
        message = "The following fields are missing or need clarification:\n"
        for field in missing_fields:
            message += f"{field}: \n"
        message += "Please re-enter only the missing fields, for example: 'distance: 280 miles.'"
        # Send the message to the user
        await update.message.reply_text(message)
    return missing_fields

async def collect_rate_info(update: Update, context: CallbackContext) -> int:
    user_message = update.message.text.strip()

    # Correctly extract load criteria from the user message
    load_criteria = await extract_initial_load_criteria(update, context)
    
    # Calculate and return the rate quote based on the extracted criteria
    rate_quote_message = await calculate_approximate_rate_quote(db, load_criteria, update, context)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=rate_quote_message)
    return ConversationHandler.END


async def calculate_rate_quote(update: Update, context: CallbackContext) -> int:
    # Perform rate calculation here
    # Placeholder implementation
    await update.message.reply_text("Based on the information provided, your estimated rate is: $XXX.XX")
    return ConversationHandler.END

# Error handler
def error_handler(update: Update, context: CallbackContext):
    logger.warning(f'Update "{update}" caused error "{context.error}"')


async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    application = Application.builder().token(os.environ["TELEGRAM_API_KEY"]).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ENTER_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_number)],
            VERIFY_NUMBER: [MessageHandler(filters.TEXT, confirm_company)],
            AWAITING_RATE_COMMAND: [CommandHandler('rate', rate_quote)],
            INITIALIZE_RATE_QUOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_rate_info)],
            CALCULATING_RATE_QUOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate_rate_quote)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    # Start the Bot
    asyncio.run(application.run_polling())

if __name__ == '__main__':
    asyncio.run(main())
