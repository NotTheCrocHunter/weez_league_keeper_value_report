import requests
import pandas as pd 
import math
from sleeper_wrapper import Players
import json

def get_adp_round(row):
    return math.ceil(row['adp_rank'] / 12)


def get_adp_df():
    adp_response = requests.get(
        url="https://fantasyfootballcalculator.com/api/v1/adp/ppr?teams=12&year=2023&position=all")
    adp_data = adp_response.json()
    adp_df = pd.DataFrame(adp_data['players'])

    adp_df.rename(columns={'player_id': 'ffcalc_id'}, inplace=True)
    adp_df['adp_rank'] = adp_df.index + 1
    adp_df['average_draft_round'] = adp_df.apply(get_adp_round, axis=1)

    return adp_df

def get_adp_data():
    adp_response = requests.get(
        url="https://fantasyfootballcalculator.com/api/v1/adp/ppr?teams=12&year=2023&position=all")
    adp_json = adp_response.json()
    return adp_json['players']

adp_data = get_adp_data()

players = Players()
player_dict = players.get_all_players()
matched_players = []
unmatched_players = []

for adp_player in adp_data:
    adp_name = adp_player['name'].lower().replace('.', '')
    if adp_name == 'gabriel davis':
        adp_name = 'gabe davis'
    if adp_name[-4:] == ' iii':
        adp_name = adp_name[:-4]
    if adp_name[-3:] in [' jr', ' ii']:
        adp_name = adp_name[:-3] 
    adp_position = adp_player['position']
    if adp_position == 'PK':
        adp_position = 'K'

    adp_team = adp_player['team']

    matched = False

    for player_id, sleeper_player in player_dict.items():
        if 'full_name' in sleeper_player:
            # make sure names are lower case and remove punctuation
            sleeper_name = sleeper_player['full_name'].lower().replace('.', '')  # .replace(r'[^\w\s]+', '')

        elif sleeper_player.get('position') == 'DEF':
            sleeper_name = f"{sleeper_player['first_name'].lower()} defense"

        sleeper_position = sleeper_player['position']
        sleeper_team = sleeper_player['team']

        if adp_team == 'FA':
            if sleeper_team == None:
                sleeper_team = 'FA'
                print(sleeper_team)

        if (
            adp_name in sleeper_name
            and adp_position == sleeper_position
            and adp_team == sleeper_team
        ):
            matched = True
            matched_players.append({
                'adp_player': adp_player,
                'dictionary_player': sleeper_player
            })
            break
    
    if not matched:
        adp_player['stripped_name'] = adp_name
        adp_player['stripped_team'] = adp_team
        adp_player['stripped_position'] = adp_position
        unmatched_players.append(adp_player)


# Create a dictionary to store matched ADP IDs and Sleeper IDs
match_dict = {}

for matched_player in matched_players:
    adp_player_id = matched_player['adp_player']['player_id']
    sleeper_player_id = matched_player['dictionary_player']['player_id']
    match_dict[str(adp_player_id)] = str(sleeper_player_id)

# Create a list to store unmatched ADP IDs
unmatched_adp_ids = {player['player_id']: player['name'] for player in unmatched_players}

# Create a dictionary to store matched and unmatched data
data_to_export = {
    'matched_players': match_dict,
    'unmatched_adp_ids': unmatched_adp_ids
}

# Export the data to a JSON file
with open('data/players/ffcalc_id_to_sleeper_id_mapping.json', 'w') as json_file:
    json.dump(data_to_export, json_file, indent=4)

print("Data exported to player_id_mapping.json")


"""
# Print the matched players
for matched_player in matched_players:
    print("ADP Player:", matched_player['adp_player']['name'])
    print("Dictionary Player:", matched_player['dictionary_player']['full_name'])
    print("-" * 40)
"""
"""
for p in unmatched_players:
    print(f'adp name: {p["name"]} - stripped name {p["stripped_name"]}')
    print("*" * 40)

print(f"total unmatched players: {len(unmatched_players)}")

"""