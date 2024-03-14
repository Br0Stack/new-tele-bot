from telegram import ForceReply, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot
from telegram.ext import Application, CallbackContext, CommandHandler, ConversationHandler, MessageHandler, filters
import os
import requests
import logging
from pymongo import MongoClient
import asyncio
import re
from openai import OpenAI
import nest_asyncio

nest_asyncio.apply()

# logging.basicConfig(level=logging.DEBUG)

# Environment variables and logging setup
FMCSA_API_KEY = os.environ['FMCSA_API_KEY']
MONGO_CLIENT = os.environ['MONGO_CLIENT']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
MAX_TOKENS_LIMIT = 350

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
    
client = MongoClient(MONGO_CLIENT)
db = client['hivedb']
hiveData = db['hive-cx-data']
gpt_client = OpenAI()

# Define conversation states
STATE = {
    'NUMBER': 0, 'VERIFY': 1, 'CONFIRM_COMPANY': 2, 'REENTER_NUMBER': 3,
    'READY_FOR_RATE_QUOTE': 4, 'RATE_QUOTE': 5, 'COLLECTING_RATE_INFO': 6,
    'GENERAL': 7, 'LOOKUP': 8, 'ENTER_NUMBER': 9, 'DEFAULT': 10, 
    'CALCULATE_RATE': 11, 'LOOKUP_CHOICE': 12, 'LOOKUP_MC_DOT': 13, 
    'LOOKUP_MC_DOT_NUMBER': 14, 'SENDING_RATE_QUOTE': 15, 'LOOKUP_COMMAND': 16, 
    'END': 17, 'ASK_DB_COMMAND': 18
}

# Utility functions
def update_conversation_history(user_id, user_message, bot_response):
    conversation = {
        "user_id": user_id,
        "messages": [{"role": "user", "content": user_message},
                     {"role": "assistant", "content": bot_response}],
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

# Lookup functions
async def lookup(update: Update, context: CallbackContext) -> int:
    reply_keyboard = [['MC Lookup', 'DOT Lookup']]
    await update.message.reply_text(
        'Welcome! How can I assist you today?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return STATE['LOOKUP']

async def lookup_choice(update: Update, context: CallbackContext) -> int:
    user_choice = update.message.text
    context.user_data['lookup_type'] = user_choice
    await update.message.reply_text(
        f'You selected {user_choice}. Please enter the number for lookup.',
        reply_markup=ReplyKeyboardRemove(),
    )
    return STATE['ENTER_NUMBER']

async def enter_number(update: Update, context: CallbackContext) -> int:
    number = update.message.text.strip()
    lookup_type = context.user_data.get('lookup_type', 'MC/DOT Lookup')

    # Perform the lookup using the FMCSA API
    lookup_result = await perform_lookup(number, lookup_type)
    
    # Send the lookup result to the user
    await update.message.reply_text(lookup_result, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def perform_lookup(number: str, lookup_type: str) -> str:
    base_url = 'https://mobile.fmcsa.dot.gov/qc/services/carriers/'
    if 'DOT' in lookup_type:
        url = f"{base_url}{number}?webKey={FMCSA_API_KEY}"
    else:  # Default to MC lookup if not explicitly DOT
        url = f"{base_url}docket-number/{number}?webKey={FMCSA_API_KEY}"
    
    response = requests.get(url)
    if response.status_code == 200:
        print("perform lookup response", response.json())
        return f"Lookup result: {response.json()}"
    else:
        return "Failed to retrieve data. Please try again later."

# Command handlers
async def start_command(update: Update, context: CallbackContext) -> int:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Hi, welcome our Hive-Bot! Please enter your MC or DOT number to get started.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return STATE['NUMBER']

async def lookup_command(update: Update, context: CallbackContext) -> int:
    # Check if user is verified; assuming verification status is stored in user_data or a database
    if context.user_data.get('verified', False):  # or any other logic to check verification
        await update.message.reply_text(
            'Please enter the MC/DOT number you wish to lookup.',
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data['awaiting_lookup'] = True
        return STATE['LOOKUP']
    else:
       await update.message.reply_text(
           'You need to verify your MC/DOT number first. Please use /start to verify.',
           reply_markup=ReplyKeyboardRemove(),
        )
       return ConversationHandler.END

async def rate_quote_command(update: Update, context: CallbackContext) -> int:
    """Send a message when the command /rate is issued."""
    # Prompt the user for rate quote details
    await context.bot.send_message(
        chat_id= update.effective_chat.id,
        text="Sure let's calculate a rate quote, please provide these details about the load: both the shipper and consignee's city, state, distance, weight, equipment type, hazmat(yes/no), extra stops, driver assistance, and storage days.",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data['rate_quote_info'] = {}
    return STATE['COLLECTING_RATE_INFO']

    # await update.message.reply_text(
    #     "Let's calculate a rate quote. Please provide the consignee zip code and shipper's zip code.",
    #     reply_markup=ReplyKeyboardRemove(),
    # )
    # context.user_data['rate_quote_info'] = {}
    # return STATE['COLLECTING_RATE_INFO']

async def list_command(update: Update, context: CallbackContext):
    """Send a message when the command /list is issued."""
    await update.message.reply_text(
        "Here are the commands that Hive-Bot can perform:\n"
        "/start - Start the bot\n"
        "/rate - Request a rate quote\n"
        "/lookup - Perform an MC/DOT lookup\n"
        "/cancel - Cancel the current operation",
        reply_markup=ReplyKeyboardRemove(),
    )
    return STATE['DEFAULT']        

async def cancel_command(update: Update, context: CallbackContext):
    """Cancels and ends the conversation."""
    await update.message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardRemove())
    return STATE['DEFAULT']  # Instead of ending the conversation

async def ask_db_command(update: Update, context: CallbackContext):
# Get the user's message
    user_message = update.message.text

    # Call the chat_with_your_database function to chat with the Super DuperDB
    result = chat_with_your_database('super-duper-collection', user_message)

    # Send the result back to the user
    await update.message.reply_text(result)
    return STATE['DEFAULT']

async def help_command(update: Update, context: CallbackContext):
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")
    
async def collect_rate_info(update, context):
# Prompt the user for rate quote information
    await update.message.reply_text("Please provide rate quote details.")
    
async def received_number(update: Update, context: CallbackContext):
    number = update.message.text
    context.user_data['number'] = number
    
   # Attempt to verify the MC/DOT number
    response = await verify_number(number)
    if response and response['status'] == 'verified':
        companyName = response['data']['carrier']['legalName'] or response['data']['carrier']['dbaName']
        reply_keyboard = [['YES', 'NO']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        await update.message.reply_text(f"Is your company name {companyName}?", reply_markup=markup)
        return STATE['CONFIRM_COMPANY']
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
        await update.message.reply_text(f"Is the company name {companyName}?", markup)
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
        return STATE['DEFAULT']  # Instead of ending the conversation
    # return ConversationHandler.END
    
async def confirm_company(update: Update, context: CallbackContext):
    user_response = update.message.text
    if user_response == 'YES':
        await update.message.reply_text("Your MC/DOT was successfully verified. You can now request a rate quote.", reply_markup=ReplyKeyboardRemove())
        return STATE['DEFAULT']  # Transition to a state ready for rate quotes
    elif user_response == 'NO':
        await update.message.reply_text("Please re-enter your MC/DOT number.", reply_markup=ReplyKeyboardRemove())
        return STATE['NUMBER']
    
async def reenter_number(update: Update, context: CallbackContext):
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
        return STATE['CONFIRM_COMPANY']
    else:
        # Handle non-verified or error cases
        await update.message.reply_text("I couldn't find any MC/DOT info for that number. Please try again or contact support.")
        return STATE['NUMBER']  # Loop back to NUMBER state
    
def end_conversation(update, context):
    """End the conversation gracefully."""
    update.message.reply_text('Thank you for using Hive-Bot. Have a great day!')
    return STATE['DEFAULT']  # Instead of ending the conversation
    # return ConversationHandler.END

async def verify_number(number: str):
    """Verify the MC or DOT number."""
    # First, try with DOT number
    response = await verify_dot(number)
    if response['status'] == 'verified':
       # if context:
           # context.user_data['verified'] = True
        return response
    elif response['status'] == 'not_verified':
    # If DOT fails, try with MC number
        response = await verify_mc(number)
        return response
    else:
        return {'status': 'error', 'message': 'Error verifying MC/DOT number.'}
  
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

async def verify_dot(user_message):
    dot_number = user_message # request.json['mc_dot_number']
    # Make the API call to FMCSA lookup API
    response = requests.get(f"https://mobile.fmcsa.dot.gov/qc/services/carriers/{dot_number}?webKey={FMCSA_API_KEY}")
    print("verify DOT response", response.json())
    details = response.json()['content']
    # Check the conditions
    if details and details['carrier']['allowedToOperate'].upper() in ['Y', 'YES']:
        return {'status': 'verified', 'message': 'MC/DOT number verified.', 'data': details}
    else:
        return {'status': 'not_verified', 'message': 'DOT info not found. Please re-enter an MC or DOT number.'} 

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


# Calculation and conversation logic
async def text_message(update: Update, context: CallbackContext):
    user_message = update.message.text.strip()
    chat_id = update.effective_chat.id
    
    if context.user_data.get('awaiting_lookup'):
        # Perform the lookup with the provided number
        lookup_result = await perform_lookup(user_message, "MC/DOT Lookup")
        await update.message.reply_text(lookup_result, reply_markup=ReplyKeyboardRemove())
        context.user_data['awaiting_lookup'] = False
        return ConversationHandler.END
    
    await context.bot.send_chat_action(chat_id=chat_id, action='TYPING')

    if user_message.strip() in ["rate", "rate quote", "rate me", "quote", "/rate"]:
        await context.bot.send_message(chat_id=chat_id, text="Sure let's calculate a rate quote, please provide these details about the load: both the shipper and consignee's city, state, distance, weight, equipment type, hazmat(yes/no), extra stops, driver assistance, and storage days.")
        return STATE['COLLECTING_RATE_INFO']
    else:
    
    # For other general messages, handle using chat_with_gpt functionality
        response = await chat_with_gpt(chat_id, user_message, task="conversation", context=context)
        await update.message.reply_text(response)
        return STATE['DEFAULT']

    # For other general messages, handle using chat_with_gpt functionality
    # response = await chat_with_gpt(chat_id, user_message, task="conversation", context=context)
    # await update.message.reply_text(response)
    # return STATE['DEFAULT']
    # else:
    #     # If all information is collected, transition to rate calculation
    #     # This assumes you have a function called calculate_rate_quote ready to handle the calculation
    #     await calculate_approximate_rate_quote(db, load_criteria, update, context)
    # return STATE['CALCULATE_RATE']
    #     prompt = "I couldn't extract all the necessary information. Please provide more details."
    #     await ask_for_clarification(chat_id, prompt, context)
    #     return STATE['COLLECTING_RATE_INFO']

  

async def chat_with_gpt(user_id, user_message, task="conversation", context=None):
    # let the user know the bot is typing
    await context.bot.send_chat_action(chat_id=user_id, action='TYPING')
    
    history = get_conversation_history(user_id)
    history.append({
            "role": "system",  # Use "system" for initial instructions
            "content": f'''You are Hive Engine Logistics Bot, an advanced AI assistant designed to support shippers and carriers in the logistics industry. It provides real-time tracking updates, delivery times, rate calculations, carrier information, and answers inquiries, resolves issues, and guides shipping best practices. The HELA bot delivers excellent customer service and support of logistics business.
                Key Features:
                - Real-Time Data Access: Connects to a MongoDB instance with multiple logistics data platform's data for up-to-date tracking information
                - Comprehensive Tracking: Offers detailed information including location, status, and delivery times
                - Enhanced Rate Calculation: Incorporates variables like fuel costs and tolls for accurate rates
                - Industry Updates: Regularly updates on trends and regulations
                Response Guidelines:
                - Prioritize historic data retrieval and accurate analytics on historic loads in the database and their insights, including rate.
                - Offer predictive insights and context-aware recommendations for freight logistics companies
                - Maintain an up-to-date knowledge base of industry trends and regulations
                Ethical and Compliance Considerations:
                - Uphold data privacy standards
                - Comply with terms and conditions of logistics data providers
                - Avoid storing sensitive information beyond current queries
                Analyze this user's conversation and if they just made conversation with you that doesn't trigger a rate quote or mc/dot number lookup conversation handler functionality, handle it conversationally and naturally, otherwise tell them to use the '/lookup', 'rate',
                or '/rate' commands.'''
        },)
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
            max_tokens=400,
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

def chat_with_your_database(collection_name, query):
    # Correctly format the prompt as a message dictionary
    messages = [
        {
            "role": "system",  # Use "system" for initial instructions
            "content": f'''Hive Engine Logistics Bot is an advanced AI assistant designed to support shippers and carriers in the logistics industry. It provides real-time tracking updates, delivery times, rate calculations, carrier information, and answers inquiries, resolves issues, and guides shipping best practices. The HELA bot delivers excellent customer service and support of logistics business.
                Key Features:
                - Real-Time Data Access: Connects to multiple logistics data platforms for up-to-date tracking information
                - Comprehensive Tracking: Offers detailed information including location, status, and delivery times
                - Advanced Data Analysis: Uses machine learning for predictive insights on delays, cost-effective routes, and optimal shipment times
                - Context-Aware Recommendations: Considers factors like carrier reputation, tracking and lane procurement
                - Interactive Troubleshooting Guides: Provides step-by-step guides for common logistics issues
                - Personalized Experience: Tailors suggestions based on user history and preferences
                - External Tool Integration: Integrates with external logistics management tools
                - Enhanced Rate Calculation: Incorporates variables like fuel costs and tolls for accurate rates
                - Feedback Loop: Implements a user feedback system for continuous improvement to the rate estimate functionality and MC/DOT number lookup features
                - Industry Updates: Regularly updates on trends and regulations
                Response Guidelines:
                - Prioritize historic data retrieval and accurate analytics on historic loads in the database and their insights, including rate.
                - Offer predictive insights and context-aware recommendations
                - Guide users interactively through troubleshooting
                - Personalize interactions for regular users
                - Maintain an up-to-date knowledge base of industry trends and regulations
                Ethical and Compliance Considerations:
                - Uphold data privacy standards
                - Comply with terms and conditions of logistics data providers
                - Avoid storing sensitive information beyond current queries
                Continuous Improvement:
                - Update the system for new platforms and better compatibility
                - Refine data retrieval for speed and reliability'''
        },
        {
            "role": "user",  # Use "user" for user-like queries
            "content": f"Act as a database administrator and data scientist highly skilled in MongoDB and advanced data business analytics. Here's the task: analyse the collection named {collection_name} for similar loads, give an accurate rate quote for the given criteria based on historic loads that are similar enough, probably best to. The query is: {query}"
        }
    ]
    
    # Make the API call with the correctly formatted messages
    openai_chat = gpt_client.chat.completions.create(
        model='gpt-4-1106-preview',
        messages=messages  # Pass an array of message strings or objects
    )
    
    print(f"Rate quote calculated: {openai_chat}")  # Debugging line

    # Return the response from GPT
    return openai_chat

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

        if result and 'averageRate' in result[0]:
            average_rate = result[0]['averageRate']
            message = f"The estimated rate is: ${average_rate:.2f}"
        else:
            message = "No similar historical data found to calculate an approximate rate."
    except Exception as e:
        message = f"Sorry, I couldn't process that due to an error: {e}"

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
    user_message = update.message.text
    chat_id = update.message.chat_id
    
    # Initialize load_criteria at the beginning
    load_criteria = {}
    
    # Regex patterns to extract load criteria
    #it sdhould match from this test string and any variation the user could ask: "Shipper zip 33570, consignee zip 33166, bill distance 250 miles, weight is 40000 lbs, no extra drops, dry van"
    shipper_zip_pattern = r"\b(?:shipper(?:'s)?\s(?:zip(?:\scode)?|code)\s*[:=]?\s*|)(\d{5})\b" 
    #|shipper\s(?:zip\s)?(?:code\s)?(?:is\s|:)?\s?(\d{5})"
    consignee_zip_pattern = r"\b(?:consignee(?:'s)?\s(?:zip(?:\scode)?|code)\s*[:=]?\s*|)(\d{5})\b"
    distance_pattern = r"\b(?:distance\s*[:=]?\s*|)(\d+)\s*(?:miles?|mi\b)"
    weight_pattern = r"\b(\d+)\s*(?:lbs?|pounds?|kg|kilograms?)\b"
    # extra_stops_pattern = r"\b(?:extra\s(?:stops?|drops?|pickups?)\s*[:=]?\s*|)(\d*)\b"
    driver_assist_pattern = r"\bdriver\s(?:assistance|assist|help|aid|support|service)\b"
    
    shipper_zipmatch = re.search(shipper_zip_pattern, user_message, re.IGNORECASE)
    consignee_zipmatch = re.search(consignee_zip_pattern, user_message, re.IGNORECASE)
    distance_match = re.search(distance_pattern, user_message, re.IGNORECASE)
    weight_match = re.search(weight_pattern, user_message, re.IGNORECASE)
    # equipment_match = re.search(equipment_pattern, user_message, re.IGNORECASE)
    # hazmat_match = re.search(hazmat_pattern, user_message, re.IGNORECASE)
    # extra_stops_match = re.search(extra_stops_pattern, user_message, re.IGNORECASE)    
    driver_assist_match = re.search(driver_assist_pattern, user_message, re.IGNORECASE)
    # storage_days_match = re.search(storage_days_pattern, user_message, re.IGNORECASE)

       # Use regex searches to fill the dictionary
    load_criteria['Shipper zip'] = re.search(shipper_zip_pattern, user_message, re.IGNORECASE).group(1) if re.search(shipper_zip_pattern, user_message) else "00000"
    load_criteria['Consignee zip'] = int(re.search(consignee_zip_pattern, user_message, re.IGNORECASE).group(1)) if re.search(consignee_zip_pattern, user_message) else 00000
    load_criteria['Bill Distance'] = int(re.search(distance_pattern, user_message, re.IGNORECASE).group(1)) if re.search(distance_pattern, user_message) else 0
    load_criteria['Weight'] = int(re.search(weight_pattern, user_message, re.IGNORECASE).group(1)) if re.search(weight_pattern, user_message) else 0
    load_criteria['Driver assistance'] = re.search(driver_assist_pattern, user_message, re.IGNORECASE).group(1) if re.search(driver_assist_pattern, user_message) else "No"
    # load_criteria['Extra drops'] = int(re.search(extra_stops_pattern, user_message, re.IGNORECASE).group(1)) if re.search(extra_stops_pattern, user_message) else 0

    # extra_stops_search = re.search(extra_stops_pattern, user_message, re.IGNORECASE)
    # if extra_stops_search:
    #     extra_stops_str = extra_stops_search.group(1)
    #     load_criteria['Extra drops'] = int(extra_stops_str) if extra_stops_str.isdigit() else 0
    # else:
    #     load_criteria['Extra drops'] = 0

    # Now that we have extracted load criteria, calculate the rate quote.
    await context.bot.send_message(chat_id=chat_id, text=f"I understand your load criteria is: {load_criteria}, please wait while I run some advanced calculations and analysis...")


    # load_criteria = {
    #     "Shipper zip": str(shipper_zipmatch.group(1)) if shipper_zipmatch else "00000",
    #     "Consignee zip": int(consignee_zipmatch.group(1)) if consignee_zipmatch else 00000,
    #     "Bill Distance": int(distance_match.group(1)) if distance_match else 0,
    #     "Weight": int(weight_match.group(1)) if weight_match else 0,
    #     # "Trailer type": equipment_match.group(0) if equipment_match else "V",
    #     # "Hazmat routing": hazmat_match.group(0) if hazmat_match else "No",
    #     "Extra drops": int(extra_stops_match.group(1)) if extra_stops_match else 0,
    #     "Driver assistance": driver_assist_match.group(0) if driver_assist_match else "No",
    #     # "Storage days": int(storage_days_match.group(1)) if storage_days_match else 0
    # }
    print("load_criteria", load_criteria)

    missing_fields = await check_missing_or_unclear_fields(load_criteria, update)
    if missing_fields:
        prompt = "I couldn't understand all the necessary information. Please provide the ${missing_fields}."  # Use f-strings to insert the missing fields
        await ask_for_clarification(chat_id, prompt, context)
        return STATE['COLLECTING_RATE_INFO']
    else:
        rate = await calculate_approximate_rate_quote(db, load_criteria, update, context)
    await context.bot.send_message(chat_id=chat_id, text=f"{rate}")
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
            return STATE['COLLECTING_RATE_INFO']

    # Aggregation and Calculation
    rate_quote = await calculate_approximate_rate_quote(db, load_criteria, update, context)

    # Send the calculated rate quote to the user
    await context.bot.send_message(chat_id=chat_id, text=f"The estimated rate is: ${rate_quote}")

    # Prompt for feedback or next action
    await context.bot.send_message(chat_id=chat_id, text="Please provide your feedback on the quote or let me know if you want to request another quote or switch to conversational mode.")

    return STATE['AFTER_RATE_QUOTE']  # Assume this is a state that handles post-quote interactions

# Error handler
def error_handler(update: Update, context: CallbackContext):
    logger.warning(f'Update "{update}" caused error "{context.error}"')

async def echo(update: Update, context: CallbackContext):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message)
                                   
async def main():
    application = Application.builder().token(os.environ["TELEGRAM_API_KEY"]).build()
    start_command_handler = CommandHandler('start', start_command)
    text_message_handler = MessageHandler(filters.TEXT, text_message)
    lookup_mc_dot_handler = MessageHandler(filters.Regex(r"MC|DOT"), lookup)
    lookup_command_handler = CommandHandler('lookup', lookup_command)
    ask_db_command_handler = CommandHandler('chatdb', ask_db_command)
    rate_quote_command_handler = CommandHandler('rate', extract_and_calculate_rate_quote)
    sending_rate_quote_handler = MessageHandler(filters.TEXT, extract_and_calculate_rate_quote)
        
    conv_handler = ConversationHandler(
        allow_reentry=True,
        entry_points=[CommandHandler('start', start_command)],
        states={
            STATE['NUMBER']: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_number)],
            STATE['VERIFY']: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_number)],
            STATE['CONFIRM_COMPANY']: [MessageHandler(filters.Regex('^(YES|NO)$'), confirm_company)],
            STATE['REENTER_NUMBER']: [MessageHandler(filters.TEXT & ~filters.COMMAND, reenter_number)],
            STATE['READY_FOR_RATE_QUOTE']: [MessageHandler(filters.TEXT & ~filters.COMMAND, extract_and_calculate_rate_quote)],
            STATE['CALCULATE_RATE']: [MessageHandler(filters.TEXT & ~filters.COMMAND, extract_and_calculate_rate_quote)],
            STATE['RATE_QUOTE']: [MessageHandler(filters.TEXT & ~filters.COMMAND, rate_quote_command)],
            STATE['COLLECTING_RATE_INFO']: [MessageHandler(filters.TEXT & ~filters.COMMAND, extract_and_calculate_rate_quote)],
            STATE['GENERAL']: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_message)],
            STATE['LOOKUP_MC_DOT']: [MessageHandler(filters.Regex(r"MC|DOT"), lookup)],
            STATE['LOOKUP_COMMAND']: [CommandHandler('lookup', lookup_command)],
            STATE['ASK_DB_COMMAND']: [CommandHandler('chatdb', ask_db_command)],
            STATE['RATE_QUOTE']: [CommandHandler('rate', rate_quote_command)],
            STATE['SENDING_RATE_QUOTE']: [MessageHandler(filters.TEXT & ~filters.COMMAND, extract_and_calculate_rate_quote)],
            STATE['LOOKUP']: [
                CommandHandler('lookup', lookup_command),
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_number)
            ],
            STATE['ENTER_NUMBER']: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_number)],
            STATE['DEFAULT']: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_message)],
        }, 
        # Define states based on STATE dict
        fallbacks=[CommandHandler('cancel', cancel_command), CommandHandler('end', end_conversation)],
        conversation_timeout=500,
        )
    # Register handlers
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.Regex(r"MC|DOT|lookup"), lookup))
    application.add_handler(CommandHandler('lookup', lookup_command))
    application.add_handler(CommandHandler('chatdb', ask_db_command))
    application.add_handler(CommandHandler('rate', rate_quote_command))
    application.add_handler(CommandHandler('list', list_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    application.add_error_handler(error_handler)
    application.add_handler(start_command_handler)
    application.add_handler(text_message_handler)
    application.add_handler(lookup_mc_dot_handler)
    application.add_handler(lookup_command_handler)
    application.add_handler(ask_db_command_handler)
    application.add_handler(rate_quote_command_handler)
    application.add_handler(sending_rate_quote_handler)
    
    # On non-command textual messages - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Start the bot
    await application.run_polling()
    
#     # try:

#     # Start the bot
#     await application.initialize()
#     # await asyncio.get_event_loop().create_task(application.run_polling())
#     await application.run_polling()
#     # finally:
#         # Shutdown the bot
#         # await application.shutdown()

if __name__ == '__main__':
    asyncio.run(main())

  # Run the bot and Flask app
    # asyncio.get_event_loop().create_task(application.run_polling())
