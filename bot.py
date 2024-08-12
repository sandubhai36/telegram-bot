from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import logging
import os
import random
import time

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = '7076788390:AAG1vOxSaTMDSI3kEPYtqzEpIXFFrlvvbAo'
CHANNEL_ID = 'cryptocombat2'  # Remove '@'
PROMOCODE_FILE = 'promocode.txt'
FEEDBACK_FILE = 'feedback.txt'
USER_KEYS = {}
USER_REQUESTS = {}
ADMIN_IDS = [5841579466]
KEYS_PER_CLICK = 4  # Provide 4 keys at once

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.message.chat_id
        bot = context.bot

        # Send message with subscription button
        keyboard = [[InlineKeyboardButton("📢 Subscribe to Channel", url=f"https://t.me/{CHANNEL_ID}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await bot.send_message(chat_id, "To receive your keys, please subscribe to our channel using the button below.", reply_markup=reply_markup)

        # After sending the subscribe message, send a button for the user to verify their subscription
        verify_button = [[InlineKeyboardButton("✅ Verify Subscription", callback_data='verify_subscription')]]
        verify_reply_markup = InlineKeyboardMarkup(verify_button)
        await bot.send_message(chat_id, "Once subscribed, click the button below to verify your subscription.", reply_markup=verify_reply_markup)
    except Exception as e:
        logging.error(f"Error in start command: {e}")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        bot = context.bot

        if query.data == 'verify_subscription':
            if await check_subscription(bot, user_id):
                keyboard = [[InlineKeyboardButton("🔑 Get Your Keys", callback_data='get_key')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await bot.send_message(chat_id, "You are now subscribed! Click below to get your keys.", reply_markup=reply_markup)
            else:
                await bot.send_message(chat_id, "You need to subscribe to the channel to access the keys.")

        elif query.data == 'get_key':
            if await check_subscription(bot, user_id):
                if can_request_key(user_id):
                    keys = get_keys(user_id)
                    if keys:
                        key_list = "\n".join(keys)
                        await bot.send_message(chat_id, f"Here are your keys:\n{key_list}")
                        log_request(user_id)
                    else:
                        await bot.send_message(chat_id, "🔒 All keys have been used up. Please wait for a while to get new keys.")
                else:
                    await bot.send_message(chat_id, "🕒 You have already received your keys. Please try again after 24 hours.")
            else:
                await bot.send_message(chat_id, "You need to subscribe to the channel to access the keys.")

        await query.answer()  # Important to acknowledge callback queries
    except Exception as e:
        logging.error(f"Error in button callback: {e}")

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
    return len(USER_REQUESTS[user_id]) < 1  # User can only click once in 24 hours

async def add_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id

        if user_id not in ADMIN_IDS:
            await update.message.reply_text("🚫 You are not authorized to use this command.")
            return

        if not context.args:
            await update.message.reply_text("ℹ️ Usage: /add_promocode <promocode>")
            return

        promocode = ' '.join(context.args)
        with open(PROMOCODE_FILE, 'a') as file:
            file.write(f"{promocode}\n")
        await update.message.reply_text(f"✅ Promo code '{promocode}' has been added.")
    except Exception as e:
        logging.error(f"Error adding promocode: {e}")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        bot = context.bot

        if await check_subscription(bot, user_id):
            keyboard = [[InlineKeyboardButton("🔑 Get Your Keys", callback_data='get_key')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("✅ You are subscribed! Click below to get your keys.", reply_markup=reply_markup)
        else:
            await update.message.reply_text("❗ Please subscribe to the channel to get your keys.")
    except Exception as e:
        logging.error(f"Error in subscribe command: {e}")

async def show_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        promocodes = load_promocodes()
        remaining_keys = len(promocodes)
        if remaining_keys > 0:
            await update.message.reply_text(f"🗝️ Total remaining keys: {remaining_keys}")
        else:
            await update.message.reply_text("🔒 No keys available. Please upload a new promocode file.")
    except Exception as e:
        logging.error(f"Error showing keys: {e}")

async def upload_promocodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id

        if user_id not in ADMIN_IDS:
            await update.message.reply_text("🚫 You are not authorized to use this command.")
            return

        if update.message.document:
            file = update.message.document
            file_id = file.file_id
            new_file = await context.bot.get_file(file_id)
            file_path = f"/tmp/{file.file_path.split('/')[-1]}"
            
            await new_file.download_to_drive(file_path)
            
            # Process the uploaded file
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Backup old promocode file and replace it with the new one
            if os.path.exists(PROMOCODE_FILE):
                os.rename(PROMOCODE_FILE, f"{PROMOCODE_FILE}.bak")

            with open(PROMOCODE_FILE, 'w') as f:
                f.write(content)
            
            await update.message.reply_text("✅ Promo codes have been updated successfully.")
    except Exception as e:
        logging.error(f"Error uploading promocodes: {e}")

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        feedback_text = ' '.join(context.args)
        
        if not feedback_text:
            await update.message.reply_text("ℹ️ Usage: /feedback <your feedback>")
            return

        with open(FEEDBACK_FILE, 'a') as file:
            file.write(f"User {user_id}: {feedback_text}\n")
        
        await update.message.reply_text("✅ Thank you for your feedback!")
    except Exception as e:
        logging.error(f"Error processing feedback: {e}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("🚫 You are not authorized to use this command.")
            return

        total_keys = len(load_promocodes())
        total_users = len(USER_KEYS)
        total_requests = sum(len(requests) for requests in USER_REQUESTS.values())
        
        stats_message = (
            f"📊 **Bot Statistics**\n\n"
            f"Total Keys: {total_keys}\n"
            f"Total
