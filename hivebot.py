from telegram import ForceReply, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, ContextTypes, CommandHandler, ConversationHandler, MessageHandler, filters
import os
import requests
import logging
from pymongo import MongoClient
import asyncio
import re
from openai import OpenAI
import json

FMCSA_API_KEY = os.environ['FMCSA_API_KEY']  # FMCSA webKey
MONGO_CLIENT = os.environ['MONGO_CLIENT']  # MongoDB connection string
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']  # OpenAI API key
MAX_TOKENS_LIMIT = 280  # Max tokens limit for GPT-4

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
gpt_client = OpenAI()
user_conversations = {}  # A dictionary to store conversation history for each user

# Define states for the conversation
# CHOOSING, TYPING_REPLY = range(2)
NUMBER, VERIFY, CONFIRM_COMPANY, REENTER_NUMBER = range(4)
GENERAL = 5

def update_conversation_history(user_id, user_message, bot_response):
    conversation = {
        "user_id": user_id,
        "messages": [{"role": "user", "content": user_message},
                     {"role": "assistant", "content": bot_response}]
    }
    db.conversations.update_one(
        {"user_id": user_id},
        {"$push": {"messages": {"$each": conversation["messages"]}}},
        upsert=True
    )


def get_conversation_history(user_id):
    try:
        conversation_record = db.conversations.find_one({"user_id": user_id})
        return conversation_record["messages"] if conversation_record else []
    except Exception as e:
        logger.error(f"Error fetching conversation history: {e}")
        return []


async def chat_with_gpt(user_id, user_message, task="conversation"):
    history = get_conversation_history(user_id)
    history.append({"role": "user", "content": user_message})

    # Convert each message content to string and then join
    content_history = " ".join([msg.get('content', '') for msg in history])

    # Truncate history if it's too long
    while len(content_history) > MAX_TOKENS_LIMIT:
        history.pop(0)
        content_history = " ".join([msg.get('content', '') for msg in history])

    try:
        response = gpt_client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=history,
            max_tokens=200,
            stop=None if task == "conversation" else ["\n"]  # Adjust stopping condition based on the task
        )

        # Extract the text response and update history
        gpt_response = response.choices[0].message.content if response.choices else ""
        
        # Update conversation history for general conversation
        if task == "conversation":
            update_conversation_history(user_id, user_message, gpt_response)

        return gpt_response
    except Exception as e:
        logger.error(f"Error in chat_with_gpt: {e}")
        return "I'm having trouble understanding that. Could you rephrase or ask something else?"


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
        await update.message.reply_text("Your MC/DOT was successfully verified. You can now use Hive Bot.", reply_markup=ReplyKeyboardRemove())
        return GENERAL  # Transition to GENERAL state
    elif user_response == 'NO':
        await update.message.reply_text("Please re-enter your MC/DOT number.", reply_markup=ReplyKeyboardRemove())
        return NUMBER

async def reenter_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    number = update.message.text
    context.user_data['number'] = number

    response = await verify_number(number)
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
        return NUMBER  # Loop back to NUMBER state

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

rate_quote_tool = {
    "type": "function",
    "function": {
        "name": "calculate_dynamic_rate_quote",
        "description": "Calculate dynamic rate quote for carriers based on input criteria",
        "parameters": {
            "type": "object",
            "properties": {
                "distance": {"type": "number"},
                "weight": {"type": "number"},
                "shipperCity": {"type": "string"},
                "shipperState": {"type": "string"},
                "consigneeCity": {"type": "string"},
                "consigneeState": {"type": "string"},
                "equipmentType": {"type": "string"},
                "hazmat": {"type": "boolean"},
            },
            "required": ["distance", "weight", "shipperCity", "shipperState", "consigneeCity", "consigneeState", "equipmentType", "hazmat"]
        }
    }
}


def calculate_rate_with_gpt(user_message: str, user_id: str):
    try:
        print(f"User ID: {user_id}, User Message: {user_message}")
        # Fetch and filter the conversation history
        history = get_conversation_history(user_id)
        valid_history = [msg for msg in history if isinstance(msg.get('content'), str) and msg['content']]

        # Append the current user message to the valid history
        valid_history.append({"role": "user", "content": user_message})
        print("Valid history being sent to GPT-4:", valid_history)

        # Send the filtered history to GPT-4
        completion = gpt_client.chat.completions.create(
            model="gpt-4-0613",
            messages=valid_history,
            tools=[rate_quote_function],
            tool_choice="auto"
        )
        print("Completion object from GPT-4:", completion)
        
    # Check if rate calculation is needed
        if "calculate_dynamic_rate_quote" in gpt_response:
            # Extract necessary data for rate calculation from user_message or history
            # For example:
            # distance = 1800  # Extract from user_message or history
            # weight = 20000  # Extract from user_message or history
            # base_rate = 100  # This could be a default or calculated value
            # Modify these values as needed

            # Calculate rate
            rate = calculate_carrier_rate(distance, weight, consignee_city, consignee_state, shipper_city, shipper_state)

            # Construct a response with the calculated rate
            gpt_response = f"The estimated rate is: ${rate:.2f}"
        
        if completion.choices and len(completion.choices) > 0:
            gpt_response = completion.choices[0].message.content
            update_conversation_history(user_id, user_message, gpt_response)
            return gpt_response
        else:
            logger.error(f"No response from GPT-4 for rate quote calculation. Completion object: {completion}")
            return "GPT-4 did not provide a response."

    except Exception as e:
        logger.error(f"Error in calculate_rate_with_gpt: {e}")
        return f"Sorry, I couldn't process that due to an error: {e}"

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
# def calculate_carrier_rate(load):
#     start_date = load["start_date"]
#     end_date = load["end_date"]
    
#     # Example aggregation pipeline to calculate the rate
#     pipeline = [
#     # Match stage to filter data (if needed, based on some criteria)
#     {
#         "$match": {
#             "date": {"$gte": start_date, "$lte": end_date}  # Example date range
#         }
#     },
#     # Group by relevant fields
#     {
#         "$group": {
#             "_id": {
#                 "shipperCity": "$Shipper city",
#                 "shipperState": "$Shipper state",
#                 "consigneeCity": "$Consignee city",
#                 "consigneeState": "$Consignee state",
#                 "trailerType": "$Trailer type"
#             },
#             "averageRate": {"$avg": "$Total charges from the customer"},
#             "averageWeight": {"$avg": "$Weight"},
#             # Add more averages or sums as needed
#         }
#     },
#     # Sort by some field if needed
#     {
#         "$sort": {"_id": 1}
#     }
# ]
#     # Include the rate calculation logic here
#     # You can fetch data from your MongoDB and apply the formula
#     historic_rate_aggregated = db.hive_cx_data.aggregate(pipeline)
#     # Return a string with the calculated rate or related information
#     return historic_rate_aggregated

def calculate_carrier_rate(load_type, equipment_type, distance, weight, volume_ft3=None, hazmat=False, extra_stops=0, driver_assist=False, storage_days=0, toll_charges=0):
    # Constants
    base_rate_per_mile = 1.2
    fuel_surcharge_per_mile = 0.5  # Example value, adjust as needed

    # Equipment type multiplier
    equipment_multiplier = {
        "V": 1,
        "PO": 1,
        "FO": 0.8,
        "R": 1.2,
        "VM": 1.7,
        "RM": 2.2,
        "F": 0.8
    }

    # Calculate base rate
    base_rate = distance * base_rate_per_mile * equipment_multiplier.get(equipment_type, 1)

    # Add fuel surcharge
    total_rate = base_rate + (distance * fuel_surcharge_per_mile)

    # Additional charges
    if driver_assist:
        driver_assist_fee = 150 if load_type == "FTL" else 100
        total_rate += driver_assist_fee

    if hazmat:
        hazmat_fee = 500 if load_type == "FTL" else 300
        total_rate += hazmat_fee

    # Extra stops charge
    extra_stop_fee = 75 * extra_stops
    total_rate += extra_stop_fee

    # LTL specific charges
    if load_type == "LTL":
        weight_charge = weight * 0.3
        volume_charge = volume_ft3 * 10 if volume_ft3 else 0
        total_rate += weight_charge + volume_charge

    # Storage fees and toll charges
    storage_fee = 200 * storage_days
    total_rate += storage_fee + toll_charges

    return total_rate

# def calculate_carrier_rate(distance, weight, equipmentType, shipperCity, shipperState, consigneeCity, consigneeState, length_ft=None, trailer_type=None, hazmat=False, number_of_stops=1, driver_type='solo', driver_assistance=False, storage_days=0, toll_charges=0):
    # Constants for rate calculation (customize these as needed)
    base_rate_per_mile = 1.5  # Base rate per mile
    weight_rate_per_pound = 0.05  # Rate per pound

    # Adjustments based on trailer type and other factors
    trailer_type_modifier = {
        "R": 1.1,  # Reefer
        "": 1.0,  # Dry van
        "F": 1.05,  # Flatbed
        "S": 1.15,  # Step deck
        "DD": 1.2,  # Double drop
        "LB": 1.25,  # Lowboy
        "A": 1.3,  # Auto carrier
        "T": 1.35,  # Tanker
        "D": 1.4,  # Dump
        "H": 1.45,  # Hot shot
        "AH": 1.5,  # Auto hauler
        "HZ": 1.55,  # Hazmat
        "P": 1.6,  # Power only
    }
        # Add other trailer types and their modifiers here
    #         if equipmentType == "flatbed":
    #     equip_type_modifier = 1.05
    # elif equipmentType == "reefer":
    #     equip_type_modifier = 1.1
    # elif equipmentType == "van":
    #     equip_type_modifier = 1.15
    # elif equipmentType == "power only":
    #     equip_type_modifier = 1.2
    # elif equipmentType == "step deck":
    #     equip_type_modifier = 1.25
    # elif equipmentType == "double drop":
    #     equip_type_modifier = 1.3
    # elif equipmentType == "lowboy":
    #     equip_type_modifier = 1.35
    # elif equipmentType == "auto carrier":
    #     equip_type_modifier = 1.4
    # elif equipmentType == "tanker":
    #     equip_type_modifier = 1.45
    # elif equipmentType == "dump":
    #     equip_type_modifier = 1.5
    # elif equipmentType == "hot shot":
    #     equip_type_modifier = 1.55
    # elif equipmentType == "auto hauler":
    #     equip_type_modifier = 1.6
    # elif equipmentType == "hazmat":
    #     equip_type_modifier = 1.65

    hazmat_modifier = 1.2 if hazmat else 1.0
    driver_assistance_fee = 150 if driver_assistance else 0
    stop_fee = 75 * (number_of_stops - 1)  # Additional $75 per extra stop
    storage_fee = 200 * storage_days  # $200 per day for storage
    driver_type_modifier = 1.1 if driver_type == 'team' else 1.0

    # Calculate the distance, weight, and trailer type components of the rate
    distance_cost = distance * base_rate_per_mile
    weight_cost = weight * weight_rate_per_pound
    equipment_modifier = trailer_type_modifier.get(trailer_type, 1.0)

    # Sum up all components to get the total rate
    total_rate = (distance_cost + weight_cost) * equipment_modifier * hazmat_modifier * driver_type_modifier
    total_rate += driver_assistance_fee + stop_fee + storage_fee + toll_charges

    # Ensure the rate is positive
    return max(total_rate, 0)

def next_key_to_collect(rate_info):
    required_keys = ["distance", "weight", "equipmentType", "shipperCity", "shipperState", "consigneeCity", "consigneeState"]
    for key in required_keys:
        if key not in rate_info:
            return key
    return None

async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_message = update.message.text.lower() if update.message and update.message.text else ''

    # If the message is too general, ask for more details
    if user_message.strip() in ["rate", "rate quote"]:
        await context.bot.send_message(chat_id=chat_id, text="Could you provide more details for the rate quote, such as shipper city, state, consignee city, state, distance, weight, and equipment type?")
        return
    
    # Regular expressions to extract information
    city_state_pattern = r"(?P<city>[a-zA-Z\s]+),\s*(?P<state>[a-zA-Z\s]+)"
    distance_pattern = r"(\d+)\s*miles"
    weight_pattern = r"(\d+)\s*lbs"
    equipment_pattern = r"dry van|flatbed|reefer"

    # Try extracting information using regex
    shipper_match = re.search(f"shipper city, state: {city_state_pattern}", user_message)
    consignee_match = re.search(f"consignee city, state: {city_state_pattern}", user_message)
    distance_match = re.search(distance_pattern, user_message)
    weight_match = re.search(weight_pattern, user_message)
    equipment_match = re.search(equipment_pattern, user_message)

    rate_info = {
        "shipperCity": shipper_match.group("city") if shipper_match else None,
        "shipperState": shipper_match.group("state") if shipper_match else None,
        "consigneeCity": consignee_match.group("city") if consignee_match else None,
        "consigneeState": consignee_match.group("state") if consignee_match else None,
        "distance": int(distance_match.group(1)) if distance_match else None,
        "weight": int(weight_match.group(1)) if weight_match else None,
        "equipmentType": equipment_match.group(0) if equipment_match else "dry van" # Default to dry van if not specified
    }

    # Check if all required fields are filled
    missing_fields = [key for key, value in rate_info.items() if not value]    
    if missing_fields:
        # Use GPT-4 for interpretation
        gpt_response = await chat_with_gpt(chat_id, "Can you extract the shipper city and state, consignee city and state, distance, weight, and equipment type from this message: '" + user_message + "'", task="info_extraction")
        
        # Process GPT-4 response to fill missing fields in rate_info
        # This part needs to be implemented based on how you expect GPT-4 to respond
        # For example:
        if 'shipperCity' in missing_fields:
            extracted_city = extract_city_from_gpt_response(gpt_response)
            rate_info['shipperCity'] = extracted_city

    # Check again if all required info is present
    if all(value is not None for value in rate_info.values()):
        # Prepare the arguments for the calculate_carrier_rate function
        rate_args = {
            "load_type": "FTL",  # Assuming FTL, adjust as needed
            "equipment_type": rate_info["equipmentType"],
            "distance": rate_info["distance"],
            "weight": rate_info["weight"],
            # Add more parameters as needed based on your calculate_carrier_rate function
        }
        rate = calculate_carrier_rate(**rate_args)
        await context.bot.send_message(chat_id=chat_id, text=f"The estimated rate is: ${rate:.2f}")
    else:
        await context.bot.send_message(chat_id=chat_id, text="I couldn't extract all the necessary information. Please provide more details.")

        
        
        
def extract_city_from_gpt_response(gpt_response):
    print("GPT-4 response:", gpt_response)
    # Implement logic to extract city from GPT-4 response
    # Example (you need to adapt this based on actual GPT-4 response):
    match = re.search(r"Shipper City: (\w+)", gpt_response)
    return match.group(1) if match else None


# async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     chat_id = update.effective_chat.id
#     user_message = update.message.text.lower() if update.message and update.message.text else ''
#     user_data = context.user_data
    
#       # # Check if all required details are collected
#         # if check_rate_info_completion(user_data):
#         #     # Calculate the rate
#         #     rate = calculate_carrier_rate(
#         #         user_data["distance"], user_data["weight"],
#         #         user_data["equipment_type"], user_data["consignee_city"],
#         #         user_data["consignee_state"], user_data["shipper_city"],
#         #         user_data["shipper_state"]
#         #     )
#         #     await context.bot.send_message(chat_id=chat_id, text=f"The estimated rate is: ${rate:.2f}")

#         #     # Reset the flag and clear collected data
#         #     user_data["collecting_rate_info"] = False
#         #     clear_rate_info(user_data)

#     # Check if the user is in the process of providing rate quote details
#     if user_data.get("collecting_rate_info", False):
#         key = next_key_to_collect(user_data["rate_info"])
#         user_data["rate_info"][key] = user_message
#         next_key = next_key_to_collect(user_data["rate_info"])
#         if next_key:
#             await context.bot.send_message(chat_id=chat_id, text=f"Please provide the {next_key}.")
#         else:
#             # All information collected, calculate rate
#             rate_info = user_data["rate_info"]
#             rate = calculate_carrier_rate(**rate_info)
#             await context.bot.send_message(chat_id=chat_id, text=f"The estimated rate is: ${rate:.2f}")
#             user_data["collecting_rate_info"] = False  # Reset flag
#             user_data.pop("rate_info", None)  # Clear stored data
#         return # Return to stay in the current conversation state
#     else:
#         # Start collecting rate quote information
#         if "rate quote" in user_message or "calculate rate" in user_message or "rate" in user_message:
#         # Start collecting rate quote information
#             user_data["collecting_rate_info"] = True
#             user_data["rate_info"] = {}  # Dictionary to store rate information
#             await context.bot.send_message(chat_id=chat_id, text="Please provide the distance of the shipment.")
#             return # Return to stay in the current conversation state
#         else:
#             # Normal conversation flow
#             response = await chat_with_gpt(chat_id, user_message)
#             await context.bot.send_message(chat_id=chat_id, text=response)

#     return ConversationHandler.END

# Helper functions for rate info collection
def check_rate_info_completion(user_data):
    required_fields = ["distance", "weight", "equipment_type", "consignee_city", "consignee_state", "shipper_city", "shipper_state"]
    return all(field in user_data for field in required_fields)

def clear_rate_info(user_data):
    for field in ["distance", "weight", "equipment_type", "consignee_city", "consignee_state", "shipper_city", "shipper_state"]:
        user_data.pop(field, None)

async def chat_with_gpt_for_rate_info(chat_id, user_message, user_data):
    # Implement GPT-4 conversation logic to collect rate info
    # Store collected info in user_data
    # Return the bot's response message
    # ...
    return "ok"


async def handle_rate_quote_request(json_data):
    if json_data.startswith("{") and json_data.endswith("}"):
        try:
            print("JSON Data:", json_data)
            data = json.loads(json_data)
            # Extract data from JSON
            distance = data.get("distance")
            weight = data.get("weight")
            equip_type = data.get("equipmentType")
            consignee_city = data.get("consigneeCity")
            consignee_state = data.get("consigneeState")
            shipper_city = data.get("shipperCity")
            shipper_state = data.get("shipperState")

            # Calculate rate
            rate = await calculate_carrier_rate(distance, weight, equip_type, consignee_city, consignee_state, shipper_city, shipper_state)
            return f"The estimated rate is: ${rate:.2f}"
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON data: {e}")
            return "Error parsing rate quote information."
        except Exception as e:
            logger.error(f"Error in handle_rate_quote_request: {e}")
            return "Error calculating rate."
    else:
        return json_data  # Return the original message if it's not JSON
    
async def handle_mc_dot_lookup(user_message):
    # Extract MC/DOT number from the message
    # Perform the lookup
    # ...
    return "MC/DOT Lookup Result: ..."

# async def handle_rate_quote_request(update, context):
#     if update.message and update.message.text:
#         user_message = update.message.text.lower()
#         # Parse the message for distance, weight, and base rate
#         # For simplicity, let's assume the user inputs text in a specific format like 'distance: 100, weight: 2000, base rate: 100'
#         # In a real-world scenario, you might want to use more sophisticated parsing or NLP techniques
#         distance = None
#         shipper_city = None
#         shipper_state = None
#         consignee_city = None
#         consignee_state = None
#         weight = None

#         for part in user_message.split(','):
#             if 'distance:' in part:
#                 distance = float(part.split(':')[1].strip())
#             elif 'weight:' in part:
#                 weight = float(part.split(':')[1].strip())
#             elif 'shipper city:' in part:
#                 shipper_city = part.split(':')[1].strip()
#             elif 'shipper state:' in part:
#                 shipper_state = part.split(':')[1].strip()
#             elif 'consignee city:' in part:
#                 consignee_city = part.split(':')[1].strip()
#             elif 'consignee state:' in part:
#                 consignee_state = part.split(':')[1].strip()
                
#                 # Check for missing information and prompt the user
#                 missing_info = []
#             if distance is None:
#                 missing_info.append("distance")
#             if weight is None:
#                 missing_info.append("weight")
#             if consignee_city is None:
#                 missing_info.append("consignee city")
#             if consignee_state is None:
#                 missing_info.append("consignee state")
#             if shipper_city is None:
#                 missing_info.append("shipper city")
#             if shipper_state is None:
#                 missing_info.append("shipper state")

#             if missing_info:
#                 response = f"Please provide the following missing information: {', '.join(missing_info)}."
#             else:
#                 # Calculate the rate
#                 rate = calculate_carrier_rate(distance, weight, consignee_city, consignee_state, shipper_city, shipper_state)
#                 response = f"Calculated Rate: ${rate:.2f}"
                
#                 # Fetch necessary data from the database
#                 # For example, load data based on some criteria from the user message
#                 load = {}  # Replace with actual data fetching logic
#                 response += ' Based on the load details you provided and historical load rates for similar loads, this should be a fair price for this load: ' + calculate_carrier_rate(load) + ' Is there anything else I can help you with?'
    
#                 await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
                    
def error_handler(update, context):
    """Handle any errors that occur."""
    logger.error(f"Update {update} caused error {context.error}")
    update.message.reply_text('Sorry, an error occurred. Let’s try something else.')
    
async def verify_state_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Logic for the VERIFY state
    # Provide options or guide the user to the next step
    await update.message.reply_text("Verification complete. How can I assist you further?")
    return VERIFY  # Or transition to a different state if needed

def timeout(update, context):
    """End the conversation after a timeout."""
    update.message.reply_text('Session timed out. Please start again.')
    return ConversationHandler.END

def end_conversation(update, context):
    """End the conversation gracefully."""
    update.message.reply_text('Thank you for using Hive-Bot. Have a great day!')
    return ConversationHandler.END

if __name__ == '__main__':
    try:
        # Initialize the application
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
        VERIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_state_handler)],
        GENERAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_message)],
    },
    fallbacks=[CommandHandler('cancel', cancel), CommandHandler('end', end_conversation)],
    conversation_timeout=300,
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
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        #  # Run the bot until the user presses Ctrl-C
        application.run_polling()