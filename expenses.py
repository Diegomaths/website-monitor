import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import locale
locale.setlocale(locale.LC_ALL, 'it_IT')
def read_google_sheet(sheet_name, worksheet_name, creds_json_path):
    # Autenticazione e accesso a Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_json_path, scope)
    client = gspread.authorize(creds)

    # Apertura del foglio di lavoro
    try:
        sheet = client.open(sheet_name).worksheet(worksheet_name)
    except gspread.SpreadsheetNotFound:
        print("Errore: Foglio di lavoro non trovato. Verifica il nome e i permessi di condivisione.")
        return None
    except gspread.WorksheetNotFound:
        print("Errore: Worksheet non trovato. Verifica il nome del worksheet.")
        return None

    # Lettura dei dati come lista di liste
    data = sheet.get_all_values()

    # Creazione del DataFrame pandas, saltando le prime 6 colonne
    df = pd.DataFrame(data)
    return df

def preprocess_google_sheet(df, period="last month"):
    df_table = df.iloc[:,:6]
    df_table.columns = df_table.iloc[0]
    df_table = df_table.iloc[1:]
    df_pvt = df.iloc[2:, 8:13]
    df_pvt.columns = df_pvt.iloc[0]
    df_pvt = df_pvt.iloc[1:].reset_index(drop=True)
    df_pvt["Periodo"] = df_pvt["Periodo"].astype(str)
    df_pvt = df_pvt[df_pvt["Periodo"]!=""]
    df_pvt["Year"] = df_pvt["Periodo"].str.split("-").str[0]
    df_pvt["Month"] = "0" + df_pvt["Periodo"].str.split("-").str[1]
    df_pvt["Month"] = df_pvt["Month"].str[-2:]
    df_pvt["Periodo"] = df_pvt["Year"] + "-" + df_pvt["Month"]
    df_pvt["Date"] = pd.to_datetime(df_pvt["Periodo"], format="%Y-%m")
    df_pvt["Month Name"] = df_pvt["Date"].dt.strftime("%B")
    df_pvt["Periodo di riferimento"] = df_pvt["Month Name"] + " " + df_pvt["Year"]
    df_pvt["Periodo di riferimento"] = df_pvt["Periodo di riferimento"].fillna("Totale")
    for col in ["Anna", "Bibo", "Diego", "Grand Total"]:
        df_pvt[col] = df_pvt[col].replace("","0").astype(int).fillna(0)
    df_output = df_pvt[["Periodo di riferimento", "Anna", "Bibo", "Diego", "Grand Total"]]
    df_output = df_output.rename(columns={"Grand Total": "Totale"})
    if period != "last month":
        df_output = df_output[df_output["Periodo di riferimento"]==period]
    str_output1 = f"Nel mese di {df_output['Periodo di riferimento'].iloc[-1]} la spesa totale è *{df_output['Totale'].iloc[-1]} euro*\n"
    for col in ["Anna", "Bibo", "Diego"]:
        str_output2 = f"Spesa {col}: *{df_output[col].iloc[-1]}* euro\n"
        str_output1 = str_output1 + str_output2
    return str_output1

# Esempio di utilizzo
# sheet_name = 'Spese casa'  # Nome del documento Google Sheets
# worksheet_name = 'Sheet1'  # Nome del worksheet
# creds_json_path = 'sheets_key.json'  # Percorso del file JSON delle credenziali
# df = read_google_sheet(sheet_name, worksheet_name, creds_json_path)
# print(preprocess_google_sheet(df, period="aprile 2024"))