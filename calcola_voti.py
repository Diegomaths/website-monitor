import pandas as pd
import re
s = '''
GOL D. ROGER - Giornata 1
Pickford 7.5
Castagne 5 Dumfries 6.5 Dias 6.5 (Kounde Gvardiol)
Chiesa 6.5 Olmo 6 Fernandes 5.5 Griezmann 5 (Gundogan Pasalic)
Morata 10 Depay 6 Hojlund 5 (Thuram Dovbyk)
'''
def compute_ratings(input_string):
    ratings = []
    tokens = input_string.split('\n')[1:]
    for token in tokens:
        sub = token.split(" ")
        ratings.append(sub)
    #convert ratings list of list to a single list, keep only numbers and dots
    ratings = pd.Series([item for sublist in ratings for item in sublist]).str.strip("\)").str.strip("\(").str.strip()
    players_ratings = {}
    for i in range(len(ratings)):
        value = ratings[i]
        #if value contains numbers
        if re.search(r'\d', value):
            players_ratings[ratings[i-1]] = value
    players_ratings = pd.Series(players_ratings).astype(float)
    players_ratings["TOTAL"] = players_ratings.dropna().sum()
    return players_ratings

def series_to_string(series):
    result_string = ""
    for index, value in series.items():
        result_string += f"{index}: {value}\n"
    return(result_string)

# print(series_to_string(compute_ratings(s)))