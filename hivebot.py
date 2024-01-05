from telegram.ext import Application, CommandHandler, MessageHandler, filters
import os
import asyncio

async def start_command(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Hello, welcome to Hive-Bot. How can I help you today?')

async def text_message(update, context):
    response = 'I understood your message: ' + update.message.text
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