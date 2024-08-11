from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import logging
import os
import random
import time

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Configuration
TOKEN = '7076788390:AAG1vOxSaTMDSI3kEPYtqzEpIXFFrlvvbAo'  # Replace with your bot token
CHANNEL_ID = 'https://t.me/cryptocombat2'  # Replace with your channel ID without '@'
PROMOCODE_FILE = 'promocode.txt'
USER_KEYS = {}
USER_REQUESTS = {}  # To track user requests and timestamps
ADMIN_ID = 5841579466  # Replace with your Telegram user ID
CO_ADMINS = set()  # Store co-admin IDs here

MAX_KEYS_PER_DAY = 4
TIME_LIMIT = 24 * 60 * 60  # 24 hours in seconds
KEYS_PER_CLICK = 4  # Provide 4 keys at once

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    bot = context.bot

    # Send message with subscription button
    keyboard = [[InlineKeyboardButton("🔔 Subscribe", url=f"https://t.me/cryptocombat2}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(chat_id, "Please subscribe to the channel to get your key 🔑.", reply_markup=reply_markup)

    # Verification button
    verify_button = [[InlineKeyboardButton("✅ Verify Subscription", callback_data='verify_subscription')]]
    verify_reply_markup = InlineKeyboardMarkup(verify_button)
    await bot.send_message(chat_id, "After subscribing, click the button below to verify your subscription.", reply_markup=verify_reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    bot = context.bot

    if query.data == 'verify_subscription':
        if await check_subscription(bot, user_id):
            keyboard = [[InlineKeyboardButton("🎁 Get Key", callback_data='get_key')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await bot.send_message(chat_id, "You are subscribed! Click below to receive your keys 🎁.", reply_markup=reply_markup)
        else:
            await bot.send_message(chat_id, "You need to subscribe to the channel to get the keys 🚫.")

    elif query.data == 'get_key':
        if await check_subscription(bot, user_id):
            if can_request_key(user_id):
                keys = get_keys(user_id)
                if keys:
                    key_list = "\n".join(keys)
                    await bot.send_message(chat_id, f"Here are your keys:\n{key_list}")
                    log_request(user_id)
                else:
                    await bot.send_message(chat_id, "All keys have been used up. Please try again later ⏳.")
            else:
                await bot.send_message(chat_id, "You have already received your keys. Please try again after 24 hours 🕒.")
        else:
            await bot.send_message(chat_id, "You need to subscribe to the channel to get the keys 🚫.")

    await query.answer()  # Acknowledge callback queries

async def check_subscription(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_ID}", user_id=user_id)
        logging.info(f"Checked subscription for user {user_id}: {member.status}")
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Error checking subscription for user {user_id}: {e}")
        return False

def load_promocodes():
    if os.path.exists(PROMOCODE_FILE):
        with open(PROMOCODE_FILE, 'r') as file:
            return file.read().splitlines()
    return []

def get_keys(user_id):
    promocodes = load_promocodes()
    if not promocodes:
        return []

    available_keys = [code for code in promocodes if code not in USER_KEYS.get(user_id, [])]
    if available_keys:
        keys = []
        for _ in range(KEYS_PER_CLICK):
            if available_keys:
                key = random.choice(available_keys)
                keys.append(key)
                available_keys.remove(key)
                USER_KEYS.setdefault(user_id, []).append(key)  # Assign all keys at once
            else:
                break
        
        # Update the promocode file after keys are issued
        with open(PROMOCODE_FILE, 'w') as file:
            for code in available_keys:
                file.write(f"{code}\n")
        
        return keys
    return []

def log_request(user_id):
    current_time = time.time()
    USER_REQUESTS[user_id] = [current_time]

def can_request_key(user_id):
    if user_id not in USER_REQUESTS:
        return True
    log_request(user_id)  # Clean old requests
    return len(USER_REQUESTS[user_id]) < 1  # User can only click once in 24 hours

async def add_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /add_promocode <promocode>")
        return

    promocode = ' '.join(context.args)
    with open(PROMOCODE_FILE, 'a') as file:
        file.write(f"{promocode}\n")
    await update.message.reply_text(f"Promo code '{promocode}' added.")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    bot = context.bot

    if await check_subscription(bot, user_id):
        keyboard = [[InlineKeyboardButton("🎁 Get Key", callback_data='get_key')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("You are subscribed! Click below to get your keys 🎁.", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Please subscribe to the channel to get the keys 🚫.")

async def show_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promocodes = load_promocodes()
    remaining_keys = len(promocodes)
    if remaining_keys > 0:
        await update.message.reply_text(f"Total remaining keys: {remaining_keys} 🔑")
    else:
        await update.message.reply_text("No keys available at the moment. Please wait a while before trying again ⏳.")

async def upload_promocodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        file = update.message.document
        file_id = file.file_id
        file.download(f'./{file_id}.txt')  # Download file with unique name

        with open(f'./{file_id}.txt', 'r') as f:
            promocodes = f.read().splitlines()

        with open(PROMOCODE_FILE, 'a') as f:
            f.writelines('\n'.join(promocodes) + '\n')
        
        os.remove(f'./{file_id}.txt')  # Clean up the file after processing
        await update.message.reply_text("Promo codes have been uploaded and saved.")

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler('add_promocode', add_promocode))
    application.add_handler(CommandHandler('subscribe', subscribe))
    application.add_handler(CommandHandler('show_keys', show_keys))
    application.add_handler(MessageHandler(filters.Document.ALL, upload_promocodes))

    application.run_polling()

if __name__ == '__main__':
    main()
