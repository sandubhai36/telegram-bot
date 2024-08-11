from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import logging
import os
import random
import time

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Bot and Channel Information
TOKEN = 'YOUR_BOT_TOKEN'
CHANNEL_ID = 'yourchannel'  # Without '@'
PROMOCODE_FILE = 'promocode.txt'
ADMIN_IDS = [123456789, 987654321]  # Replace with actual admin user IDs

# State Tracking
USER_KEYS = {}
USER_REQUESTS = {}
USER_POINTS = {}
REFERRAL_TRACKER = {}
SPECIAL_EVENTS = False

# Configuration
MAX_KEYS_PER_DAY = 4
TIME_LIMIT = 24 * 60 * 60  # 24 hours in seconds
KEYS_PER_CLICK = 4
BONUS_KEYS_EVENT = 2  # Extra keys during special events
EMOJIS = {'greeting': '😊', 'key': '🔑', 'check': '✔️', 'trophy': '🏆'}

# Startup Message
STARTUP_MESSAGE = "THIS BOT IS MADE BY QURESHI BOY AND SHAHIDLALA. 🎉 Enjoy our features and have a great time!"

# Bot Initialization
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_first_name = update.message.from_user.first_name
    bot = context.bot

    await bot.send_message(chat_id, f"{EMOJIS['greeting']} Welcome {user_first_name}!\n{STARTUP_MESSAGE}")

    # Subscription Prompt
    keyboard = [[InlineKeyboardButton("Subscribe", url=f"https://t.me/{CHANNEL_ID}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(chat_id, "Please subscribe to the channel to get your promo key.", reply_markup=reply_markup)

    # Verify Subscription Button
    verify_button = [[InlineKeyboardButton("Verify Subscription", callback_data='verify_subscription')]]
    verify_reply_markup = InlineKeyboardMarkup(verify_button)
    await bot.send_message(chat_id, "After subscribing, click the button below to verify your subscription.", reply_markup=verify_reply_markup)

# Button Callback Handler
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    bot = context.bot

    if query.data == 'verify_subscription':
        if await check_subscription(bot, user_id):
            keyboard = [[InlineKeyboardButton("Get Key", callback_data='get_key')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await bot.send_message(chat_id, f"{EMOJIS['check']} You're subscribed! Click below to get your keys.", reply_markup=reply_markup)
        else:
            await bot.send_message(chat_id, "You need to subscribe to the channel to receive keys.")
    elif query.data == 'get_key':
        if await check_subscription(bot, user_id):
            if can_request_key(user_id):
                keys = get_keys(user_id)
                if keys:
                    key_list = "\n".join([f"{EMOJIS['key']} {key}" for key in keys])
                    await bot.send_message(chat_id, f"Here are your keys:\n{key_list}")
                    log_request(user_id)
                    increment_user_points(user_id, len(keys))
                else:
                    await bot.send_message(chat_id, "All keys have been used. Please wait 1 hour for an update.")
            else:
                await bot.send_message(chat_id, "You've already received keys. Try again after 24 hours.")
        else:
            await bot.send_message(chat_id, "You need to subscribe to the channel to receive keys.")
    
    await query.answer()  # Acknowledge callback queries

# Subscription Check Function
async def check_subscription(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_ID}", user_id=user_id)
        logging.info(f"Checked subscription for user {user_id}: {member.status}")
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Error checking subscription for user {user_id}: {e}")
        return False

# Promo Code Management
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
                USER_KEYS.setdefault(user_id, []).append(key)
            else:
                break
        
        # Update the promocode file after issuing keys
        with open(PROMOCODE_FILE, 'w') as file:
            for code in available_keys:
                file.write(f"{code}\n")
        
        return keys + (['Bonus Key'] * BONUS_KEYS_EVENT if SPECIAL_EVENTS else [])
    return []

def log_request(user_id):
    current_time = time.time()
    USER_REQUESTS[user_id] = [current_time]

def can_request_key(user_id):
    if user_id not in USER_REQUESTS:
        return True
    log_request(user_id)  # Clean old requests
    return len(USER_REQUESTS[user_id]) < 1  # User can only click once in 24 hours

# Admin-Only Info Command
async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    
    total_users = len(USER_KEYS)
    total_referrals = len(REFERRAL_TRACKER)
    total_keys_issued = sum(len(keys) for keys in USER_KEYS.values())
    remaining_keys = len(load_promocodes())
    
    info_message = (
        f"{EMOJIS['trophy']} Bot Statistics:\n"
        f"Total Users: {total_users}\n"
        f"Total Referrals: {total_referrals}\n"
        f"Total Keys Issued: {total_keys_issued}\n"
        f"Remaining Keys: {remaining_keys}\n"
    )
    
    await update.message.reply_text(info_message)

# Gamification: Loyalty Points
def increment_user_points(user_id, points):
    USER_POINTS[user_id] = USER_POINTS.get(user_id, 0) + points
    if USER_POINTS[user_id] % 10 == 0:  # Reward user every 10 points
        USER_KEYS.setdefault(user_id, []).append('Special Key')
        logging.info(f"User {user_id} rewarded with a Special Key for reaching {USER_POINTS[user_id]} points.")

# User Interaction Feedback
async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    feedback_text = ' '.join(context.args)
    
    # Save feedback to a file
    with open('feedback.txt', 'a') as file:
        file.write(f"User {user_id}: {feedback_text}\n")
    
    await update.message.reply_text(f"Thank you for your feedback! {EMOJIS['trophy']}")

# Referral System
async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    referred_user = context.args[0] if context.args else None

    if referred_user and referred_user not in REFERRAL_TRACKER:
        REFERRAL_TRACKER[referred_user] = user_id
        increment_user_points(user_id, 5)  # Reward the referrer with 5 points
        await update.message.reply_text(f"{EMOJIS['check']} You successfully referred a user! You've earned 5 points.")
    else:
        await update.message.reply_text(f"{EMOJIS['greeting']} This user has already been referred or doesn't exist.")

# Promo Code Management Commands
async def add_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /add_promocode <promocode>")
        return

    promocode = ' '.join(context.args)
    with open(PROMOCODE_FILE, 'a') as file:
        file.write(f"{promocode}\n")
    await update.message.reply_text(f"Promo code '{promocode}' added.")

async def show_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promocodes = load_promocodes()
    remaining_keys = len(promocodes)
    if remaining_keys > 0:
        await update.message.reply_text(f"Total remaining keys: {remaining_keys}")
    else:
        await update.message.reply_text("No keys available at the moment. Please wait a while before trying again.")

async def upload_promocodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        file = update.message.document
        file_id = file.file
