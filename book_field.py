import datetime
import sys
import time
import logging
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
logging.basicConfig(filename='logs/book_field.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filemode="w")
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('')
logger.info("Book field script start")

if len(sys.argv) < 3:
    print("Usage: python book_field.py <username> <password> [time, default = 20:00] [confirm_booking, default = N]")
    sys.exit(1)

user = sys.argv[1]
psw = sys.argv[2]

if len(sys.argv) > 3: time_to_book = sys.argv[3]
else: time_to_book = '20:00'

if len(sys.argv) > 4: confirm_booking = sys.argv[4]
else: confirm_booking = 'N'

def find_field_id(start_time, add = 0):
    h = (float(start_time.split(':')[0]) - 8)*2
    m = float(start_time.split(':')[1])/30
    return str(int(h+m+add))

def click_button(xpath, wait=0.1):
    logger.info(f"Clicking button: {xpath}")
    time.sleep(wait)
    button = driver.find_element(By.XPATH, xpath)
    button.click()
    time.sleep(wait)

webpage = 'https://www.v-padel.com/vpadel/'
options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(options=options)
try:
    driver.get(webpage)
    username_field = driver.find_element(By.XPATH, '//*[@id="edit-name"]')
    username_field.send_keys(user)
    time.sleep(0.1)
    psw_field = driver.find_element(By.XPATH, '//*[@id="edit-pass"]')
    psw_field.send_keys(psw)
    time.sleep(0.1)
    click_button('//*[@id="edit-submit"]')  # click login button

    # Open Court 1
    logger.info('Opening Court 1 booking...')
    click_button('//*[@id="menu-1029-1"]/a')  # click book court button
    court1_xpath = '/html/body/div[2]/div[1]/div[5]/div[2]/div[2]/div/div/div/div[2]/table/tbody/tr[1]/td[1]/div/span[2]/a'
    click_button(court1_xpath)  # click court 1 button

    # Select day to book
    general_xpath = '//*[@id="block-system-main"]/div/div/div[2]/div/div/table/tbody[2]/tr[NUMBER]/td[2]/div/div/a'
    next_week = '//*[@id="block-system-main"]/div/div/div[1]/a[3]'
    next_day = '//*[@id="block-system-main"]/div/div/div[1]/a[4]'
    booking_date = (datetime.datetime.now() + datetime.timedelta(weeks=2) + datetime.timedelta(days=1)).strftime("%d-%m-%Y")
    logger.info("One week forward...")
    click_button(next_week)
    logger.info("Another week forward...")
    click_button(next_week)
    ct0 = datetime.datetime.now()
    logger.info("Waiting for next day...")
    loop = True
    while loop:
        ct = datetime.datetime.now()
        if ct.second < 53 and ct.second!=0:
            time.sleep(5)
        if ct.minute != ct0.minute:
            logger.info("One day forward...")
            click_button(next_day, wait=0)
            loop = False
    logger.info(f"Opening Court 1 - {booking_date}")

    # Select time to book
    try:
        logger.info(f"TRY BOOKING at {time_to_book}!")
        btn = f"{general_xpath.replace('NUMBER', find_field_id(time_to_book))}"
        logger.info(btn)
        logger.info(f"Trying opening court booking for working day with the following xpath: {btn}")
        click_button(btn, wait=0)
        logger.info("FREE COURT!")
    except Exception as e:
        logger.warning("NOT BOOKED!")
        logger.warning(f"{e} didn't work.")
    # Confirm booking
    save_booking_xpath = '//*[@id="edit-submit"]'
    if confirm_booking == 'Y':
        logger.info(f'Saving booking for Court 1 on {booking_date} at {time_to_book}...')
        click_button(save_booking_xpath, wait=0)
    else: 
        logging.warning(f'Booking not confirmed!')

        
except Exception as e:
    logging.error(e)

finally:
    # Close webpage
    driver.quit()
    logger.info('End of process. \n__________________________________________________________________________________')
