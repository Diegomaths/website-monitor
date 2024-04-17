import datetime
import telepot
with open("credentials.json", "r") as f:
    credentials = eval(f.read())
    TOKEN = credentials["solar_energy_token"]
    CHATID = credentials["chat_id"]

def t_notify(msg="ok"):
    bot = telepot.Bot(TOKEN).sendMessage(CHATID, msg, parse_mode="markdown")
def t_send_photo(image_path):
    bot = telepot.Bot(TOKEN).sendPhoto(CHATID, open(image_path, 'rb'))
def t_send_doc(doc_path):
    bot = telepot.Bot(TOKEN).sendDocument(CHATID, open(doc_path, 'rb'))

