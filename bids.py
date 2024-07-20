import os
import pandas as pd
data_dir = 'data/bids_history'
bids_history = pd.read_csv(f"{data_dir}/leagues.csv")
bids_history["code"] = "0" + bids_history.code.astype("str")
bids_history.set_index("code", inplace=True)
files_list = os.listdir(data_dir)
#filter files_list by .xlsx extension
files_list = [file for file in files_list if file.endswith('.xlsx')]
print(files_list)
all_leagues_data = pd.DataFrame(columns=['Ruolo','Calciatore','Squadra','Costo', 'Fantasquadra', "Numero Squadre", "Nome Lega"])
for file_name in files_list:
    league_code = file_name[:2]
    season = file_name[3:7]
    league_name = bids_history.loc[league_code, "league_name"]
    file_path = os.path.join(data_dir, file_name)
    excel_data = pd.ExcelFile(file_path)
    data_sheet = excel_data.sheet_names[0]
    #read just first n columns of sheet
    n_teams = bids_history.loc[league_code,"n_teams"]
    data_rows = bids_history.loc[league_code,"n_players_per_team"] + 4
    team_names_rows = [5 + data_rows*j for j in range(n_teams//2)]
    all_teams_data = pd.DataFrame(columns=['Ruolo','Calciatore','Squadra','Costo', 'Fantasquadra', "Numero Squadre"])
    for j in range(n_teams//2):
        for cols_to_use in ["A:D", "F:I"]:
            df = excel_data.parse(data_sheet, skiprows=team_names_rows[j]-1, usecols= cols_to_use).iloc[:30, :]
            team_name = df.columns[0]
            df = df.iloc[1:, :]
            df["Fantasquadra"] = team_name
            df["Numero Squadre"] = n_teams
            df.columns = all_teams_data.columns
            df = df[df.Ruolo != "Ruolo"]
            df = df[~df.Ruolo.astype("string").str.contains("Crediti")]
            all_teams_data = pd.concat([all_teams_data, df], ignore_index=True)
    all_teams_data["Nome Lega"] = league_name
    all_leagues_data = pd.concat([all_leagues_data, all_teams_data], ignore_index=True)
    all_leagues_data = all_leagues_data[all_leagues_data.Costo.fillna(0).astype("int") > 0]
all_leagues_data.to_csv(f"{data_dir}/all_leagues_data_{season}.csv", index=False)