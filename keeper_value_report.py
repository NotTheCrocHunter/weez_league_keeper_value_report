import requests
from datetime import datetime
from sleeper_wrapper import League, Players, Drafts
import math
import pandas as pd

year = datetime.now().year


def get_adp_data():
    adp_response = requests.get(
        url=f"https://fantasyfootballcalculator.com/api/v1/adp/ppr?teams=12&year={year}&position=all")
    adp_json = adp_response.json()
    for i, p in enumerate(adp_json['players']):
        p['adp_rank'] = i + 1
    return adp_json['players']

def get_adp_round(player_dict):
    if 'maher' in player_dict['name'].lower():
        print('DK')
    return math.ceil(player_dict['adp_rank'] / 12)

# Function to calculate the keeper value
def calculate_keeper_value(last_year_round, last_year_draft_by, last_year_keeper,
                           last_year2_draft_by, last_year2_final_roster, last_year2_keeper):
    if last_year_round == 'Undrafted':
        return 16
    elif last_year_round <= 3:
        return "Cannot keep player drafted in first three rounds"
    elif ((last_year_draft_by == last_year2_draft_by == last_year2_final_roster)
        and (last_year_keeper and last_year2_keeper)):
            return "Cannot keep player more than two consecutive years"
      # Indicate that no keeper value should be set
    else:
        return last_year_round - 2

adp_data = get_adp_data()

print(f'Keeper Report for Weez League {year}')

weez_league_id = 981251192351240192  # 2023 weez league id

league = League(weez_league_id)

# get players dict
all_players_manager = Players()
all_players = all_players_manager.get_all_players()

# get rosters - contains the fields
rosters = league.get_rosters()

# match up owner id to owner team name
league_users = league.get_users()
owner_usernames = league.map_users_to_owner_username(league_users)

# create rosters display list to hold the owners names and the player names
rosters_display = [{'owner_username': owner_usernames[r['owner_id']], 'player_ids': r['players']} for r in rosters]
player_count = 0
for r in rosters_display:
    player_count += len(r['player_ids'])

print(f'Number of players in league: {player_count}')

# get drafts - need draft id, previous league id, and previous leage draft id first
# then need to get picks historically including owner name and draft round and if keeper
current_draft = league.get_current_draft()
current_draft_id = current_draft[0]['draft_id']
prev_league_id = league._league['previous_league_id']
prev_draft_id = str(int(prev_league_id) + 1)
# new Draft object that begins with last years draft from prev_draft_id
drafts = Drafts(prev_draft_id)

all_drafts, all_final_rosters = drafts.get_all_drafts(weez_league_id)

# Main loop
for r in rosters_display:
    r['players'] = []
    
    # Loop through each player in the roster
    for player_id in r['player_ids']:
        # create beginning of player_dict, which will then add keeper value and final roster info through loops
        player_dict = {
            'player_id': player_id,
            # Using .get() to handle missing keys and provide default values
            'name': all_players.get(player_id, {}).get('full_name', all_players.get(player_id, {}).get('last_name', '')),
            'ffcalc_id': all_players.get(player_id, {}).get('ffcalc_id', ''),
        }
        # Loop through all drafts to get the historical draft rounds for each player
        for i, draft in enumerate(all_drafts):
            season_key = f'{year - i - 1}_round'
            picked_by_key = f'{year - i - 1}_drafted_by'
            keeper_key = f'{year - i - 1}_keeper'
            player_dict.setdefault(season_key, 'Undrafted')
            player_dict.setdefault(picked_by_key, '')
            player_dict.setdefault(keeper_key, False)

            for pick in draft:
                if pick['player_id'] == player_id:
                    player_dict[season_key] = pick['round']
                    player_dict[picked_by_key] = owner_usernames.get(pick['picked_by'], pick['picked_by'])
                    player_dict[keeper_key] = pick['is_keeper']

        # Loop through all final rosters to find if the player was kept
        for i, final_rosters in enumerate(all_final_rosters):
            season_key = f'{year - i - 1}_final_roster'
            player_dict.setdefault(season_key, None)

            try:
                for roster in final_rosters:
                    if player_id in roster['players']:
                        player_dict[season_key] = owner_usernames.get(roster['owner_id'], roster['owner_id'])
                        break
            except TypeError:
                break

        # Extract values for calculation from the player dictionary
        last_year_round = player_dict[f'{year - 1}_round']
        last_year_draft_by = player_dict[f'{year - 1}_drafted_by']
        last_year_keeper = player_dict[f'{year - 1}_keeper']
        last_year2_draft_by = player_dict[f'{year - 2}_drafted_by']
        last_year2_final_roster = player_dict[f'{year - 2}_final_roster']
        last_year2_keeper = player_dict[f'{year - 2}_keeper']

        # Calculate the keeper value using the function
        keeper_value = calculate_keeper_value(last_year_round, last_year_draft_by, last_year_keeper,
                                              last_year2_draft_by, last_year2_final_roster, last_year2_keeper)
        
        # Set the calculated keeper value in the player dictionary
        player_dict[f'{year}_keeper_round'] = keeper_value

        # now go trough the adp data to get the adp rank and round
        player_dict['adp_round'] = None
        for adp_player in adp_data:
            player_dict['adp_rank'] = 'Undrafted'
            player_dict['adp_round'] = 'Undrafted'

            if player_dict['ffcalc_id'] == str(adp_player['player_id']):
                player_dict['adp_rank'] = adp_player['adp']
                player_dict['adp_round'] = get_adp_round(adp_player)
                break

        # Append the completed player_dict to the players list for the roster
        r['players'].append(player_dict)

df_data = []
# print the results
for roster in rosters_display:
    owner = roster['owner_username']
    for player in roster['players']:
        
        player_data = {
            'Owner': owner,
            'Name': player['name'],
            f'{year} ADP Round': player['adp_round'],
            f'{year} Keeper Round': player[f'{year}_keeper_round'],
            # 'ADP - Keeper Round': player[f'{year}_keeper_round'] - player['adp_round']
        }
        df_data.append(player_data)

df = pd.DataFrame(df_data)


# Define a function to subtract values or return 'NA' if values are not numeric
def subtract_or_na(val1, val2):
    if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
        return val1 - val2
    else:
        return 'NA'

# apply subtract function to df to get the difference between ADP and Keeper Round
df['Keeper Round - ADP Round'] = df.apply(lambda row: subtract_or_na(row[f'{year} Keeper Round'], row[f'{year} ADP Round']), axis=1) 

# Make groupby object
keeper_report_pivot = df.groupby(['Owner', 'Name']).agg({'2023 Keeper Round': 'max', '2023 ADP Round': 'max', 'Keeper Round - ADP Round': 'max'})

# Convert the groupby object to a DataFrame
keeper_report_df = keeper_report_pivot.reset_index()

# Convert the column to a string data type temporarily
keeper_report_df['Keeper Round - ADP Round'] = keeper_report_df['Keeper Round - ADP Round'].astype(str)

# Create a temporary column to help with sorting
def custom_isnumeric(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

keeper_report_df['SortKey'] = keeper_report_df['Keeper Round - ADP Round'].apply(custom_isnumeric)

# Sort the DataFrame by 'SortKey' and 'ADP Round - Keeper Round'
keeper_report_df.sort_values(by=['Owner', 'SortKey', 'Keeper Round - ADP Round'], ascending=[True, False, False], inplace=True)

# Drop the temporary 'SortKey' column
keeper_report_df.drop(columns=['SortKey'], inplace=True)

# Convert the column back to original data types
keeper_report_df['Keeper Round - ADP Round'] = pd.to_numeric(keeper_report_df['Keeper Round - ADP Round'], errors='coerce')

# Replace NaN values with "NA"
keeper_report_df['Keeper Round - ADP Round'] = keeper_report_df['Keeper Round - ADP Round'].fillna('NA')

# Save the DataFrame to an Excel file
filename = f'Weez League {year} Keeper Report.xlsx'

# Create a Pandas Excel writer using XlsxWriter as the engine.
with pd.ExcelWriter(filename) as writer:
    # set the properties to align the text to the center
    keeper_report_df.style.set_properties(**{'text-align': 'center'}).to_excel(writer, sheet_name='Sheet1', index=False)

    # Get the xlsxwriter workbook and worksheet objects
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']

    # Calculate the optimal width for each column and set the column width
    for i, col in enumerate(keeper_report_df.columns):
        column_len = max(keeper_report_df[col].astype(str).apply(len).max(), len(col)) + 2
        worksheet.set_column(i, i, column_len)

print(f"DataFrame saved to {filename}")
