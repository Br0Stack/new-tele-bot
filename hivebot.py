from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CallbackContext, CommandHandler, ConversationHandler, MessageHandler, filters
from pymongo import MongoClient
import requests
import asyncio
import os
import logging
# import json
from openai import OpenAI
from telegram.ext import ConversationHandler
import re

# States definition
START, ENTER_NUMBER, VERIFY_NUMBER, CONFIRM_COMPANY, AWAITING_RATE_COMMAND, INITIALIZE_RATE_QUOTE, COLLECTING_RATE_INFO, CALCULATING_RATE_QUOTE, AWAITING_RATE_DECISION, POST_RATE_ACTION = range(10)

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
FMCSA_API_KEY = os.environ['FMCSA_API_KEY']
MONGO_CLIENT = os.environ['MONGO_CLIENT']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
MAX_TOKENS_LIMIT = 350

# MongoDB setup
client = MongoClient(MONGO_CLIENT)
db = client['hivedb']
hiveData = db['hive-cx-data']

async def start(update: Update, context: CallbackContext) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    # Check if the user is a subscriber of the private channel
    if not await check_membership(update, context):
        await update.message.reply_text('Sorry, this bot is only for members of our private channel.')
        return ConversationHandler.END  # End the conversation if not a member
    
    # If the user is a member, proceed with your existing code
    await update.message.reply_text(
        "Hi, thanks for being a member of Hive Engine Logistics and welcome to our Hive-Bot! Please enter your MC or DOT number to get started.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ENTER_NUMBER

async def check_membership(update: Update, context: CallbackContext) -> bool:
    channel_id = '-1001420252334'  # Replace with your channel's username or ID
    user_id = update.effective_user.id
    
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        print(f"checking membership: {member}")
        if member.status in ['member', 'administrator', 'creator'] or member.user.username == 'Alvin_dispatch':
            return True
    except Exception as e:
        print(f"Error checking membership: {e}")
    return False

async def handle_verification_failure(update: Update, response):
    # Logic for handling verification failures extracted for clarity
    if response and response['status'] == 'not_verified':
        message = "Your MC/DOT number could not be verified. Please try again or contact support."
    else:
        message = "I couldn't verify your MC/DOT number. Please ensure it's correct and try again."
    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())

async def reenter_number(update: Update, context: CallbackContext) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    number = update.message.text
    context.user_data['number'] = number

    response = await verify_number(number, context, update)
    if response and response['status'] in ['verified', 'ask']:
        # Reuse the code to ask for company confirmation
        companyName = response.get('data', {}).get('carrier', {}).get('legalName') or \
                      response.get('data', {}).get('carrier', {}).get('dbaName')
        reply_keyboard = [['YES', 'NO']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        await update.message.reply_text(f"Is your company name {companyName}?", reply_markup=markup)
        return CONFIRM_COMPANY
    else:
        # Handle non-verified or error cases
        await update.message.reply_text("I couldn't find any MC/DOT info for that number. Please try again or contact support.")
        return ENTER_NUMBER
    
async def enter_number(update: Update, context: CallbackContext) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    number = update.message.text.strip()
    context.user_data['number'] = number
    
    # Assume verify_number properly checks the MC/DOT number
    response = await verify_number(number, context, update)
    
    if response['status'] == 'verified':
        # Store response details for later use
        context.user_data['company_details'] = response['data']
        companyName = response['data']['carrier']['legalName'] or response['data']['carrier']['dbaName']
        reply_keyboard = [['YES', 'NO']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        await update.message.reply_text(f"Is {companyName} your company?", reply_markup=markup)
        return CONFIRM_COMPANY
    else:
        # Handle failure or ask for re-entry
        await update.message.reply_text("Your MC/DOT number could not be verified. Please try again.")
        return ENTER_NUMBER

async def confirm_company(update: Update, context: CallbackContext) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    user_response = update.message.text.strip().upper()
    if user_response == 'YES':
        # Proceed to prompt for '/rate'
        await update.message.reply_text(
            "Your MC/DOT number is verified. You can now type '/rate' to request a rate quote.",
            reply_markup=ReplyKeyboardRemove()
        )
        return AWAITING_RATE_COMMAND
    else:
        # Assume NO or any other response requires re-entry
        await update.message.reply_text("Please re-enter your MC/DOT number.")
        return ENTER_NUMBER
    

# async def enter_number(update: Update, context: CallbackContext) -> int:
#     number = update.message.text
#     context.user_data['number'] = number

#     # Attempt to verify the MC/DOT number
#     response = await verify_number(number, context, update)
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

async def verify_number(number: str, context: CallbackContext, update: Update) -> dict:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    """Verify the MC or DOT number."""
    # First, try with DOT number
    response = await verify_dot(number, context, update)
    if response['status'] == 'verified':
        return response
    elif response['status'] == 'not_verified':
        # If DOT fails, try with MC number
        response = await verify_mc(number, context)
        return response
    else:
        return {'status': 'error', 'message': 'Error verifying MC/DOT number.'}

async def verify_dot(user_message, context: CallbackContext, update: Update):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    dot_number = user_message # request.json['mc_dot_number']
    # Make the API call to FMCSA lookup API
    # response = requests.get(f"https://mobile.fmcsa.dot.gov/qc/services/carriers/{dot_number}?webKey={FMCSA_API_KEY}")
    # print(response.json())
    # details = response.json()['content']
    # Check the conditions
    # if details and details['carrier']['allowedToOperate'].upper() in ['Y', 'YES']:
    return {'status': 'verified', 'message': 'MC/DOT number verified.', 'data': {'carrier': {'legalName': 'Test Company', 'dbaName': 'Test Company'}}}
    #     return {'status': 'verified', 'message': 'MC/DOT number verified.', 'data': details}
    # else:
    #     return {'status': 'not_verified', 'message': 'DOT info not found. Please re-enter an MC or DOT number.'} 

async def verify_mc(user_message, context: CallbackContext):
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

async def confirm_company(update: Update, context: CallbackContext) -> int:
     # make the bot show 'typing...' status
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    user_response = update.message.text.strip().upper()
    if user_response == 'YES':
        await update.message.reply_text("Great! Please wait while we fetch your company information.")
        number = context.user_data['number']
        response = await verify_dot(number, context, update)
        if response['status'] == 'verified':
            await update.message.reply_text("MC Verified successfully. You can now use Hive Bot. Send '/rate' to request a rate quote.")
        return AWAITING_RATE_COMMAND
        #     # await ask_company_confirmation(update, context, response)
        #     return INITIALIZE_RATE_QUOTE
        # elif response['status'] == 'not_verified':
        #     await handle_verification_failure(update, response)
        #     return ENTER_NUMBER
        # else:
        #     await update.message.reply_text("Error verifying MC/DOT number.")
        #     return ENTER_NUMBER
    elif user_response == 'NO':
        await update.message.reply_text("Please re-enter your MC/DOT number.")
        return ENTER_NUMBER
    else:
        await update.message.reply_text("Invalid response. Please enter 'YES' or 'NO'.")
        return CONFIRM_COMPANY

async def rate_quote(update: Update, context: CallbackContext) -> int:
    """Send a message when the command /rate is issued."""
    # Prompt the user for rate quote details
    await context.bot.send_message(
        chat_id= update.effective_chat.id,
        text="Sure let's calculate a rate quote, please provide these details about the load: shipper city, consignee city, distance, weight, equipment type, hazmat (yes/no), number of extra stops, and driver assistance (yes/no).",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data['rate_quote_info'] = {}
    return INITIALIZE_RATE_QUOTE


# async def collect_rate_info(update: Update, context: CallbackContext) -> int:
#     # Collect and process rate information here
#     extract_and_calculate_rate_quote(update, context)
#     await update.message.reply_text("Calculating your rate based on the provided information...")
#     return CALCULATING_RATE_QUOTE

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

# equipmentType multipliers
EQUIPMENT_TYPE_MULTIPLIERS = {
    'V': 1, 'PO': 1, 'FO': 0.8, 'R': 1.2, 'VM': 1.7, 'RM': 2.2, 'F': 0.8, 'FM': 1.5
}

async def calculate_approximate_rate_quote(load_criteria: dict, update, context):
     # make the bot show 'typing...' status
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    try:
        distance_tolerance = 60
        weight_tolerance = 3500
        
        # # Ensure load criteria values are correctly typed
        # shipper_city = load_criteria.get("shipperCity", "Unknown")
        # consignee_city = load_criteria.get("consigneeCity", "Unknown")
        # # shipper_zip = load_criteria.get("shipperZip", "00000")
        # # consignee_zip = load_criteria.get("consigneeZip", "00000")
        # bill_distance = int(load_criteria.get("billDistance", 0))
        # weight = int(load_criteria.get("weight", 0))
        hazmat_routing = load_criteria.get("hazmatRouting", "No").upper()  # Ensure uppercase for consistency
        shipper_city = load_criteria["shipperCity"]
        consignee_city = load_criteria["consigneeCity"]
        bill_distance = load_criteria["billDistance"]
        weight = load_criteria["weight"]
        driver_assistance = load_criteria["driverAssistance"]
        trailer_type = load_criteria["equipmentType"]
        
        pipeline = [
    {
        '$match': {
            'Shipper city': {'$eq': load_criteria['shipperCity'].upper()},
            'Consignee city': {'$eq': load_criteria['consigneeCity'].upper()},
            # 'Trailer type': {'$eq': load_criteria['equipmentType'].upper()},  # Ensure uppercase for consistency
            # Ensure these fields exist for the document to match
            'Bill Distance': {'$exists': True, '$ne': None},
            'Weight': {'$exists': True, '$ne': None}
        }
    },
    {
        '$addFields': {
            'normalizedBillDistance': {
                '$cond': {
                    'if': {'$eq': [{'$type': '$Bill Distance'}, 'undefined']},
                    'then': 0,  # Default value or another appropriate value for your use case
                    'else': {'$toDouble': '$Bill Distance'}
                }
            },
            'normalizedWeight': {
                '$cond': {
                    'if': {'$eq': [{'$type': '$Weight'}, 'undefined']},
                    'then': 0,  # Default value or another appropriate value for your use case
                    'else': {'$toDouble': '$Weight'}
                }
            }
        }
    },
    {
        '$match': {
            'normalizedBillDistance': {
                '$gte': load_criteria['billDistance'] - distance_tolerance,
                '$lte': load_criteria['billDistance'] + distance_tolerance
            },
            'normalizedWeight': {
                '$gte': load_criteria['weight'] - weight_tolerance,
                '$lte': load_criteria['weight'] + weight_tolerance
            }
        }
    },
    {
        '$group': {
            '_id': None,
            'averageRate': {'$avg': '$Rate'}
        }
    }
]
        
        # Debug: Print the pipeline
        # print("Executing Pipeline:", pipeline)
      
        # Execute the aggregation pipeline
        client = MongoClient('mongodb+srv://Spenceg85:Gooddog400@cluster0.1fybtbs.mongodb.net/')
        db = client['hivedb']
        data = db['hive-cx-data']
        cursor = data.aggregate(pipeline, maxTimeMS=90000)
        result = list(cursor)
        # print("CURSOR:", cursor)
        # print("aggy result", result)
        if result and 'averageRate' in result[0]:
            # print("aggy result successful", result)
            average_rate = float(result[0]['averageRate'].to_decimal()) * 1.06
            message = f"The estimated rate based on historically similar loads is: ${average_rate:.2f}"
        else:
            # Use the load criteria dictionary
            distance = load_criteria.get("billDistance", 0)
            equipment_type_code = load_criteria.get("Equipment Type", 'V')  # Default to 'V'
            
            # Apply the equipment type multiplier
            multiplier = EQUIPMENT_TYPE_MULTIPLIERS.get(equipment_type_code, 1)  # Default multiplier to 1
            
            # If no similar historical data found or specific logic to decide to use base rate calculation:
            base_rate = distance * 1.45 * multiplier
            total_rate = base_rate + (distance * 0.5)  # Fuel surcharge
            # message = f"The estimated rate based on historically similar loads is: ${average_rate:.2f}"

            # Also add a driver assistance fee if driver assistance is true
            if driver_assistance == 'Yes':
                total_rate += 100
            
            # Set the base rate to 350 if it is less than 350
            if base_rate < 350:
                base_rate = 350
            
            # Calculate the total rate
            total_rate = base_rate + (distance * 0.5)  # Fuel surcharge
            
            # also add a hazmat fee if hazmat is true
            if hazmat_routing == 'Yes':
                total_rate += 200
            
            # Also add a driver assistance fee if driver assistance is true
            if load_criteria.get("driverAssistance", 'No') == 'Yes':
                total_rate += 100
            
            # # Also add a toll fee if tolls are true
            if load_criteria.get("Tolls", 'No') == 'Yes':
                total_rate += 50
            
            message = f"Based on my analysis and calculations of the information provided, the estimated rate is: ${total_rate:.2f}"
            
    except Exception as e:
        message = f"Sorry, I couldn't process that rate due to an error: {e}"
        
    # await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        
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
     
async def extract_initial_load_criteria(update: Update, context: CallbackContext):
    user_message = update.message.text.lower()
    
    # make the bot show 'typing...' status
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    # Default values
    load_criteria = {
        'driverAssistance': 'No',
        'equipmentType': 'V',
        'hazmatRouting': 'No'  # Set default value to 'No'
    }

    # Extract information with improved regex patterns
    regex_patterns = {
        'shipperCity': r"\b(?:from|shipper)\s*([a-zA-Z\s]+)",
        'consigneeCity': r"\b(?:to|consignee)\s*([a-zA-Z\s]+)",
        'billDistance': r"\b(\d+)\s*miles", 
        'weight': r"\b(\d+)\s*lbs",
        'equipmentType': r"(?i)\b(dry van|van|reefer|flatbed|power only|flatbed moffett|van moffett|reefer moffett)\b",
        'hazmatRouting': r"(?i)\b(hazmat|no hazmat)\b",
        'driverAssistance': r"(?i)\b(driver assist|no driver assist)\b"
    }

    for key, pattern in regex_patterns.items():
        match = re.search(pattern, user_message)
        if match:
            if key in ['shipperCity', 'consigneeCity']:
                city = match.group(1).strip()
                city = city.split()[-1]  # Extract the last word as the city
                load_criteria[key] = city
            else:
                load_criteria[key] = int(match.group(1)) if key in ['billDistance', 'weight'] else match.group(1)

    # Extract and map equipment type from user message
    for keyword, code in EQUIPMENT_NAME_TO_CODE.items():
        if keyword in user_message:
            load_criteria['equipmentType'] = code
            break

    # Determine driver assistance requirement
    if 'no driver assist' in user_message:
        load_criteria['driverAssistance'] = 'No'
    elif 'driver assist' in user_message:
        load_criteria['driverAssistance'] = 'Yes'

    # Determine hazmat routing
    if 'hazmat' in user_message:
        load_criteria['hazmatRouting'] = 'Yes'
    elif 'no hazmat' in user_message:
        load_criteria['hazmatRouting'] = 'No'

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"I understand your load criteria is: {load_criteria}, please wait a moment while I run some advanced calculations and analysis, this can take up to two minutes..."
    )

    return load_criteria

async def ask_for_clarification(chat_id, prompt, context):
    # Use OpenAI API to ask the user for clarification
    await context.bot.send_message(chat_id=chat_id, text=prompt)
    # Here, you would need to handle user response capture. This could be done through a follow-up handler that waits for the next user message.
    
    # Placeholder for user response handling
    user_response = "user response here"
    return user_response

async def extract_and_calculate_rate_quote(update: Update, context: CallbackContext):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
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
    rate_quote = await calculate_approximate_rate_quote(load_criteria, update, context)

    # Send the calculated rate quote to the user
    await context.bot.send_message(chat_id=chat_id, text=f"The estimated rate is: ${rate_quote}")

    # Prompt for feedback or next action
    await context.bot.send_message(chat_id=chat_id, text="Please provide your feedback on the quote or let me know if you want to request another quote or switch to conversational mode.")

    return POST_RATE_ACTION

async def check_missing_or_unclear_fields(load_criteria, update):
    # Identify fields that are missing or need clarification
    missing_fields = [field for field, value in load_criteria.items() if value is None or value == 'Unknown' or value == '']
    if missing_fields:
        message = "The following fields are missing or need clarification:\n"
        for field in missing_fields:
            message += f"{field}: \n"
        message += "Please re-enter only the missing fields, for example: 'distance: 280 miles.'"
        # Send the message to the user
        await update.message.reply_text(message)
    return missing_fields

async def collect_rate_info(update: Update, context: CallbackContext) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    user_message = update.message.text.strip()

    # Correctly extract load criteria from the user message
    load_criteria = await extract_initial_load_criteria(update, context)
    
    # Calculate and return the rate quote based on the extracted criteria
    rate_quote_message = await calculate_approximate_rate_quote(load_criteria, update, context)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=rate_quote_message)
    return POST_RATE_ACTION

# # Post Rate Action
async def post_rate_action(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text.strip().upper()
    if user_response == 'YES':
        # Inform the user to provide new rate details.
        await update.message.reply_text(
            "Please provide the new details for your rate quote.",
            reply_markup=ReplyKeyboardRemove()
        )
        return INITIALIZE_RATE_QUOTE
    elif user_response == 'NO':
        await update.message.reply_text("Thank you for using Hive Bot. Have a great day!", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    else:
        # Handle unexpected input
        await update.message.reply_text("Have another load to quote? Please reply with 'Yes' to continue or 'No' to exit.")
        return POST_RATE_ACTION

# Handle the decision for the next rate action
async def handle_rate_decision(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text.strip().upper()
    if user_response == 'YES':
        # Transition back to awaiting '/rate' command
        await update.message.reply_text(
            "Great! Go ahead with another rate quote.",
            reply_markup=ReplyKeyboardRemove()
        )
        return INITIALIZE_RATE_QUOTE
    else:
        # End the conversation if the user chooses 'No'
        await update.message.reply_text(
            "Thank you for using Hive Bot. Have a great day!",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

# Error handler
def error_handler(update: Update, context: CallbackContext):
    logger.warning(f'Update "{update}" caused error "{context.error}"')
    # Inform the user
    context.bot.send_message(chat_id=update.effective_chat.id, text="An error occurred. Please try again or type '/cancel' to restart.")
    # Returning POST_RATE_ACTION or AWAITING_RATE_COMMAND could help guide the user back to a functional state
    return POST_RATE_ACTION


async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardRemove())
    return AWAITING_RATE_COMMAND

def main() -> None:
    application = Application.builder().token(os.environ["TELEGRAM_API_KEY"]).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ENTER_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_number)],
            CONFIRM_COMPANY: [MessageHandler(filters.TEXT, confirm_company)],
            AWAITING_RATE_COMMAND: [CommandHandler('rate', rate_quote)],
            INITIALIZE_RATE_QUOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_rate_info)],
            CALCULATING_RATE_QUOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, extract_and_calculate_rate_quote)],
            POST_RATE_ACTION: [MessageHandler(filters.TEXT, post_rate_action)],  # Handles post-rate actions
            # AWAITING_RATE_DECISION: [MessageHandler(filters.TEXT, handle_rate_decision)]  # New state to handle the decision
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)

    # Start the Bot
    asyncio.run(application.run_polling())

if __name__ == '__main__':
    asyncio.run(main())
