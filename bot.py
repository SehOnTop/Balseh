import os
import random
import telebot
from telebot import types
from datetime import datetime, timedelta
import threading
import re
import time

# --- Configuration ---
TOKEN = "7878751580:AAHbmBlPEY-oD2ExIKDogQ2ef2uZASssZdA"
DATABASE_FOLDER = "XCDATABASE"
OWNER_USERNAME = "@sehontop"
ADMIN_ID = 7645531452  # Replace with the admin's Telegram ID
CREDITS_MESSAGE = "Made by Seh"
REMOVE_URLS_DEFAULT = True
REGISTERED_USERS = {}  # {user_id: expiry_time}
# --- End Configuration ---

bot = telebot.TeleBot(TOKEN)


def process_lines_and_send(keyword, num_lines, remove_urls, chat_id, message_id):
    """Processes lines, sends as doc, and handles removal."""
    try:
        found_lines = []
        file_paths = [os.path.join(DATABASE_FOLDER, f) for f in os.listdir(DATABASE_FOLDER) if f.endswith(".txt")]

        if not file_paths:
            bot.edit_message_text("No text files found.", chat_id, message_id)
            return

        for file_path in file_paths:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                for line in file:
                    if keyword.lower() in line.lower():
                        if remove_urls:
                            line = re.sub(r"https?://\S+|www\.\S+", "", line).strip()
                        found_lines.append(line.strip())
                        if len(found_lines) >= num_lines:
                            break
            if len(found_lines) >= num_lines:
                break

        if not found_lines:
            bot.edit_message_text(f"No lines with '{keyword}' found.", chat_id, message_id)
            return

        selected_lines = found_lines[:num_lines]
        # Modified file name creation
        temp_file_name = f"xc_{keyword}_{num_lines}.txt"
        temp_file_path = temp_file_name

        with open(temp_file_path, "w", encoding="utf-8") as temp_file:
            for line in selected_lines:
                temp_file.write(line + "\n")

        with open(temp_file_path, "rb") as temp_file:
            bot.send_document(chat_id, temp_file, caption=f"Owner: {OWNER_USERNAME}\nKeywords: {keyword}\nLines: {num_lines}")

        os.remove(temp_file_path)
        remove_used_lines(keyword, selected_lines)
        bot.edit_message_text("Done!", chat_id, message_id)

    except Exception as e:
        bot.edit_message_text(f"Error: {e}", chat_id, message_id)

def remove_used_lines(keyword, lines):
    """Removes used lines from original files."""
    file_paths = [os.path.join(DATABASE_FOLDER, f) for f in os.listdir(DATABASE_FOLDER) if f.endswith(".txt")]
    for file_path in file_paths:
        temp_lines = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
            for line in file:
                if keyword.lower() in line.lower() and line.strip() in lines:
                    continue
                temp_lines.append(line)
        with open(file_path, "w", encoding="utf-8") as file:
            file.writelines(temp_lines)



@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Generate Lines"), types.KeyboardButton("Admin Commands"))
    bot.send_message(message.chat.id, " 𝚆𝙴𝙻𝙲𝙾𝙼𝙴 𝙼𝙰 𝙼𝙰𝙽!", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Generate Lines")
def generate_lines_handler(message):
    if check_registration(message):
        msg = bot.send_message(message.chat.id, "Enter keyword:")
        bot.register_next_step_handler(msg, get_num_lines)
    else:
        bot.reply_to(message, "You are not registered to use this command.")

def get_num_lines(message):
    keyword = message.text
    msg = bot.send_message(message.chat.id, "Enter number of lines:")
    bot.register_next_step_handler(msg, get_url_choice, keyword)

def get_url_choice(message, keyword):
    try:
        num_lines = int(message.text)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Yes", callback_data=f"url_yes_{keyword}_{num_lines}"),
                   types.InlineKeyboardButton("No", callback_data=f"url_no_{keyword}_{num_lines}"))
        bot.send_message(message.chat.id, "Remove URLs?", reply_markup=markup)
    except ValueError:
        bot.reply_to(message, "Invalid number.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("url_"))
def handle_url_choice(call):
    remove_urls = call.data.split("_")[1] == "yes"
    keyword = call.data.split("_")[2]
    num_lines = int(call.data.split("_")[3])
    msg = bot.send_message(call.message.chat.id, "Searching....")
    threading.Thread(target=process_lines_and_send, args=(keyword, num_lines, remove_urls, call.message.chat.id, msg.message_id)).start()

@bot.message_handler(func=lambda message: message.text == "Admin Commands")
def admin_commands(message):
    if message.from_user.id == ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("List Files"), types.KeyboardButton("Delete File"),
                   types.KeyboardButton("Register User"), types.KeyboardButton("Unregister User"), types.KeyboardButton("Registered Users"), types.KeyboardButton("Back"))
        bot.send_message(message.chat.id, "🛠️ Admin Commands:", reply_markup=markup)
    else:
        bot.reply_to(message, "Unauthorized.")

@bot.message_handler(func=lambda message: message.text == "List Files")
def list_files(message):
    if message.from_user.id == ADMIN_ID:
        files = "\n".join(os.listdir(DATABASE_FOLDER))
        bot.send_message(message.chat.id, f"Files:\n{files}")
    else:
        bot.reply_to(message, "Unauthorized.")

@bot.message_handler(func=lambda message: message.text == "Delete File")
def delete_file_handler(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.send_message(message.chat.id, "Enter filename to delete:")
        bot.register_next_step_handler(msg, delete_file)
    else:
        bot.reply_to(message, "Unauthorized.")

def delete_file(message):
    file_path = os.path.join(DATABASE_FOLDER, message.text)
    try:
        os.remove(file_path)
        bot.send_message(message.chat.id, "File deleted.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {e}")

@bot.message_handler(func=lambda message: message.text == "Register User")
def register_user_handler(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.send_message(message.chat.id, "Enter user ID and minutes (e.g., 12345 60):")
        bot.register_next_step_handler(msg, register_user)
    else:
        bot.reply_to(message, "Unauthorized.")

def register_user(message):
    try:
        user_id, minutes = map(int, message.text.split())
        expiry_time = datetime.now() + timedelta(minutes=minutes)
        REGISTERED_USERS[user_id] = expiry_time
        bot.send_message(message.chat.id, f"User {user_id} registered for {minutes} minutes.")
    except ValueError:
        bot.send_message(message.chat.id, "Invalid input.")

@bot.message_handler(func=lambda message: message.text == "Unregister User")
def unregister_user_handler(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.send_message(message.chat.id, "Enter user ID to unregister:")
        bot.register_next_step_handler(msg, unregister_user)
    else:
        bot.reply_to(message, "Unauthorized.")

def unregister_user(message):
    try:
        user_id = int(message.text)
        if user_id in REGISTERED_USERS:
            del REGISTERED_USERS[user_id]
            bot.send_message(message.chat.id, f"User {user_id} unregistered.")
        else:
            bot.send_message(message.chat.id, f"User {user_id} not found.")
    except ValueError:
        bot.send_message(message.chat.id, "Invalid input.")

@bot.message_handler(func=lambda message: message.text == "Registered Users")
def registered_users_handler(message):
    if message.from_user.id == ADMIN_ID:
        if REGISTERED_USERS:
            user_list = "\n".join([f"{uid}: {exp}" for uid, exp in REGISTERED_USERS.items()])
            bot.send_message(message.chat.id, f"Registered Users:\n{user_list}")
        else:
            bot.send_message(message.chat.id, "No users registered.")
    else:
        bot.reply_to(message, "Unauthorized.")

@bot.message_handler(func=lambda message: message.text == "Back")
def back_to_main(message):
    start(message)

def check_registration(message):
    """Checks if user is registered and registration is not expired."""
    user_id = message.from_user.id
    if user_id in REGISTERED_USERS:
        if datetime.now() < REGISTERED_USERS[user_id]:
            return True
        else:
            del REGISTERED_USERS[user_id]  # Remove expired user
            return False
    return False

@bot.message_handler(func=lambda message: message.text == "Generate Lines")
def generate_lines_handler(message):
    if check_registration(message):
        msg = bot.send_message(message.chat.id, "Enter keyword:")
        bot.register_next_step_handler(msg, get_num_lines)
    else:
        bot.reply_to(message, "You are not registered to use this command.")

bot.polling()
