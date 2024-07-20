import logging
import datetime
import sys
import time
import threading
import schedule
import subprocess
import os
import pandas as pd
import gspread
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from pyvirtualdisplay import Display
from oauth2client.service_account import ServiceAccountCredentials
import telebot
from telebot import types

from expenses import read_google_sheet, preprocess_google_sheet
# from calcola_voti import compute_ratings, series_to_string

logging.basicConfig(filename='logs/web_monitor.log', level=logging.DEBUG, format='%(asctime)s - BOT - %(levelname)s - %(message)s', filemode="w")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger = logging.getLogger('')
logger.addHandler(console_handler)

# Leggi le credenziali dal file
try:
    with open("credentials.json", "r") as f:
        credentials = eval(f.read())
        user = credentials["username"]
        psw = credentials["password"]
        TOKEN = credentials["test_token"] #test_token, prod_token
        padel_user = credentials["padel_user"]
        padel_password = credentials["padel_pass"]
except Exception as e:
    logger.error(f"Error loading credentials or configuration: {e}")

# Funzione per controllare il livello della batteria
def scrape_battery_level(webpage='https://xstoragehome.com/'):
    try:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Firefox(options=options)
        driver.get(webpage)
        time.sleep(15)
        username_field = driver.find_element(By.ID, "logonIdentifier")
        username_field.send_keys(user)
        time.sleep(0.2)
        psw_field = driver.find_element(By.ID, "password")
        psw_field.send_keys(psw)
        confirm_login = driver.find_element(By.ID, "next")
        confirm_login.click()
        time.sleep(15)
        battery_status = driver.find_element(By.ID, "BatteryStatus_StateOfChargePercentage")
        battery_status_text = battery_status.text
        logger.debug(f"New level = {battery_status_text}")
        battery_level_filename = "data/old_level.txt"
        with open(battery_level_filename, "r") as f:
            old_level = f.read()
        logger.debug(f"Old level: {old_level}")
        with open(battery_level_filename, "w") as f:
            f.write(battery_status_text)

        with open("data/battery_history.txt", "a") as f:
            f.write(f"{datetime.datetime.now()};{battery_status_text}\n")

        perc = int(battery_status_text.replace("%", ""))
        out=True
    except Exception as e:
        #save screenshot with selenium
        driver.save_screenshot('data/xstorage_error.png')
        logging.error(f"Scraping error: {e}")
        out=False
    finally:
        driver.quit()
        logger.info(f'End of process on {webpage}. \n__________________________________________________________________________________')
    return out
def format_datetime(mod_time, current_time):
    if mod_time.date() == current_time.date():
        return f"oggi alle {mod_time.strftime('%H:%M')}"
    elif mod_time.date() == (current_time - datetime.timedelta(days=1)).date():
        return f"ieri alle {mod_time.strftime('%H:%M')}"
    else:
        return mod_time.strftime('il %d/%m alle %H:%M')

def format_battery_level():
    battery_level_filename = 'data/old_level.txt'
    with open(battery_level_filename, "r") as f:
        battery_level = f.read()
    perc = int(battery_level.replace("%", ""))
    modification_time = os.path.getmtime(battery_level_filename)
    modification_datetime = datetime.datetime.fromtimestamp(modification_time)
    formatted_modification_time = format_datetime(modification_datetime, datetime.datetime.now())
    msg = f"\U0001F4CC I pannelli sono al {bold_message(battery_level)} {get_emoji(perc)}\n\n\n\n\U0001F4C5 _Dato aggiornato {formatted_modification_time}_\n\U0001F504 Per un dato più aggiornato, usa il comando /pannelli"
    return msg

def bold_message(text):
    return f"*{text}*"

def get_emoji(perc):
    if perc < 50:
        return "\U0001FAAB"
    else:
        return "\U0001F50B"

# Funzione principale del bot Telegram
def telegram_bot():
    tg_bot = telebot.TeleBot(TOKEN)

    @tg_bot.message_handler(commands=['start'])
    def send_welcome(message):
        tg_bot.reply_to(message, "Ciao! Sono il tuo bot.")

        
    @tg_bot.message_handler(commands=['spese', "spesa", "conti"])
    def get_table(message, period="last month"):
        sheet_name = 'Spese casa'
        worksheet_name = 'Sheet1'
        creds_json_path = 'sheets_key.json'
        df = read_google_sheet(sheet_name, worksheet_name, creds_json_path)
        out = preprocess_google_sheet(df, period=period)
        with open("data/expenses.txt", "w") as f:
            f.write(out)
        tg_bot.send_message(message.chat.id, out, parse_mode='Markdown')

    @tg_bot.message_handler(commands=['battery', "fotovoltaico", "pannelli", "refresh"])
    def send_battery(message):
        check = scrape_battery_level()
        if check:
            msg = format_battery_level()
            tg_bot.send_message(message.chat.id, msg, parse_mode='Markdown')
        else:tg_bot.send_photo(message.chat.id, open('data/xstorage_error.png', 'rb'))


    # @tg_bot.message_handler(commands=["voti"])
    # def compute_matchday(message):
    #     chat_id = message.chat.id
    #     tg_bot.send_message(chat_id, "Per favore, fornisci una stringa di testo con la formazione.")
    #     tg_bot.register_next_step_handler(message, get_lineup)

    # def get_lineup(message):
    #     chat_id = message.chat.id
    #     modules_list = ["4-4-2", "4-3-3", "3-5-2", "3-4-3", "5-3-2", "5-4-1", "3-6-1", "4-5-1", "5-2-3"]
    #     user_input = message.text
    #     with open("data/lineup.txt", "w") as f:
    #         f.write(user_input)
    #     markup_mods= types.InlineKeyboardMarkup()
    #     for el in modules_list:
    #         button = types.InlineKeyboardButton(el, callback_data=f"mod_{el}")
    #         markup_mods.add(button)
    #     tg_bot.send_message(chat_id, "Scegli il tuo modulo", reply_markup=markup_mods)
    #     tg_bot.register_next_step_handler(message, get_module)

    # @tg_bot.callback_query_handler(func=lambda call: call.data.startswith("mod_"))
    # def get_module(call):
    #     chat_id = call.from_user.id
    #     module = call.data.replace("mod_", "")
    #     with open("data/module.txt", "w") as f:
    #         f.write(module)
    #     try:
    #         subprocess.run([sys.executable, "calcola_voti.py"])
    #         with open("data/ratings.txt") as f:
    #             result = f.read()
    #     except Exception as e:
    #         result = str(e)
    #     tg_bot.send_message(chat_id, result)

    @tg_bot.message_handler(commands=["book_field"])
    def book_court(message):
        user = message.from_user.username
        if user == "RealShambles":
            sent_message = tg_bot.reply_to(message, f"Ciao {user}, provo a prenotare a nome {padel_user}!")
            subprocess.run([sys.executable, "book_field.py", padel_user, padel_password, "20:00", "Y"])
            with open("data/booked_court.txt", "r") as f:
                book_court_response = f.read()
            tg_bot.edit_message_text(chat_id=sent_message.chat.id, message_id=sent_message.message_id, text=book_court_response)
        else:
            tg_bot.reply_to(message, f"Ciao {user}. Non sei autorizzato ad utilizzare questo comando.")

    @tg_bot.message_handler(commands=["get_log"])
    def get_log(message):
        logs_list = os.listdir("./logs")
        chat_id = message.chat.id
        markup = types.InlineKeyboardMarkup()
        for el in logs_list:
            el = el.replace(".log", "")
            button = types.InlineKeyboardButton(el, callback_data=f"{el}.log")
            markup.add(button)
        tg_bot.send_message(chat_id, "Scegli un'opzione:", reply_markup=markup)

    @tg_bot.callback_query_handler(func=lambda call: call.data.endswith(".log"))
    def handle_query(call):
        chat_id = call.from_user.id
        file_path = f"./logs/{call.data}"
        with open(file_path, 'rb') as file:
            tg_bot.send_document(chat_id, file)

    @tg_bot.message_handler(commands=["commands"])
    def list_commands(message):
        commands = [
            ('/start', 'Avvia il bot'),
            ('/spese', 'Mostra le spese'),
            ('/pannelli', 'Mostra lo stato della batteria'),
            ('/book_field', 'Prenota un campo da padel'),
            ('/get_log', 'Ottieni il log'),
        ]
        help_text = "\n".join([f"{cmd[0]} - {cmd[1]}" for cmd in commands])
        tg_bot.reply_to(message, help_text)

    @tg_bot.message_handler(func=lambda msg: True)
    def show_battery_level(message):
        print(1)
        logger.info(f"{message.from_user.username} - {message.text}")
        mt = message.text.lower()
        if "pannelli" in mt:
            msg = format_battery_level()
            tg_bot.send_message(message.chat.id, msg, parse_mode='Markdown')
        elif "spese" in mt:
            try:
                mt_month = mt.replace("spese ", "")
                if int(mt_month[-4:]) >= 2024:
                    get_table(message, period=mt_month)
            except:
                get_table(message)
            # with open("data/expenses.txt", "r") as f:
            #     out = f.read()
            # tg_bot.send_message(message.chat.id, out, parse_mode='Markdown')

    tg_bot.infinity_polling()

telegram_thread = threading.Thread(target=telegram_bot)
telegram_thread.daemon = True
telegram_thread.start()

schedule.every().hour.do(scrape_battery_level)
while True:
    schedule.run_pending()
    time.sleep(1)
