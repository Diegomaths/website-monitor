import logging
import datetime
import sys
import time
logging.basicConfig(filename='logs/web_monitor.log', level=logging.DEBUG, format='%(asctime)s - scrape - %(levelname)s - %(message)s', filemode="w")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
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
logger.debug("Imported from func find field id")

try:
    with open("credentials.json", "r") as f:
        credentials = eval(f.read())
        user = credentials["username"]
        psw = credentials["password"]
    with open('config.json', "r") as f:
        config = eval(f.read())
except Exception as e:
    logger.error(f"Error loading credentials or configuration: {e}")

webpage = ''
headless=1
try:    
    display = Display(visible=1-int(headless), size=(1024, 768))
    display.start()
except Exception as e:
    logger.error(f"Error starting display: {e}")

try:
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    driver.get(webpage)

except Exception as e:
    logging.error(f"Scraping error: {e}")

finally:
    # Close webpage
    driver.quit()
    logger.info('End of process. \n__________________________________________________________________________________')
    t_send_doc("logs/web_monitor.log")