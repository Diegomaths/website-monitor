import pandas as pd
import numpy as np
import re
import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup

with open("data/lineup.txt", "r") as f:
    s = f.read()

logging.basicConfig(filename='logs/voti_webpage.log', level=logging.DEBUG, format='%(asctime)s - BOT - %(levelname)s - %(message)s', filemode="w")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger = logging.getLogger('')
logger.addHandler(console_handler)

def compute_ratings(input_string, formation = "3-4-3"):
    n_players = ["0", formation.split('-')]
    roles = ["P", "D", "C", "A"]
    
    n_players = [int(item)+2 for sublist in n_players for item in (sublist if isinstance(sublist, list) else [sublist])]
    ratings = []
    tokens = input_string.split('\n')[1:]
    for token in tokens:
        sub = token.split(" ")
        ratings.append(sub)
    #convert ratings list of list to a single list, keep only numbers and dots
    ratings = pd.Series([item for sublist in ratings for item in sublist]).str.strip("\)").str.strip("\(").str.strip()
    # print(ratings)
    players_ratings = {}
    s = ""
    for i in range(len(n_players)):
        s += roles[i] * n_players[i]

    for i in range(len(ratings)):
        value = ratings[i]
        #if value contains numbers
        if re.search(r'\d', value):
            players_ratings[ratings[i-1]] = value
        else:
            players_ratings[value] = np.nan
    players_ratings = pd.Series(players_ratings).astype(float)
    # players_ratings["TOTAL"] = players_ratings.dropna().sum()
    lineup = pd.DataFrame(players_ratings)
    lineup.reset_index(inplace=True)
    lineup.columns = ["Player", "Rating"]
    lineup["Role"] = list(s)
    return lineup
    # return [lineup, s]
def series_to_string(series):
    result_string = ""
    for index, value in series.items():
        result_string += f"{index}: {value}\n"
    return(result_string)

def scrape_ratings(webpage='https://fantapiu3.com/voti/voti-gazzetta-sport-fantacalcio-europei.php'):
    try:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Firefox(options=options)
        driver.get(webpage)
        s = driver.page_source
        with open("data/page_scraping.txt", "w") as f:
            f.write(s)
    except Exception as e:
        logging.error(f"Error scraping webpage {webpage}:\n\n\n{e}")
    finally:
        driver.quit()
        logger.info(f'End of process with webpage {webpage}. \n__________________________________________________________________________________')

def clean(s):
    # Usa una regex per trovare tutto ciò che è tra i caratteri < e >
    return re.sub(r'<[^>]*>', '', s)

def contiene_pattern(s):
    # Definisci il pattern regex: 'v' seguito da uno o più cifre
    pattern = r'v\d+|vsv'
    
    # Usa re.search per cercare il pattern nella stringa
    if re.search(pattern, s):
        return True
    else:
        return False

def manage_scraping_result():
    with open ("data/page_scraping.txt", "r") as f:
        html_content = f.read()
    # Parsing del contenuto HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    # def extract_player_image(soup):
    players = {}
    rows = soup.find_all('div', class_='table-row')
    players_list = []
    out = []
    for row in rows:
        name_tag = row.find('p', class_='table-text bolder')
        if name_tag:
            name = name_tag.text.strip()
            players_list.append(name)
            img_tag = row.find_next('img')
            temp = img_tag["src"]
            j=1
            
            while not contiene_pattern(temp):
                img_tag = row.find_all_next('img')
                temp = img_tag[j]["src"]
                j+=1

            if contiene_pattern(temp) and len(out)==0:
                img_temp = row.find_all_next('img')
                for i in range(len(img_temp)):
                    other_cols = img_temp[i]["src"]
                    imgs = other_cols.split("/")[-1]
                    imgs = imgs.replace(".png", "")
                    imgs = imgs.replace("tr", "0")
                    out.append(imgs)

            voto = temp.split("/")[-1]
            voto = voto.replace(".png", "")[1:].replace("sv", "")
            if voto !="":
                if float(voto) > 11:
                    voto = voto[0] + "." + voto[1]
            players[name] = voto

    risultati = {}
    # Lunghezza della lista originale
    lunghezza_lista = len(out)
    # Indice per scorrere la lista
    i=0
    j=0
    while i < lunghezza_lista:
        if contiene_pattern(out[i]):
            temp = out[i]
            voto = temp.split("/")[-1]
            voto = voto.replace(".png", "")[1:].replace("sv", "")
            if voto !="":
                if float(voto) > 11:
                    voto = voto[0] + "." + voto[1]
            out[i] = voto  
            # Se trovi una stringa che contiene il pattern
            # Prendi i 9 elementi successivi se ci sono abbastanza elementi rimanenti
            if i + 9 < lunghezza_lista:
                        
                risultati[players_list[j]] = out[i:i+10]
                j+=1
            # Aggiorna l'indice per saltare direttamente ai prossimi 9 elementi
            i += 9
        else:
            # Se non trovi il pattern, passa all'elemento successivo
            i += 1
    return risultati 

def get_dataframe(results):
    df = pd.DataFrame(results).T
    colnames = ['Voto',
        'Bonus/Malus Portiere',
        'Goal Fatto',
        'Goal su Rigore',
        'Ammonizione',
        'Espulsione',
        'Rigore',
        'Autogoal',
        'Assist',
        'Assist da Fermo']
    df.columns = colnames
    df.Voto = df.Voto.apply(lambda x: float(x) if x != '' else np.nan)
    df["Bonus/Malus Portiere"] = df["Bonus/Malus Portiere"].str.replace("gs", "-").str.replace("gk", "1").astype("float")
    df["Goal Fatto"] = df["Goal Fatto"].str.replace("gf", "3").astype("float")
    df["Goal su Rigore"] = df["Goal su Rigore"].str.replace("gri", "3").astype("float")
    df["Ammonizione"] = df["Ammonizione"].str.replace("giallo", "-0.5").astype("float")
    df["Espulsione"] = df["Espulsione"].str.replace("rossos", "-1").astype("float")
    df["Rigore"] = df["Rigore"].str.replace("rsb", "-3").str.replace("rp", "3").astype("float")
    df["Autogoal"] = df["Autogoal"].str.replace("autogo", "-2").astype("float")
    df["Assist"] = df["Assist"].str.replace("assis", "1").astype("float")
    df['Assist da Fermo'] = df['Assist da Fermo'].apply(lambda x: 1 if x != '0' else x).astype("float")
    df["Fantavoto"] = df.sum(axis=1)
    df = df.replace(0, np.nan)
    df = df.reset_index()
    df = df.rename(columns={"index": "Player"})

    df.to_csv("data/last_matchday.csv", sep=";")
    return df

def transform(input_string, formation = "3-4-3"):
    # scrape_ratings()
    ris = manage_scraping_result()
    df = get_dataframe(ris)
    df.Player = df.Player.str.lower()
    lineup = compute_ratings(input_string, formation=formation)
    lineup.Player = lineup.Player.astype("string").str.lower().str.replace("_", " ")
    a = pd.merge(lineup, df[["Player", "Fantavoto"]], on="Player", how="left")
    a["Player"] = a["Player"].str.title()
    roles = ["P", "D", "C", "A"]
    n_players = ["1", formation.split('-')]
    n_players = [int(item) for sublist in n_players for item in (sublist if isinstance(sublist, list) else [sublist])]
    role_limits = dict(zip(roles, n_players))
    a["no_voto"] = a.Fantavoto.isna()
    a = a.sort_values(by=["Role", "no_voto"], ascending=[False, True])
    selected_players = []
    for role, limit in role_limits.items():
        top_players = a[a['Role'] == role].head(limit)
        selected_players.append(top_players)

    selected_players = pd.concat(selected_players, ignore_index=True)
    df_with_total = pd.concat([selected_players, pd.DataFrame({"Player": ["TOTAL"], "Fantavoto": [selected_players.Fantavoto.sum()]})], ignore_index=True)
    df_with_total.set_index("Player", inplace=True)
    res = df_with_total["Fantavoto"]
    with open("data/ratings.txt", "w") as f:
        f.write(series_to_string(res).replace(": nan", ": SV"))

if __name__ == "__main__": 
    try:
        with open("data/module.txt", "r") as f:
            module = f.read()
        transform(s, formation = module)
    except Exception as e:
        with open("data/ratings.txt", "w") as f:
            f.write("ERROR \n" + str(e))
        logger.error(e)