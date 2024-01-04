from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
updater = Updater(token='ВАШ API КЛЮЧ') # Telegram Bot API key
dispatcher = updater.dispatcher

def startCommand(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='Hello, welcome to Hive-Bot. How can I help you today?')
def textMessage(bot, update):
    response = 'I understood your message: ' + update.message.text
    bot.send_message(chat_id=update.message.chat_id, text=response)
    
    # Handlers
start_command_handler = CommandHandler('start', startCommand)
text_message_handler = MessageHandler(Filters.text, textMessage)
# Adding handlers to the dispatcher
dispatcher.add_handler(start_command_handler)
dispatcher.add_handler(text_message_handler)
# Let's start looking for updates
updater.start_polling(clean=True)
# Stop Hive chat at any time by pressing Ctrl + C
updater.idle()