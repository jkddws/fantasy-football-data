import nfl_data_py as nfl
import pandas as pd

# Load 2024 play-by-play data
print("Loading 2024 play-by-play data...")
pbp_2024 = nfl.import_pbp_data([2024])

print(f"Loaded {len(pbp_2024)} plays from 2024 season")
print(f"Columns: {pbp_2024.columns.tolist()[:20]}...")  # Show first 20 columns

# Find TD length bonuses for specific players
def get_player_td_bonuses(pbp_df, player_name):
    """Calculate TD bonuses for a specific player"""
    
    # Find all TDs by this player
    player_tds = pbp_df[
        (pbp_df['td_player_name'] == player_name) &
        (pbp_df['touchdown'] == 1)
    ].copy()
    
    if len(player_tds) == 0:
        print(f"No TDs found for {player_name}")
        return None
    
    # Calculate bonuses
    tds_40plus = sum(player_tds['yards_gained'] >= 40)
    tds_50plus = sum(player_tds['yards_gained'] >= 50)
    
    bonus_points = (tds_40plus * 3) + (tds_50plus * 5)
    
    return {
        'player': player_name,
        'total_tds': len(player_tds),
        'tds_40plus': tds_40plus,
        'tds_50plus': tds_50plus,
        'td_bonus_points': bonus_points
    }

# Test with Saquon Barkley
barkley_bonuses = get_player_td_bonuses(pbp_2024, 'S.Barkley')
if barkley_bonuses:
    print("\nSaquon Barkley TD Bonuses:")
    for key, value in barkley_bonuses.items():
        print(f"  {key}: {value}")

# Get QB sacks
print("\nCalculating QB sacks...")
qb_sacks = pbp_2024[pbp_2024['sack'] == 1].groupby('passer_player_name').size().reset_index(name='times_sacked')
qb_sacks['sack_penalty'] = qb_sacks['times_sacked'] * -1
print(qb_sacks.head())

# Save to CSV
qb_sacks.to_csv('qb_sacks_2024.csv', index=False)
print("Saved QB sacks to qb_sacks_2024.csv")
