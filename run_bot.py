import logging
import datetime
import sys
import time
import threading
import schedule
import os
import pandas as pd
import gspread
import subprocess
import selenium
from oauth2client.service_account import ServiceAccountCredentials
import locale
locale.setlocale(locale.LC_ALL, 'it_IT')
from expenses import read_google_sheet, preprocess_google_sheet
from calcola_voti import compute_ratings
def is_day():
    current_hour = datetime.datetime.now().hour
    return 8 <= current_hour <= 23

logging.basicConfig(filename='logs/web_monitor.log', level=logging.DEBUG, format='%(asctime)s - BOT - %(levelname)s - %(message)s', filemode="w")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger = logging.getLogger('')
logger.addHandler(console_handler)
logger.warning("SCRAPE start")
from selenium import webdriver
logger.debug("Imported selenium")
from pyvirtualdisplay import Display
logger.debug("Imported display")
from telepot_functions import t_notify, t_send_doc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import telebot
logs_list = [el.replace(".log", "") for el in os.listdir("logs")]
try:
    with open("credentials.json", "r") as f:
        credentials = eval(f.read())
        user = credentials["username"]
        psw = credentials["password"]
        TOKEN = credentials["solar_energy_token"]
        padel_user = credentials["padel_user"]
        padel_password = credentials["padel_pass"]
except Exception as e:
    logger.error(f"Error loading credentials or configuration: {e}")

def scrape_battery_level(webpage = 'https://xstoragehome.com/'):
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
        with open("old_level.txt", "r") as f:
            old_level = f.read()
        logger.debug(f"Old level: {old_level}")
        with open("old_level.txt", "w") as f:
            f.write(battery_status_text)
        
        with open("battery_history.txt", "a") as f:
            f.write(f"{datetime.datetime.now()};{battery_status_text}\n")

        perc = int(battery_status_text.replace("%", ""))
        # if old_level != battery_status_text:
        #     if ((perc > 90) or (perc < 20)) and is_day():
        #         t_notify(f"Alert battery level: {battery_status_text}")
        # else: t_notify(f"No battery level change: {battery_status_text}")
    except Exception as e:
        logging.error(f"Scraping error: {e}")

    finally:
        # Close webpage
        driver.quit()
        logger.info('End of process. \n__________________________________________________________________________________')

def format_datetime(mod_time, current_time):
    if mod_time.date() == current_time.date():
        return f"oggi alle {mod_time.strftime('%H:%M')}"
    elif mod_time.date() == (current_time - datetime.timedelta(days=1)).date():
        return f"ieri alle {mod_time.strftime('%H:%M')}"
    else:
        return mod_time.strftime('il %d/%m alle %H:%M')

def format_battery_level():
    battery_level_filename = 'old_level.txt'
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

def telegram_bot():
    tg_bot = telebot.TeleBot(TOKEN)
    @tg_bot.message_handler(commands=['start'])
    def send_welcome(message):
        tg_bot.reply_to(message, "Hi!")

    @tg_bot.message_handler(commands=['spese', "spesa", "conti"])
    def get_table(message, period="last month"):
        sheet_name = 'Spese casa'  # Nome del documento Google Sheets
        worksheet_name = 'Sheet1'  # Nome del worksheet
        creds_json_path = 'sheets_key.json'  # Percorso del file JSON delle credenziali
        df = read_google_sheet(sheet_name, worksheet_name, creds_json_path)
        out = preprocess_google_sheet(df,period=period)
        with open("expenses.txt", "w") as f:
            f.write(out)
        # tg_bot.reply_to(message, out)

    @tg_bot.message_handler(commands=['battery', "fotovoltaico", "pannelli", "refresh"])
    def send_battery(message):
        from_user_dict = message.from_user.__dict__
        scrape_battery_level()
        msg = format_battery_level()
        tg_bot.send_message(message.chat.__dict__["id"], msg, parse_mode='Markdown')

    @tg_bot.message_handler(commands=["voti"])
    def compute_matchday(message):
        chat_id = message.chat.id
        tg_bot.send_message(chat_id, "Per favore, fornisci una stringa di testo con la formazione.")
        tg_bot.register_next_step_handler(message, get_user_input)
    def get_user_input(message):
        chat_id = message.chat.id
        user_input = message.text
        result = compute_ratings(user_input)
        tg_bot.send_message(chat_id, result)
    
    @tg_bot.message_handler(commands=["book_field"])
    def book_field(message):
        from_user_dict = message.from_user.__dict__
        user = from_user_dict["username"]
        chat_dict = message.chat.__dict__
        if user == "RealShambles":
            tg_bot.reply_to(message, f"Ciao {user}")
            cwd = os.getcwd()
            subprocess.run([sys.executable, "book_field.py", padel_user, padel_password])
        else:
            tg_bot.reply_to(message, f"Ciao {user}. Non sei autorizzato ad utilizzare questo comando.")
    ##
    @tg_bot.message_handler(commands=["get_log"])
    def test_function(message):
        chat_id = message.chat.id
        markup = telebot.types.InlineKeyboardMarkup()
        for el in logs_list:
            button = telebot.types.InlineKeyboardButton(el, callback_data=el)
            markup.add(button)
        tg_bot.send_message(chat_id, "Scegli un'opzione:", reply_markup=markup)
        # tg_bot.register_next_step_handler(message, get_user_input)
    @tg_bot.callback_query_handler(func=lambda call: True)
    def handle_query(call):
        chat_id = call.message.chat.id
        file_path = f"./logs/{call.data}.log"
        with open(file_path, 'rb') as file:
            tg_bot.send_document(chat_id, file)

    def get_user_input(message):
        chat_id = message.chat.id
        user_input = message.text
        tg_bot.send_message(chat_id, f"hai scelto {user_input}")
    ##
    @tg_bot.message_handler(func=lambda msg:True)
    def show_battery_level(message):
        from_user_dict = message.from_user.__dict__
        chat_dict = message.chat.__dict__
        mt = message.text.lower()
        if "pannelli" in mt:
            msg = format_battery_level()
            tg_bot.send_message(chat_dict["id"], 
            msg,
            parse_mode='Markdown')
        elif "spese" in mt:
            try:
                mt_month = mt.replace("spese ", "")
                if int(mt_month[-4:]) >= 2024:
                    get_table(message, period = mt_month)
            except: get_table(message)
            with open("expenses.txt", "r") as f:
                out = f.read()
            tg_bot.send_message(chat_dict["id"], out, parse_mode='Markdown')
    tg_bot.infinity_polling()
telegram_thread = threading.Thread(target=telegram_bot)
telegram_thread.daemon = True
telegram_thread.start()
schedule.every().hour.do(scrape_battery_level)
while True:
    schedule.run_pending()
    time.sleep(1) 
