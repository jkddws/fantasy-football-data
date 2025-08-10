import nfl_data_py as nfl
import pandas as pd

print("Loading data...")
pbp = nfl.import_pbp_data([2024])
weekly = nfl.import_weekly_data([2024])

# Get Saquon's stats
saquon = weekly[weekly['player_name'] == 'Saquon Barkley']
saquon_total = saquon.groupby('player_name').agg({
    'rushing_yards': 'sum',
    'rushing_tds': 'sum',
    'receiving_yards': 'sum',
    'receiving_tds': 'sum',
    'receptions': 'sum',
    'carries': 'sum'
}).iloc[0]

# Get TD bonuses
saquon_tds = pbp[(pbp['td_player_name'] == 'S.Barkley') & (pbp['touchdown'] == 1)]
td_40plus = sum(saquon_tds['yards_gained'] >= 40)
td_50plus = sum(saquon_tds['yards_gained'] >= 50)

# Calculate score
score = 0
score += saquon_total['carries'] * 0.2
score += saquon_total['rushing_yards'] / 10
score += saquon_total['rushing_tds'] * 6
score += saquon_total['receptions'] * 1
score += saquon_total['receiving_yards'] / 10
score += saquon_total['receiving_tds'] * 6
score += (td_40plus * 3) + (td_50plus * 5)
if saquon_total['rushing_yards'] >= 200:
    score += 10

print(f"Saquon Barkley: {score:.1f} pts (Expected: 520.3)")
