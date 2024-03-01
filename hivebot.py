# from telegram import ForceReply, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
# from telegram.ext import Application, CallbackContext, ContextTypes, CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
# import os
# import requests
# import logging
# from pymongo import MongoClient, collection, database, aggregation
# import asyncio
# import re
# from openai import OpenAI
# import json
# import numpy as np
# import requests
# import requests
# from telegram import ReplyKeyboardRemove
# from telegram import Update
# from telegram.ext import ContextTypes
# from enum import Enum
# from telegram import Bot
# import asyncio

# # Set up environment variables and logging
# FMCSA_API_KEY = os.environ['FMCSA_API_KEY']
# MONGO_CLIENT = os.environ['MONGO_CLIENT']
# OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
# MAX_TOKENS_LIMIT = 280

# logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
# logger = logging.getLogger(__name__)
# client = MongoClient(MONGO_CLIENT)
# db = client['hivedb']
# hiveData = db['hive-cx-data']
# gpt_client = OpenAI()

# SUPER_DUPER_DB = db

# # Define states for the conversation
# NUMBER, VERIFY, CONFIRM_COMPANY, REENTER_NUMBER, READY_FOR_RATE_QUOTE, RATE_QUOTE, COLLECTING_RATE_INFO, GENERAL, LOOKUP, ENTER_NUMBER, DEFAULT = range(11)

# def update_conversation_history(user_id, user_message, bot_response):
#     conversation = {
#         "user_id": user_id,
#         "messages": [{"role": "user", "content": user_message},
#                      {"role": "assistant", "content": bot_response}]
#     }
#     db.conversations.update_one(
#         {"user_id": user_id},
#         {"$push": {"messages": {"$each": conversation["messages"]}}},
#         upsert=True
#     )


# def get_conversation_history(user_id):
#     try:
#         conversation_record = db.conversations.find_one({"user_id": user_id})
#         return conversation_record["messages"] if conversation_record else []
#     except Exception as e:
#         logger.error(f"Error fetching conversation history: {e}")
#         return []

# # Command handler for start
# async def lookup(update: Update, context: CallbackContext) -> int:
#     reply_keyboard = [['MC Lookup', 'DOT Lookup']]
#     await update.message.reply_text(
#         'Welcome! How can I assist you today?',
#         reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
#     )
#     return LOOKUP

# # Handler for MC/DOT lookup choice
# async def lookup_choice(update: Update, context: CallbackContext) -> int:
#     user_choice = update.message.text
#     context.user_data['lookup_type'] = user_choice
#     await update.message.reply_text(
#         f'You selected {user_choice}. Please enter the number for lookup.',
#         reply_markup=ReplyKeyboardRemove(),
#     )
#     return ENTER_NUMBER

# # Handler for entering MC/DOT number
# async def enter_number(update: Update, context: CallbackContext) -> int:
#     number = update.message.text.strip()
#     lookup_type = context.user_data.get('lookup_type', 'MC/DOT Lookup')

#     # Perform the lookup using the FMCSA API
#     lookup_result = await perform_lookup(number, lookup_type)
    
#     # Send the lookup result to the user
#     await update.message.reply_text(lookup_result, reply_markup=ReplyKeyboardRemove())
#     return ConversationHandler.END

# # Function to perform the MC/DOT lookup
# async def perform_lookup(number: str, lookup_type: str) -> str:
#     base_url = 'https://mobile.fmcsa.dot.gov/qc/services/carriers/'
#     if 'DOT' in lookup_type:
#         url = f"{base_url}{number}?webKey={FMCSA_API_KEY}"
#     else:  # Default to MC lookup if not explicitly DOT
#         url = f"{base_url}docket-number/{number}?webKey={FMCSA_API_KEY}"
    
#     response = requests.get(url)
#     if response.status_code == 200:
#         print(response.json())
#         return f"Lookup result: {response.json()}"
#     else:
#         return "Failed to retrieve data. Please try again later."

# # Handler for canceling the operation
# async def cancel(update: Update, context: CallbackContext) -> int:
#     await update.message.reply_text(
#         'Operation cancelled. Use /start to begin again.',
#         reply_markup=ReplyKeyboardRemove(),
#     )
#     return ConversationHandler.END


# def chat_with_your_database(collection_name, query):
#     # Correctly format the prompt as a message dictionary
#     messages = [
#         {
#             "role": "system",  # Use "system" for initial instructions
#             "content": f'''Hive Engine Logistics Bot is an advanced AI assistant designed to support shippers and carriers in the logistics industry. It provides real-time tracking updates, delivery times, rate calculations, carrier information, and answers inquiries, resolves issues, and guides shipping best practices. The HELA bot delivers excellent customer service and support of logistics business.
#                 Key Features:
#                 - Real-Time Data Access: Connects to multiple logistics data platforms for up-to-date tracking information
#                 - Comprehensive Tracking: Offers detailed information including location, status, and delivery times
#                 - Advanced Data Analysis: Uses machine learning for predictive insights on delays, cost-effective routes, and optimal shipment times
#                 - Context-Aware Recommendations: Considers factors like carrier reputation, tracking and lane procurement
#                 - Interactive Troubleshooting Guides: Provides step-by-step guides for common logistics issues
#                 - Personalized Experience: Tailors suggestions based on user history and preferences
#                 - External Tool Integration: Integrates with external logistics management tools
#                 - Enhanced Rate Calculation: Incorporates variables like fuel costs and tolls for accurate rates
#                 - Feedback Loop: Implements a user feedback system for continuous improvement to the rate estimate functionality and MC/DOT number lookup features
#                 - Industry Updates: Regularly updates on trends and regulations
#                 Response Guidelines:
#                 - Prioritize historic data retrieval and accurate analytics on historic loads and their insights including rate.
#                 - Offer predictive insights and context-aware recommendations
#                 - Guide users interactively through troubleshooting
#                 - Personalize interactions for regular users
#                 - Maintain an up-to-date knowledge base of industry trends and regulations
#                 Ethical and Compliance Considerations:
#                 - Uphold data privacy standards
#                 - Comply with terms and conditions of logistics data providers
#                 - Avoid storing sensitive information beyond current queries
#                 Continuous Improvement:
#                 - Update the system for new platforms and better compatibility
#                 - Refine data retrieval for speed and reliability'''
#         },
#         {
#             "role": "user",  # Use "user" for user-like queries
#             "content": f"Act as a database administrator and data scientist highly skilled in MongoDB and advanced data business analytics. Here's the task: analyse the collection named {collection_name} for similar loads, give an accurate rate quote for the given criteria based on historic loads that are similar enough, probably best to. The query is: {query}"
#         }
#     ]
    
#     # Make the API call with the correctly formatted messages
#     openai_chat = gpt_client.chat.completions.create(
#         model='gpt-4-1106-preview',
#         messages=messages  # Pass an array of message strings or objects
#     )
    
#     print(f"Rate quote calculated: {openai_chat}")  # Debugging line

#     # Return the response from GPT
#     return openai_chat

# # Define a command handler for the "/chatdb" command
# async def chat_db_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     # Get the user's message
#     user_message = update.message.text

#     # Call the chat_with_your_database function to chat with the Hive database
#     result = await chat_with_your_database('hive-cx-data', user_message)

#     # Send the result back to the user
#     await update.message.reply_text(result)

#     return DEFAULT

# async def chat_with_gpt(user_id, user_message, task="conversation", context=None):
#     # let the user know the bot is typing
#     await context.bot.send_chat_action(chat_id=user_id, action='TYPING')
    
#     history = get_conversation_history(user_id)
#     history.append({"role": "user", "content": user_message})

#     # Convert each message content to string and then join
#     content_history = " ".join([msg.get('content', '') for msg in history])

#     # Truncate history if it's too long
#     while len(content_history) > MAX_TOKENS_LIMIT:
#         history.pop(0)
#         content_history = " ".join([msg.get('content', '') for msg in history])

#     try:
#         response = gpt_client.chat.completions.create(
#             model="gpt-4-1106-preview",
#             messages=history,
#             max_tokens=200,
#             stop=None if task == "conversation" else ["\n"]  # Adjust stopping condition based on the task
#         )

#         # Extract the text response and update history
#         gpt_response = response.choices[0].message.content if response.choices else ""
        
#         # Update conversation history for general conversation
#         if task == "conversation":
#             update_conversation_history(user_id, user_message, gpt_response)

#         return gpt_response
#     except Exception as e:
#         logger.error(f"Error in chat_with_gpt: {e}")
#         return "I'm having trouble understanding that. Could you rephrase or ask something else?"


# # Define command handlers. These usually take the two arguments update and context
# async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Send a message when the command /start is issued."""
#     await update.message.reply_text(
#         "Hi, welcome to Hive-Bot! Please enter your MC or DOT number to get started.",
#         reply_markup=ReplyKeyboardRemove(),
#     )
#     return NUMBER

# async def rate_quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Send a message when the command /rate_quote is issued."""
#     await update.message.reply_text(
#         "Let's calculate a rate quote. Please provide the shipper's city and state.",
#         reply_markup=ReplyKeyboardRemove(),
#     )
#     context.user_data['rate_quote_info'] = {}
#     return COLLECTING_RATE_INFO

# async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Send a message when the command /list is issued."""
#     await update.message.reply_text(
#         "Here are the commands that Hive-Bot can perform:\n"
#         "/start - Start the bot\n"
#         "/rate - Request a rate quote\n"
#         "/lookup - Perform an MC/DOT lookup\n"
#         "/cancel - Cancel the current operation",
#         reply_markup=ReplyKeyboardRemove(),
#     )
#     return DEFAULT

# async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Cancels and ends the conversation."""
#     await update.message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardRemove())
#     return DEFAULT  # Instead of ending the conversation
#     # return ConversationHandler.END

# async def ask_db_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     # Get the user's message
#     user_message = update.message.text

#     # Call the chat_with_your_database function to chat with the Super DuperDB
#     result = chat_with_your_database('super-duper-collection', user_message)

#     # Send the result back to the user
#     await update.message.reply_text(result)
#     return DEFAULT

# async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """Send a message when the command /help is issued."""
#     await update.message.reply_text("Help!")
    
# async def received_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     number = update.message.text
#     context.user_data['number'] = number
    
#    # Attempt to verify the MC/DOT number
#     response = await verify_number(number)
#     if response and response['status'] == 'verified':
#         companyName = response['data']['carrier']['legalName'] or response['data']['carrier']['dbaName']
#         reply_keyboard = [['YES', 'NO']]
#         markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
#         await update.message.reply_text(f"Is your company name {companyName}?", reply_markup=markup)
#         return CONFIRM_COMPANY
#     if response and response['status'] == 'verified':
#         await update.message.reply_text("Your MC/DOT was successfully verified. Hive Bot features fully activated.")
#         # Store the MC/DOT and user in the hive database
#         try:  
#             db.users.update_one({'chat_id': update.effective_chat.id}, {'$set': {'mc_dot_number': number, 'fmcsa_data': response}}, upsert=True)
#         except Exception as e:
#             logger.error(f"Database error: {e}")
#     elif response and response['status'] == 'ask':
#         companyName = response[0]['legalName'] or response[0]['dbaName']
#         reply_keyboard = [['YES', 'NO']]
#         markup = ReplyKeyboardMarkup(reply_keyboard, input_field_placeholder="Is your company name {companyName}?", one_time_keyboard=True)
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
#     elif response and response['status'] == 'not_verified':
#         await update.message.reply_text("Your MC/DOT number could not be authorized. Please try again or contact support.")
#     else:
#         await update.message.reply_text("I couldn't find any MC/DOT info for that number. Please try again or contact support.")
#         return DEFAULT  # Instead of ending the conversation
#     # return ConversationHandler.END

# async def confirm_company(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     user_response = update.message.text
#     if user_response == 'YES':
#         await update.message.reply_text("Your MC/DOT was successfully verified. You can now request a rate quote.", reply_markup=ReplyKeyboardRemove())
#         return DEFAULT  # Transition to a state ready for rate quotes
#     elif user_response == 'NO':
#         await update.message.reply_text("Please re-enter your MC/DOT number.", reply_markup=ReplyKeyboardRemove())
#         return NUMBER

# async def reenter_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
#         return NUMBER  # Loop back to NUMBER state

# async def verify_number(number: str) -> dict:
#     """Verify the MC or DOT number."""
#     # First, try with DOT number
#     response = await verify_dot(number)
#     if response['status'] == 'verified':
#        # if context:
#            # context.user_data['verified'] = True
#         return response
#     elif response['status'] == 'not_verified':
#     # If DOT fails, try with MC number
#         response = await verify_mc(number)
#         return response
#     else:
#         return {'status': 'error', 'message': 'Error verifying MC/DOT number.'}

# # rate_quote_tool = {
# #     "type": "function",
# #     "function": {
# #         "name": "calculate_dynamic_rate_quote",
# #         "description": "Calculate dynamic rate quote for carriers based on input criteria",
# #         "parameters": {
# #             "type": "object",
# #             "properties": {
# #                 "distance": {"type": "number"},
# #                 "weight": {"type": "number"},
# #                 "shipperCity": {"type": "string"},
# #                 "shipperState": {"type": "string"},
# #                 "consigneeCity": {"type": "string"},
# #                 "consigneeState": {"type": "string"},
# #                 "equipmentType": {"type": "string"},
# #                 "hazmat": {"type": "boolean"},
# #             },
# #             "required": ["distance", "weight", "shipperCity", "shipperState", "consigneeCity", "consigneeState", "equipmentType", "hazmat"]
# #         }
# #     }
# # }


# # def calculate_rate_with_gpt(user_message: str, user_id: str):
# #     try:
# #         print(f"User ID: {user_id}, User Message: {user_message}")
# #         # Fetch and filter the conversation history
# #         history = get_conversation_history(user_id)
# #         valid_history = [msg for msg in history if isinstance(msg.get('content'), str) and msg['content']]

# #         # Append the current user message to the valid history
# #         valid_history.append({"role": "user", "content": user_message})
# #         print("Valid history being sent to GPT-4:", valid_history)

# #         # Send the filtered history to GPT-4
# #         completion = gpt_client.chat.completions.create(
# #             model="gpt-4-0613",
# #             messages=valid_history,
# #             tools=[rate_quote_function],
# #             tool_choice="auto"
# #         )
# #         print("Completion object from GPT-4:", completion)
        
# #     # Check if rate calculation is needed
# #         if "calculate_dynamic_rate_quote" in gpt_response:
# #             # Extract necessary data for rate calculation from user_message or history
# #             # For example:
# #             # distance = 1800  # Extract from user_message or history
# #             # weight = 20000  # Extract from user_message or history
# #             # base_rate = 100  # This could be a default or calculated value
# #             # Modify these values as needed

# #             # Calculate rate
# #             rate = calculate_carrier_rate(distance, weight, consignee_city, consignee_state, shipper_city, shipper_state)

# #             # Construct a response with the calculated rate
# #             gpt_response = f"The estimated rate is: ${rate:.2f}"
        
# #         if completion.choices and len(completion.choices) > 0:
# #             gpt_response = completion.choices[0].message.content
# #             update_conversation_history(user_id, user_message, gpt_response)
# #             return gpt_response
# #         else:
# #             logger.error(f"No response from GPT-4 for rate quote calculation. Completion object: {completion}")
# #             return "GPT-4 did not provide a response."

# #     except Exception as e:
# #         logger.error(f"Error in calculate_rate_with_gpt: {e}")
# #         return f"Sorry, I couldn't process that due to an error: {e}"

# def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#         """Cancels and ends the conversation."""
#         update.message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardMarkup(one_time_keyboard=True))
#         return DEFAULT  # Instead of ending the conversation
#         # return ConversationHandler.END
    
# # async def start_command(update, context):
# #     await context.bot.send_message(chat_id=update.effective_chat.id, text='Hello, welcome to Hive-Bot. Please provide your MC or DOT number to get started. Type /list to see a list of all commands that hive-bot can perform.')

# async def verify_dot(user_message):
#     dot_number = user_message # request.json['mc_dot_number']
#     # Make the API call to FMCSA lookup API
#     response = requests.get(f"https://mobile.fmcsa.dot.gov/qc/services/carriers/{dot_number}?webKey={FMCSA_API_KEY}")
#     print(response.json())
#     details = response.json()['content']
#     # Check the conditions
#     if details and details['carrier']['allowedToOperate'].upper() in ['Y', 'YES']:
#         return {'status': 'verified', 'message': 'MC/DOT number verified.', 'data': details}
#     else:
#         return {'status': 'not_verified', 'message': 'DOT info not found. Please re-enter an MC or DOT number.'} 
    
# async def verify_mc(user_message, context):
#     mc_number = user_message # request.json['mc_dot_number']
#     # Make the API call to FMCSA lookup API
#     response = requests.get(f"https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{mc_number}?webKey={FMCSA_API_KEY}")
#     print(response.json())
#     if response.status_code == 200 and response.json()["content"]:
#         # Check the conditions
#         if response.json()['content'][0]:
#             context.user_data['verified'] = True
#             return {'status': 'ask', 'message': 'MC/DOT number verified.', 'data': response.json()["content"]}
#         else:
#             return {'status': 'not_verified', 'message': 'MC info not found. Please re-enter an MC or DOT number.'}


# #     Objective: Leverage the 'hive-cx-data' collection to derive an estimated freight rate quotation by analyzing historical data trends based on specified load criteria.
# # Step 1: Rate Calculation
# # Utilize the formula below to initially compute the freight rate. Adjust the fuel surcharge as necessary and select the equipment type multiplier applicable to the load.
# #     Base Rate Calculation:
# #     Base Rate = Distance (miles) × Base Rate per Mile ($1.2) × Equipment Type Multiplier
# #     Fuel Surcharge Addition:
# #     Total Rate = Base Rate + (Distance × Fuel Surcharge per Mile ($0.5))
# #     Equipment Type Multipliers:
# #     {V: 1, PO: 1, FO: 0.8, R: 1.2, VM: 1.7, RM: 2.2, F: 0.8}
# #     Additional Charges:
# #     Include fees for driver assistance, hazardous materials (hazmat), extra stops, and LTL (Less Than Truckload) specific charges (weight and volume based), storage fees, and toll charges as applicable.
# # Step 2: Rate Adjustment
# # Refine the computed rate by incorporating historical trends from the 'hive-cx-data' collection. Focus on matching load criteria such as distance, weight, and locations (shipper and consignee cities and states) with historical records to adjust the rate for higher accuracy.
# # Criteria for Historical Data Matching:
# #     Distance
# #     Weight
# #     Shipper City and State
# #     Consignee City and State
# # Expected Output:
# # Provide an adjusted, approximate rate quote in US dollars that reflects both the calculated rate and adjustments based on historical data analysis.
# #     def calculate_approximate_rate_quote(db, load_criteria):
# #     try:
# #         query = {"""
# #              Fetch historical data matchrate_quote_c: 1.7, RM: 2.2, F: 0.8}
# # #     Additional Charges:
# # #     Include fees for driver assistance, hazardous materials (hazmat), extra stops, and LTL (Less Than Truckload) specific charges (weight and volume based), storage fees, and toll charges as applicable.
# # # Step 2: Rate Adjustment
# # # Refine the computed rate by incorporating historical trends from the 'hive-cx-data' collection. Focus on matching load criteria such as distance, weight, and locations (shipper and consignee cities and states) with historical records to adjust the rate for higher accuracy.
# # # Criteria for Historical Data Matching:
# # #     Distance
# # #     Weight
# # #     Shipper City and State
# # #     Consignee City and State
# # # Expected Output:
# # # Provide an adjusted, approximate rate quote in US dollars that reflects both the calculated rate and adjustments based on historical data analysis. Here are the collection fields present in the mongodb collection: 
# #                 "Load Type"
# #                " equipment Type"
# #                 "distance"
# #                 "weight"
# #                 "volume"
# #                 "hazmat"
# #                 "extra Stops"
# #                 "driver Assistance"
# #                 "storage Days"
# #                 "toll Charges"
                
# #                 and here is th euser's input: {load_criteria}
# #              """}
# #         print(query)
# #         # Analyze the historical data to calculate the rate
# #         # This is a placeholder for your analysis logic, which might involve
# #         # statistical analysis or machine learning models to predict the rate
# #         historical_data = []

# #         rates = [data["rate"] for data in historical_data]

#     # """
#     # Calculate the approximate rate quote based on similar historical data.

#     # Args:
#     #     db (Database): The database object used for querying historical data.
#     #     load_criteria (dict): The criteria for the load, including shipper city, shipper state,
#     #                           consignee city, consignee state, equipment type, weight, and distance.

#     # Returns:
#     #     str: The approximate rate quote based on similar historical data, or a message indicating
#     #          that no similar historical data was found.

#     # Raises:
#     #     Exception: If there is an error processing the rate quote.

#     # """
    
# async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     user_message = update.message.text.strip()
#     chat_id = update.effective_chat.id
    
#     if context.user_data.get('awaiting_lookup'):
#         # Perform the lookup with the provided number
#         lookup_result = await perform_lookup(user_message, "MC/DOT Lookup")
#         await update.message.reply_text(lookup_result, reply_markup=ReplyKeyboardRemove())
#         context.user_data['awaiting_lookup'] = False
#         return ConversationHandler.END
    
#     await context.bot.send_chat_action(chat_id=chat_id, action='TYPING')

#     if user_message.strip() in ["rate", "rate quote", "rate me", "quote", "/rate"]:
#         await context.bot.send_message(chat_id=chat_id, text="Sure let's calculate a rate quote, please provide these details about the load: both the shipper and consignee's city, state, distance, weight, equipment type, hazmat(yes/no), extra stops, driver assistance, and storage days.")
#         return ConversationState.COLLECTING_RATE_INFO

#     shipper_zip_pattern = r"(\d{5})"
#     consignee_zip_pattern = r"(\d{5})"
#     distance_pattern = r"(\d+)\s*miles"
#     weight_pattern = r"(\d+)\s*lbs"
#     equipment_pattern = r"dry van|flatbed|reefer|tep deck|conestoga|power only|auto carrier|double drop|lowboy|stretch|extendable|multi axle|other"
#     hazmat_pattern = r"hazmat|yes|no"
#     extra_stops_pattern = r"(\d+)\s*stops"
#     driver_assist_pattern = r"driver\s*assistance|yes|no"
#     storage_days_pattern = r"(\d+)\s*days"
    
#     shipper_zipmatch = re.search(shipper_zip_pattern, user_message)
#     consignee_zipmatch = re.search(consignee_zip_pattern, user_message)
#     distance_match = re.search(distance_pattern, user_message)
#     weight_match = re.search(weight_pattern, user_message)
#     equipment_match = re.search(equipment_pattern, user_message)
#     hazmat_match = re.search(hazmat_pattern, user_message)
#     extra_stops_match = re.search(extra_stops_pattern, user_message)
#     driver_assist_match = re.search(driver_assist_pattern, user_message)
#     storage_days_match = re.search(storage_days_pattern, user_message)

#     load_criteria = {
#         "Shipper zip": shipper_zipmatch.group(1) if shipper_zipmatch else None,
#         "Consignee zip": consignee_zipmatch.group(1) if consignee_zipmatch else None,
#         "Distance": int(distance_match.group(1)) if distance_match else None,
#         "Weight": int(weight_match.group(1)) if weight_match else None,
#         "Equipment type": equipment_match.group(0) if equipment_match else "dry van",
#         "Hazmat": hazmat_match.group(0) if hazmat_match else "no",
#         "Extra stops": int(extra_stops_match.group(1)) if extra_stops_match else 0,
#         "Driver assistance": driver_assist_match.group(0) if driver_assist_match else "no",
#         "Storage days": int(storage_days_match.group(1)) if storage_days_match else 0
#     }

#     missing_fields = check_missing_or_unclear_fields(load_criteria)
#     if missing_fields:
#         prompt = "I couldn't extract all the necessary information. Please provide more details."
#         await ask_for_clarification(chat_id, prompt, context)
#         return ConversationState.COLLECTING_RATE_INFO

#     rate = calculate_approximate_rate_quote(db, load_criteria)
#     await context.bot.send_message(chat_id=chat_id, text=f"The estimated rate is: ${rate}")

#     # Check if the user is asking for a rate quote
#     if "rate quote" in user_message or "rate" in user_message:
#         # Prompt the user for rate quote details
#         await update.message.reply_text(
#             "Let's calculate a rate quote. Please provide the shipper's zip code.",
#             reply_markup=ReplyKeyboardRemove(),
#         )
#         context.user_data['rate_quote_info'] = {}
#         return COLLECTING_RATE_INFO

#     # For other general messages, handle using chat_with_gpt functionality
#     response = await chat_with_gpt(chat_id, user_message, task="conversation", context=context)
#     await update.message.reply_text(response)
#     return DEFAULT

# # async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
# #     user_message = update.message.text.strip()
# #     chat_id = update.effective_chat.id
# #     user_data = context.user_data  # Assuming this is where you store state information

# #     # Handling lookups
# #     if user_data.get('awaiting_lookup') or user_data.get('awaiting_mc_dot') or "lookup" in user_message.lower() or user_data.get("awaiting_number"):
# #         # This part handles various lookup scenarios
# #         lookup_result = await perform_lookup(user_message, "MC/DOT Lookup")
# #         await context.bot.send_message(lookup_result, reply_markup=ReplyKeyboardRemove())
# #         user_data['awaiting_lookup'] = False
# #         user_data['awaiting_mc_dot'] = False
# #         user_data["awaiting_number"] = False
# #         return ConversationHandler.END

#     # # Handling rate quote requests
#     # if "rate quote" in user_message or "rate" in user_message:
#     #     # Directly call chat_with_gpt_for_rate_info to handle state transition
#     #     response = await chat_with_gpt_for_rate_info(chat_id, user_message, user_data)
#     #     if response != "ok":
#     #         await update.message.reply_text(response)
#     #     return ConversationHandler.END
#     # # If state is COLLECTING_RATE_INFO, prompt for more info or calculate the rate
#     # # Define ConversationState enum if not already defined
#     # class ConversationState:
#     #     START = 0
#     #     COLLECTING_RATE_INFO = 1
#     #     CALCULATING_RATE = 2
#     #     COMPLETED = 3

# async def collect_rate_info(update, context):
#     # Prompt the user for rate quote information
#     await update.message.reply_text("Please provide rate quote details.")

# # async def calculate_rate_quote(update, context, user_data):
# #     # Calculate the rate quote based on collected information
# #     await update.message.reply_text("Calculating rate quote...")

# # def extract_load_criteria(user_message):
# #     # Extract load criteria from the user's message for rate calculation
# #     return {}

# def calculate_approximate_rate_quote(db, load_criteria: dict) -> str:
#     try:
#         # Adjust these ranges according to your definition of "similar"
#         distance_tolerance = 600  # Increase the distance tolerance to 500 miles
#         weight_tolerance = 6000  # Increase the weight tolerance to 5000 lbs

#         pipeline = [
#             {
#                 # Match historical data that is similar to the specified criteria
#                 "$match": {
#                     # "Shipper city": {"$regex": load_criteria.get("Shipper_city"), "$options": "i"},
#                     # "Shipper state": {"$regex": load_criteria.get("Shipper state"), "$options": "i"},
#                     # "Consignee city": {"$regex": load_criteria.get("Consignee city"), "$options": "i"},
#                     # "Consignee state": {"$regex": load_criteria.get("Consignee state"), "$options": "i"},"Shipper zip": load_criteria.get("Shipper zip", ""),
#                     "Consignee zip": load_criteria.get("Consignee zip", ""),
#                     "Trailer type": load_criteria.get("Equipment type", ""),
#                     "Trailer type": {"$eq": load_criteria.get("Equipment type")},  # Exact match for equipment type
#                     "Weight": {
#                         "$gte": load_criteria.get("Weight", 0) - weight_tolerance,
#                         "$lte": load_criteria.get("Weight", 0) + weight_tolerance
#                     },
#                     "Bill Distance": {
#                         "$gte": load_criteria.get("Bill distance", 0) - distance_tolerance,
#                         "$lte": load_criteria.get("Bill distance", 0) + distance_tolerance
#                     }
#                 }
#             },
#             {
#                 # Calculate the average rate of similar loads
#                 "$group": {
#                     "_id": None,
#                     "averageRate": {"$avg": "$similarRate"}
#                 }
#             }
#         ]

#         # client = MongoClient("mongodb://localhost:27017")
#         # db = client['york']
#         # collection_client = db['inventory']
#         # with open('Inventory.json') as f:
#         #     datastore = json.loads(f.read())
#         # collection_client.insert_many(datastore)

#         # Execute the aggregation pipeline
#         client = MongoClient(MONGO_CLIENT)
#         db = client['hivedb']
#         collection_client = db['hive-cx-data']
#         result = list(collection_client.aggregate(pipeline))
#         print(result)
#         # result = collection_client.aggregate(pipeline)
#         if result and 'averageRate' in result[0]:
#             try:
#                 first_result = result[0]
#                 average_similar_rate = first_result.get('averageRate', 0)
#                 message = f"The estimated rate is: ${average_similar_rate:.2f}"                    
#                 return message
#             except IndexError as e:
#                 message = 'No similar historical data found to calculate an approximate rate: {e}'
#                 return message
#             except KeyError as e:
#                 message = 'Error processing rate calculation: {e}'
#                 return message
#         else:     
#             message = "No similar historical data found to calculate an approximate rate."
#             return message
#     except Exception as e:
#         return f"Sorry, I couldn't process that due to an error: {e}"
    
# async def extract_and_calculate_rate_quote(update, context, openai_api_key):
#     user_message = update.message.text.strip()
#     chat_id = update.effective_chat.id

#     # Initial Extraction with Regex
#     load_criteria = extract_initial_load_criteria(user_message, chat_id, context)

#     # Check for missing or unclear information
#     missing_or_unclear_fields = check_missing_or_unclear_fields(load_criteria)

#     # Conversational Clarification with OpenAI API
#     if missing_or_unclear_fields:
#         for field in missing_or_unclear_fields:
#             clarification_prompt = f"Could you please provide more details about the {field.replace('_', ' ')}?"
#             user_response = await ask_for_clarification(chat_id, clarification_prompt, context, openai_api_key)
#             load_criteria[field] = user_response

#     # Aggregation and Calculation
#     rate_quote = calculate_approximate_rate_quote(context.db, load_criteria)

#     # Send the calculated rate quote to the user
#     await context.bot.send_message(chat_id=chat_id, text=f"The estimated rate is: ${rate_quote}")

# import re

# async def extract_initial_load_criteria(user_message, chat_id, context):
#     shipper_zip_pattern = r"(\d{5})"
#     consignee_zip_pattern = r"(\d{5})"
#     distance_pattern = r"(\d+)\s*miles"
#     weight_pattern = r"(\d+)\s*lbs"
#     equipment_pattern = r"dry van|flatbed|reefer|tep deck|conestoga|power only|auto carrier|double drop|lowboy|stretch|extendable|multi axle|other"
#     hazmat_pattern = r"hazmat|yes|no"
#     extra_stops_pattern = r"(\d+)\s*stops"
#     driver_assist_pattern = r"driver\s*assistance|yes|no"
#     storage_days_pattern = r"(\d+)\s*days"
    
#     shipper_zipmatch = re.search(shipper_zip_pattern, user_message)
#     consignee_zipmatch = re.search(consignee_zip_pattern, user_message)
#     distance_match = re.search(distance_pattern, user_message)
#     weight_match = re.search(weight_pattern, user_message)
#     equipment_match = re.search(equipment_pattern, user_message)
#     hazmat_match = re.search(hazmat_pattern, user_message)
#     extra_stops_match = re.search(extra_stops_pattern, user_message)
#     driver_assist_match = re.search(driver_assist_pattern, user_message)
#     storage_days_match = re.search(storage_days_pattern, user_message)

#     load_criteria = {
#         "Shipper zip": shipper_zipmatch.group(1) if shipper_zipmatch else None,
#         "Consignee zip": consignee_zipmatch.group(1) if consignee_zipmatch else None,
#         "Distance": int(distance_match.group(1)) if distance_match else None,
#         "Weight": int(weight_match.group(1)) if weight_match else None,
#         "Equipment type": equipment_match.group(0) if equipment_match else "dry van",
#         "Hazmat": hazmat_match.group(0) if hazmat_match else "no",
#         "Extra stops": int(extra_stops_match.group(1)) if extra_stops_match else 0,
#         "Driver assistance": driver_assist_match.group(0) if driver_assist_match else "no",
#         "Storage days": int(storage_days_match.group(1)) if storage_days_match else 0
#     }

#     missing_fields = check_missing_or_unclear_fields(load_criteria)
#     if missing_fields:
#         prompt = "I couldn't extract all the necessary information. Please provide more details."
#         await ask_for_clarification(chat_id, prompt, context)
#         return ConversationState.COLLECTING_RATE_INFO

#     rate = calculate_approximate_rate_quote(db, load_criteria)
#     await context.bot.send_message(chat_id=chat_id, text=f"The estimated rate is: ${rate}")

#     # Check if the user is asking for a rate quote
#     if "rate quote" in user_message or "rate" in user_message:
#         # Prompt the user for rate quote details
#         await context.bot.send_message(
#             chat_id=chat_id,
#             text="Let's calculate a rate quote. Please provide the shipper's zip code.",
#             reply_markup=ReplyKeyboardRemove(),
#         )
#         context.user_data['rate_quote_info'] = {}
#         return STATE['COLLECTING_RATE_INFO']

#     # For other general messages, handle using chat_with_gpt functionality
#     response = await chat_with_gpt(chat_id, user_message, task="conversation", context=context)
#     await context.bot.send_message(chat_id=chat_id, text=response)
    
# async def chat_with_gpt(user_id, user_message, task="conversation", context=None):
#     # let the user know the bot is typing
#     await context.bot.send_chat_action(chat_id=user_id, action='TYPING')
    
#     history = get_conversation_history(user_id)
#     history.append({"role": "user", "content": user_message})

#     # Convert each message content to string and then join
#     content_history = " ".join([msg.get('content', '') for msg in history])

#     # Truncate history if it's too long
#     while len(content_history) > MAX_TOKENS_LIMIT:
#         history.pop(0)
#         content_history = " ".join([msg.get('content', '') for msg in history])

#     try:
#         response = gpt_client.chat.completions.create(
#             model="gpt-4-1106-preview",
#             messages=history,
#             max_tokens=200,
#             stop=None if task == "conversation" else ["\n"]  # Adjust stopping condition based on the task
#         )

#         # Extract the text response and update history
#         gpt_response = response.choices[0].message.content if response.choices else ""
        
#         # Update conversation history for general conversation
#         if task == "conversation":
#             update_conversation_history(user_id, user_message, gpt_response)

#         return gpt_response
#     except Exception as e:
#         logger.error(f"Error in chat_with_gpt: {e}")
#         return "I'm having trouble understanding that. Could you rephrase or ask something else?"
    
    # Define regex patterns for each field
    # patterns = {
    #     "shipper_zip": r"Shipper zip: (\w+)",
    #     # Add more patterns for other fields
    # }
    
    # # Attempt to extract information using regex
    # extracted_criteria = {}
    # for field, pattern in patterns.items():
    #     match = re.search(pattern, message, re.IGNORECASE)
    #     if match:
    #         extracted_criteria[field] = match.group(1)
    #     else:
    #         extracted_criteria[field] = None  # Mark as missing for later clarification
    
    # return extracted_criteria

# def check_missing_or_unclear_fields(load_criteria):
#     # Identify fields that are missing or need clarification
#     return [field for field, value in load_criteria.items() if value is None]

# async def ask_for_clarification(chat_id, prompt, context):
#     # Use OpenAI API to ask the user for clarification
#     await context.bot.send_message(chat_id=chat_id, text=prompt)
#     # Here, you would need to handle user response capture. This could be done through a follow-up handler that waits for the next user message.
    
#     # Placeholder for user response handling
#     user_response = "user response here"
#     return user_response
    
# # async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
# #     user_message = update.message.text.strip()
# #     chat_id = update.effective_chat.id
    
# #     if context.user_data.get('awaiting_lookup'):
# #         # Perform the lookup with the provided number
# #         lookup_result = await perform_lookup(user_message, "MC/DOT Lookup")
# #         await update.message.reply_text(lookup_result, reply_markup=ReplyKeyboardRemove())
# #         context.user_data['awaiting_lookup'] = False
# #         return ConversationHandler.END
# #      # let the user know the bot is typing
# #     await context.bot.send_chat_action(chat_id=chat_id, action='TYPING')

# #     # If the message is too general, ask for more details
# #     if user_message.strip() in ["rate", "rate quote", "rate me", "quote", "/rate"]:
# #             await context.bot.send_message(chat_id=chat_id, text="Sure let's calculate a rate quote, please provide these details about the load: both the shipper and consignee's city, state, distance, weight, equipment type, hazmat(yes/no), extra stops, driver assistance, and storage days.")
# #             return ConversationState.COLLECTING_RATE_INFO

# #     # Regular expressions to extract information
# #     # city_state_pattern = r"(?P<city>[a-zA-Z\s]+),\s*(?P<state>[a-zA-Z\s]+)"
# #     # shipper_city_pattern = r"(?P<shipper_city>[a-zA-Z\s]+)"
# #     # shipper_state_pattern = r"(?P<shipper_state>[a-zA-Z\s]+)"
# #     # consignee_city_pattern = r"(?P<consignee_city>[a-zA-Z\s]+)"
# #     # consignee_state_pattern = r"(?P<consignee_state>[a-zA-Z\s]+)"
# #     shipper_zip_pattern = r"(\d{5})"
# #     consignee_zip_pattern = r"(\d{5})"
# #     distance_pattern = r"(\d+)\s*miles"
# #     weight_pattern = r"(\d+)\s*lbs"
# #     equipment_pattern = r"dry van|flatbed|reefer|tep deck|conestoga|power only|auto carrier|double drop|lowboy|stretch|extendable|multi axle|other"
# #     hazmat_pattern = r"hazmat|yes|no"
# #     extra_stops_pattern = r"(\d+)\s*stops"
# #     driver_assist_pattern = r"driver\s*assistance|yes|no"
# #     storage_days_pattern = r"(\d+)\s*days"
    
# #        # Try extracting information using regex
# #     # shipper_city_match = re.search(shipper_city_pattern, user_message)
# #     # shipper_state_match = re.search(shipper_state_pattern, user_message)
# #     # consignee_city_match = re.search(consignee_city_pattern, user_message)
# #     # consignee_state_match = re.search(consignee_state_pattern, user_message)
# #     shipper_zipmatch = re.search(shipper_zip_pattern, user_message)
# #     consignee_zipmatch = re.search(consignee_zip_pattern, user_message)
# #     distance_match = re.search(distance_pattern, user_message)
# #     weight_match = re.search(weight_pattern, user_message)
# #     equipment_match = re.search(equipment_pattern, user_message)
# #     hazmat_match = re.search(hazmat_pattern, user_message)
# #     extra_stops_match = re.search(extra_stops_pattern, user_message)
# #     driver_assist_match = re.search(driver_assist_pattern, user_message)
# #     storage_days_match = re.search(storage_days_pattern, user_message)

# #     load_criteria = {
# #         "Shipper zip": shipper_zipmatch.group(1) if shipper_zipmatch else None,
# #         "Consignee zip": consignee_zipmatch.group(1) if consignee_zipmatch else None,
# #         "Distance": int(distance_match.group(1)) if distance_match else None,
# #         "Weight": int(weight_match.group(1)) if weight_match else None,
# #         "Equipment type": equipment_match.group(0) if equipment_match else "dry van",  # Default to dry van if not specified
# #         "Hazmat": hazmat_match.group(0) if hazmat_match else "no",  # Default to no if not specified
# #         "Extra stops": int(extra_stops_match.group(1)) if extra_stops_match else 0,  # Default to 0 if not specified
# #         "Driver assistance": driver_assist_match.group(0) if driver_assist_match else "no",  # Default to no if not specified
# #         "Storage days": int(storage_days_match.group(1)) if storage_days_match else 0  # Default to 0 if not specified
# #     }

# #     missing_fields = check_missing_or_unclear_fields(load_criteria)
# #     if missing_fields:
# #         prompt = "I couldn't extract all the necessary information. Please provide more details."
# #         await ask_for_clarification(chat_id, prompt, context)
# #         return ConversationState.COLLECTING_RATE_INFO

# #     rate = calculate_approximate_rate_quote(db, load_criteria)
# #     await context.bot.send_message(chat_id=chat_id, text=f"The estimated rate is: ${rate}")

# def extract_city_state_from_gpt_response(gpt_response):
#     print("GPT-4 response:", gpt_response)
#     # Implement logic to extract city from GPT-4 response
#     # Example (you need to adapt this based on actual GPT-4 response):
#     matches = re.findall(r"(Consignee|Shipper)|(City|State): (\w+)", gpt_response or "")
#     cities = [match[2] for match in matches]
#     return cities if cities else None
    

# # Define the states for the conversation
# class ConversationState:
#     START = 0
#     COLLECTING_RATE_INFO = 1
#     CALCULATING_RATE = 2
#     COMPLETED = 3

# async def lookup_command(update: Update, context: CallbackContext) -> int:
#     # Check if user is verified; assuming verification status is stored in user_data or a database
#     if context.user_data.get('verified', False):  # or any other logic to check verification
#         await update.message.reply_text(
#             'Please enter the MC/DOT number you wish to lookup.',
#             reply_markup=ReplyKeyboardRemove(),
#         )
#         context.user_data['awaiting_lookup'] = True
#         return STATE['LOOKUP']
#     else:
#        await update.message.reply_text(
#            'You need to verify your MC/DOT number first. Please use /start to verify.',
#            reply_markup=ReplyKeyboardRemove(),
#         )
#        return ConversationHandler.END

# extract_mc_dot_number = lambda message: re.search(r"\b(?:MC|DOT)\s*#?\s*(\d+)", message, re.IGNORECASE).group(1)

# async def handle_mc_dot_lookup(user_message):
#     # Extract MC/DOT number from the message
#     mc_number = extract_mc_dot_number(user_message)

#     # Perform the lookup using HSPCA API
#     response = requests.get(f"https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{mc_number}?webKey={FMCSA_API_KEY}")
#     print(response.json())
    
#     if response.status_code == 200 and response.json()["content"]:
#         return {'status': 'ask', 'verified': True, 'message': 'MC/DOT number verified successfully.', 'data': response.json()["content"]}
#     else:
#         return {'status': 'not_verified', 'verified': False, 'message': 'MC info not found. Please re-enter an MC or DOT number.'} 
#     # if response.status_code == 200 and response.json()["content"]:
#     #     # Check the conditions
#     #     if response.json()['content'][0]:
#     #         return {'status': 'ask', 'message': 'MC/DOT number verified.', 'data': response.json()["content"]}
#     #     else:
#     #         return {'status': 'not_verified', 'message': 'MC info not found. Please re-enter an MC or DOT number.'}
                    
# def error_handler(update, context):
#     """Handle any errors that occur."""
#     logger.error(f"Update {update} caused error {context.error}")
#     update.message.reply_text('Sorry, an error occurred. Let’s try something else.')
    
# def error(update: Update, context: CallbackContext):
#     logger.warning(f'Update "{update}" caused error "{context.error}"')
    
# async def verify_state_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     # Logic for the VERIFY state
#     # Provide options or guide the user to the next step
#     await update.message.reply_text("Verification complete. How can I assist you further?")
#     return VERIFY  # Or transition to a different state if needed

# def timeout(update, context):
#     """End the conversation after a timeout."""
#     update.message.reply_text('Session timed out. Please start again.')
#     return DEFAULT  # Instead of ending the conversation
#     # return ConversationHandler.END
    
# async def default_handler(update, context):
#     """Handle other messages that don't fit into the above categories."""
#     user_message = update.message.text

#     # Use OpenAI API to generate a natural language response
#     response = await chat_with_gpt(user_message)

#     # Reply to the user with the generated response
#     await update.message.reply_text(response)

#     # Allow the user to initialize other commands in this state
#     return DEFAULT  # Instead of ending the conversation
#     # return ConversationHandler.END

# def end_conversation(update, context):
#     """End the conversation gracefully."""
#     update.message.reply_text('Thank you for using Hive-Bot. Have a great day!')
#     return DEFAULT  # Instead of ending the conversation
#     # return ConversationHandler.END

# async def main():
#     # Create the Application instance
#     application = Application.builder().token(os.environ["TELEGRAM_API_KEY"]).build()

#     # Add the conversation handler to the application
#     application.add_handler(conv_handler)

#     # Run the bot
#     await application.run_polling()
# if __name__ == '__main__':
#     try:
#         # Initialize the application
#         application = Application.builder().token(os.environ["TELEGRAM_API_KEY"]).build()

#         # Handlers
#         start_command_handler = CommandHandler('start', start_command)
#         text_message_handler = MessageHandler(filters.TEXT, text_message)
#         lookup_mc_dot_handler = MessageHandler(filters.Regex(r"MC|DOT"), lookup)
#         lookup_command_handler = CommandHandler('lookup', lookup_command)
#         ask_db_command_handler = CommandHandler('chatdb', ask_db_command)
#         rate_quote_command_handler = CommandHandler('rate', rate_quote_command)
        

#         # Conversation handler setup
#         conv_handler = ConversationHandler(
#             # name="Hive Bot Conversation",
#             allow_reentry=True,
#             # persistent=True,
#             entry_points=[CommandHandler('start', start_command)],
#             states={
#                 NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_number)],
#                 CONFIRM_COMPANY: [MessageHandler(filters.Regex('^(YES|NO)$'), confirm_company)],
#                 LOOKUP: [MessageHandler(filters.Regex('^(MC Lookup|DOT Lookup)$'), lookup_choice)],
#                 COLLECTING_RATE_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, extract_and_calculate_rate_quote)],
#                 REENTER_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, reenter_number)],
#                 VERIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_state_handler)],
#                 GENERAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_message)],
#                 DEFAULT: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_message)],  # New state
#             },
#             fallbacks=[CommandHandler('cancel', cancel), CommandHandler('end', end_conversation)],
#             conversation_timeout=300,
#         )
        
#         # Adding handlers to the application
#         application.add_handler(conv_handler)
#         application.add_handler(lookup_mc_dot_handler)
#         application.add_handler(start_command_handler)
#         application.add_handler(text_message_handler)  
#         application.add_handler(lookup_command_handler)
#         application.add_handler(ask_db_command_handler)
#         application.add_handler(rate_quote_command_handler)
#         # application.add_error_handler(error_handler)
#         # application.add_handler(timeout)
#         # Run the bot and Flask app
#         asyncio.get_event_loop().create_task(application.run_polling())
#     except Exception as e:
#         print(f"An error occurred: {e}")
#         logger.error(f"An error occurred: {e}")
#         #  # Run the bot until the user presses Ctrl-C
#     asyncio.run(main())
    

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
        "Hi, welcome to Hive-Bot! Please enter your MC or DOT number to get started.",
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
    # shipper_zip_pattern = r"(\d{5})"
    # consignee_zip_pattern = r"(\d{5})"
    # distance_pattern = r"(\d+)\s*miles"
    # weight_pattern = r"(\d+)\s*lbs"
    # equipment_pattern = r"dry van|flatbed|reefer|tep deck|conestoga|power only|auto carrier|double drop|lowboy|stretch|extendable|multi axle|other"
    # hazmat_pattern = r"hazmat|yes|no"
    # extra_stops_pattern = r"(\d+)\s*stops"
    # driver_assist_pattern = r"driver\s*assistance|yes|no"
    # storage_days_pattern = r"(\d+)\s*days"
    
    # shipper_zipmatch = re.search(shipper_zip_pattern, user_message)
    # consignee_zipmatch = re.search(consignee_zip_pattern, user_message)
    # distance_match = re.search(distance_pattern, user_message)
    # weight_match = re.search(weight_pattern, user_message)
    # equipment_match = re.search(equipment_pattern, user_message)
    # hazmat_match = re.search(hazmat_pattern, user_message)
    # extra_stops_match = re.search(extra_stops_pattern, user_message)
    # driver_assist_match = re.search(driver_assist_pattern, user_message)
    # storage_days_match = re.search(storage_days_pattern, user_message)

    # load_criteria = {
    #     "Shipper zip": shipper_zipmatch.group(1) if shipper_zipmatch else None,
    #     "Consignee zip": consignee_zipmatch.group(1) if consignee_zipmatch else None,
    #     "Distance": int(distance_match.group(1)) if distance_match else None,
    #     "Weight": int(weight_match.group(1)) if weight_match else None,
    #     "Equipment type": equipment_match.group(0) if equipment_match else "dry van",
    #     "Hazmat": hazmat_match.group(0) if hazmat_match else "no",
    #     "Extra stops": int(extra_stops_match.group(1)) if extra_stops_match else 0,
    #     "Driver assistance": driver_assist_match.group(0) if driver_assist_match else "no",
    #     "Storage days": int(storage_days_match.group(1)) if storage_days_match else 0
    # }

    # missing_fields = check_missing_or_unclear_fields(load_criteria)
    # if not missing_fields:
    #     # Directly proceed to calculate the rate quote
    #     rate_quote = await calculate_approximate_rate_quote(db, load_criteria, update, context)
    #     await update.message.reply_text(rate_quote, reply_markup=ReplyKeyboardRemove())
    #     return ConversationHandler.END
    # else: # If there are missing fields, ask for more details
    #     prompt = "I couldn't extract all the necessary information. Please provide more details."
    #     await ask_for_clarification(chat_id, prompt, context)
    #     rate = calculate_approximate_rate_quote(db, load_criteria, update, context)
    # await context.bot.send_message(chat_id=chat_id, text=f"The estimated rate is: ${rate}")

    # # Check if the user is asking for a rate quote
    # if "rate quote" in user_message or "rate" in user_message:
    #     # Prompt the user for rate quote details
    #     await update.message.reply_text(
    #         "Let's calculate a rate quote. Please provide the shipper's zip code.",
    #         reply_markup=ReplyKeyboardRemove(),
    #     )
    #     context.user_data['rate_quote_info'] = {}
    #     return STATE['COLLECTING_RATE_INFO']
    
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
        extra_drops = int(load_criteria.get("Extra drops", 0))

        # Convert load criteria values to integers
        load_criteria["Shipper zip"] = str(load_criteria["Shipper zip"])  # Example conversion
        load_criteria["Consignee zip"] = float(load_criteria["Consignee zip"])  # Example conversion
        load_criteria["Bill Distance"] = float(load_criteria["Bill Distance"])  # Example conversion
        load_criteria["Weight"] = float(load_criteria["Weight"])  # Example conversion
        load_criteria["Extra drops"] = float(load_criteria["Extra drops"])  # Example conversion
        print("values post pipeline --->", load_criteria)
        
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
                    "Extra drops": load_criteria["Extra drops"]
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
    shipper_zip_pattern = r"shipper zip (\d{5})|shipper (\d{5})|shipper's zip (\d{5})|shipper's (\d{5})|shipper zip code (\d{5})|shipper zip code is (\d{5})|shipper zip code: (\d{5})|shipper's zip code (\d{5})|shipper's zip code is (\d{5})|shipper's zip code: (\d{5})|shipper's zip code = (\d{5})|shipper zip (\d{5})|shipper (\d{5})|shipper's zip (\d{5})|shipper's (\d{5})|shipper zip code (\d{5})|shipper zip code is (\d{5})|shipper zip code: (\d{5})|shipper's zip code (\d{5})|shipper's zip code is (\d{5})|shipper's zip code: (\d{5})|shipper's zip code = (\d{5})|shipper zip (\d{5})|shipper (\d{5})|shipper's zip (\d{5})|shipper's (\d{5})|shipper zip code (\d{5})|shipper zip code is (\d{5})|shipper zip code: (\d{5})|shipper's zip code (\d{5})|shipper's zip code is (\d{5})|shipper's zip code: (\d{5})|shipper's zip code = (\d{5})|shipper zip (\d{5})|shipper (\d{5})|shipper's zip (\d{5})|shipper's (\d{5})|shipper zip code (\d{5})|shipper zip code is (\d{5})|shipper zip code: (\d{5})|shipper's zip code (\d{5})|shipper's zip code is (\d{5})|shipper's zip code: (\d{5})|shipper's zip code = (\d{5})"
    consignee_zip_pattern = r"consignee zip (\d{5})|consignee (\d{5})|consignee's zip (\d{5})|consignee's (\d{5})|consignee zip code (\d{5})|consignee zip code is (\d{5})|consignee zip code: (\d{5})|consignee's zip code (\d{5})|consignee's zip code is (\d{5})|consignee's zip code: (\d{5})|consignee's zip code = (\d{5})|consignee zip (\d{5})|consignee (\d{5})|consignee's zip (\d{5})|consignee's (\d{5})|consignee zip code (\d{5})|consignee zip code is (\d{5})|consignee zip code: (\d{5})|consignee's zip code (\d{5})|consignee's zip code is (\d{5})|consignee's zip code: (\d{5})|consignee's zip code = (\d{5})|consignee zip (\d{5})|consignee (\d{5})|consignee's zip (\d{5})|consignee's (\d{5})|consignee zip code (\d{5})|consignee zip code is (\d{5})|consignee zip code: (\d{5})|consignee's zip code (\d{5})|consignee's zip code is (\d{5})|consignee's zip code: (\d{5})|consignee's zip code = (\d{5})|consignee zip (\d{5})|consignee (\d{5})|consignee's zip (\d{5})|consignee's (\d{5})|consignee zip code (\d{5})|consignee zip code is (\d{5})|consignee zip code: (\d{5})|consignee's zip code (\d{5})|consignee's zip code is (\d{5})|consignee's zip code: (\d{5})|consignee's zip code = (\d{5})|consignee zip (\d{5})|consignee (\d{5})|consignee's zip (\d{5})|consignee's (\d{5})|consignee zip code (\d{5})|consignee zip code is (\d{5})|consignee zip code: (\d{5})|consignee's zip code (\d{5})|consignee's zip code is (\d{5})|consignee's zip code: (\d{5})|consignee's zip code = (\d{5})"
    distance_pattern = r"distance(?: is|:| -| from| of| =)? (\d+) miles|distance (\d+) miles"
    weight_pattern = r"weight(?: in|:| -| from| of| =)? (\d+) lbs|weight (\d+) lbs"
    # equipment_pattern = r"equipment(?: type is|:| -| from| of| =)? (dry van|flatbed|reefer|tep deck|conestoga|power only|auto carrier|double drop|lowboy|stretch|extendable|multi axle|other)"
    # hazmat_pattern = r"hazmat(?: is|:| -| from| of| =)? (yes|no)"
    # storage_days_pattern = r"storage days(?: is|:| -| from| of| =)? (\d+)"
    extra_stops_pattern = r"(?:\d+ )?extra (?:stops|drops)(?:[: -]? (\d+))?"
    # driver_assist_pattern = r"driver assistance|driver assistance: (yes|no)|driver assistance - (yes|no)|driver assistance from (yes|no)|driver assistance of (yes|no)|driver assistance = (yes|no)|driver assistance is (yes|no)|driver assistance (yes|no)|driver assistance: (yes|no)|driver assistance - (yes|no)|driver assistance from (yes|no)|driver assistance of (yes|no)|driver assistance = (yes|no)|driver assistance is (yes|no)"
    
    # Use regex searches to fill the dictionary
    load_criteria['Shipper zip'] = re.search(shipper_zip_pattern, user_message, re.IGNORECASE).group(1) if re.search(shipper_zip_pattern, user_message) else None
    load_criteria['Consignee zip'] = int(re.search(consignee_zip_pattern, user_message, re.IGNORECASE).group(1)) if re.search(consignee_zip_pattern, user_message) else 00000
    load_criteria['Bill Distance'] = int(re.search(distance_pattern, user_message, re.IGNORECASE).group(1)) if re.search(distance_pattern, user_message) else None
    load_criteria['Weight'] = int(re.search(weight_pattern, user_message, re.IGNORECASE).group(1)) if re.search(weight_pattern, user_message) else None
    # load_criteria['Hazmat routing'] = "Yes" if re.search(hazmat_pattern, user_message, re.IGNORECASE) and re.search(hazmat_pattern, user_message).group(1).lower() == "yes" else "No"
    load_criteria['Extra drops'] = int(re.search(extra_stops_pattern, user_message, re.IGNORECASE).group(1)) if re.search(extra_stops_pattern, user_message) else 0
    # load_criteria['Weight'] = int(re.search(weight_pattern, user_message).group(1)) if re.search(weight_pattern, user_message) else None
    # load_criteria['Trailer type'] = re.search(equipment_pattern, user_message, re.IGNORECASE).group(1) if re.search(equipment_pattern, user_message) else None
    # load_criteria['Hazmat routing'] = re.search(hazmat_pattern, user_message, re.IGNORECASE).group(1) if re.search(hazmat_pattern, user_message) else "No"
    # load_criteria['Storage days'] = re.search(storage_days_pattern, user_message).group(1) if re.search(storage_days_pattern, user_message) else None
    # load_criteria['Extra drops'] = int(re.search(extra_stops_pattern, user_message, re.IGNORECASE).group(1)) if re.search(extra_stops_pattern, user_message) else "No"
    # load_criteria['Driver assistance'] = re.search(driver_assist_pattern, user_message, re.IGNORECASE).group(1) if re.search(driver_assist_pattern, user_message) else None
    
    # Now that we have extracted load criteria, calculate the rate quote.
    await context.bot.send_message(chat_id=chat_id, text=f"I understand your load criteria is: {load_criteria}, please wait while I run some advanced calculations and analysis...")

    
    shipper_zipmatch = re.search(shipper_zip_pattern, user_message)
    consignee_zipmatch = re.search(consignee_zip_pattern, user_message)
    distance_match = re.search(distance_pattern, user_message)
    weight_match = re.search(weight_pattern, user_message)
    # equipment_match = re.search(equipment_pattern, user_message)
    # hazmat_match = re.search(hazmat_pattern, user_message)
    extra_stops_match = re.search(extra_stops_pattern, user_message)
    # driver_assist_match = re.search(driver_assist_pattern, user_message)
    # storage_days_match = re.search(storage_days_pattern, user_message)

    load_criteria = {
        "Shipper zip": str(shipper_zipmatch.group(1)) if shipper_zipmatch else None,
        "Consignee zip": int(consignee_zipmatch.group(1)) if consignee_zipmatch else None,
        "Bill Distance": int(distance_match.group(1)) if distance_match else None,
        "Weight": int(weight_match.group(1)) if weight_match else None,
        # "Trailer type": equipment_match.group(0) if equipment_match else "V",
        # "Hazmat routing": hazmat_match.group(0) if hazmat_match else "No",
        "Extra drops": int(extra_stops_match.group(1)) if extra_stops_match else 0,
        # "Driver assistance": driver_assist_match.group(0) if driver_assist_match else "no",
        # "Storage days": int(storage_days_match.group(1)) if storage_days_match else 0
    }
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
        await ask_for_clarification(chat_id, "Please provide more details.", context)
        return STATE['COLLECTING_RATE_INFO']

    # Aggregation and Calculation
    rate_quote = await calculate_approximate_rate_quote(db, load_criteria, update, context)

    # Send the calculated rate quote to the user
    await context.bot.send_message(chat_id=chat_id, text=f"The estimated rate is: ${rate_quote}")
    return STATE['DEFAULT']

# Error handler
def error(update: Update, context: CallbackContext):
    logger.warning(f'Update "{update}" caused error "{context.error}"')

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
    application.add_error_handler(error)
    application.add_handler(start_command_handler)
    application.add_handler(text_message_handler)
    application.add_handler(lookup_mc_dot_handler)
    application.add_handler(lookup_command_handler)
    application.add_handler(ask_db_command_handler)
    application.add_handler(rate_quote_command_handler)
    application.add_handler(sending_rate_quote_handler)
    
    application.run_polling()


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
