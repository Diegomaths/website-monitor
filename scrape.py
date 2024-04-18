import logging
import datetime
import sys
import time
import threading
import schedule
from cryptocompare import get_price
def is_day():
    current_hour = datetime.datetime.now().hour
    return 8 <= current_hour <= 23

logging.basicConfig(filename='logs/web_monitor.log', level=logging.DEBUG, format='%(asctime)s - scrape - %(levelname)s - %(message)s', filemode="w")
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
try:
    with open("credentials.json", "r") as f:
        credentials = eval(f.read())
        user = credentials["username"]
        psw = credentials["password"]
        TOKEN = credentials["solar_energy_token"]
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
        if old_level != battery_status_text:
            if ((perc > 90) or (perc < 20)) and is_day():
                t_notify(f"Alert battery level: {battery_status_text}")
        # else: t_notify(f"No battery level change: {battery_status_text}")
    except Exception as e:
        logging.error(f"Scraping error: {e}")

    finally:
        # Close webpage
        driver.quit()
        logger.info('End of process. \n__________________________________________________________________________________')
        # t_send_doc("logs/web_monitor.log")

def telegram_bot():
    tg_bot = telebot.TeleBot(TOKEN)
    @tg_bot.message_handler(commands=['start'])
    def send_welcome(message):
        tg_bot.reply_to(message, "Hi!")

    @tg_bot.message_handler(commands=['battery', "fotovoltaico", "pannelli", "refresh"])
    def send_battery(message):
        from_user_dict = message.from_user.__dict__
        chat_dict = message.chat.__dict__
        tg_bot.reply_to(message, f"Hello {from_user_dict['first_name']}, I'll check battery level for you...")
        scrape_battery_level()
        with open("old_level.txt", "r") as f:
            battery_level = f.read()
        tg_bot.send_message(chat_dict["id"], f"Battery level: {battery_level}")

    @tg_bot.message_handler(func=lambda msg:True)
    def show_battery_level(message):
        from_user_dict = message.from_user.__dict__
        chat_dict = message.chat.__dict__
        mt = message.text.lower()
        if "pannelli" in mt:
            # scrape_battery_level()
            with open("old_level.txt", "r") as f:
                battery_level = f.read()
            tg_bot.send_message(chat_dict["id"], f"I pannelli sono al {battery_level}")
    tg_bot.infinity_polling()
telegram_thread = threading.Thread(target=telegram_bot)
telegram_thread.daemon = True
telegram_thread.start()


# def job():
#     scrape_battery_level()

schedule.every(3600).seconds.do(scrape_battery_level)

while True:
    schedule.run_pending()
    time.sleep(1)  # Aggiungi un piccolo ritardo per evitare di consumare troppa CPU inutilmente