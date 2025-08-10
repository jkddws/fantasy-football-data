import nfl_data_py as nfl
import pandas as pd

print("Loading data...")
pbp = nfl.import_pbp_data([2024])
weekly = nfl.import_weekly_data([2024])

# Get Saquon's stats
saquon = weekly[weekly['player_name'] == 'S.Barkley']
saquon_total = saquon.groupby('player_name').agg({
    'rushing_yards': 'sum',
    'rushing_tds': 'sum',
    'receiving_yards': 'sum',
    'receiving_tds': 'sum',
    'receptions': 'sum',
    'carries': 'sum'
}).reset_index()

# Get TD bonuses
saquon_tds = pbp[(pbp['td_player_name'] == 'S.Barkley') & (pbp['touchdown'] == 1)]
td_40plus = sum(saquon_tds['yards_gained'] >= 40)
td_50plus = sum(saquon_tds['yards_gained'] >= 50)

# Calculate score
stats = saquon_total.iloc[0]
score = 0
score += stats['carries'] * 0.2
score += stats['rushing_yards'] / 10
score += stats['rushing_tds'] * 6
score += stats['receptions'] * 1
score += stats['receiving_yards'] / 10
score += stats['receiving_tds'] * 6
score += (td_40plus * 3) + (td_50plus * 5)
if stats['rushing_yards'] >= 2000:
    score += 10
elif stats['rushing_yards'] >= 1000:
    score += 5

print(f"\nSaquon Barkley Stats:")
print(f"Rushing: {stats['carries']} att, {stats['rushing_yards']} yds, {stats['rushing_tds']} TD")
print(f"Receiving: {stats['receptions']} rec, {stats['receiving_yards']} yds, {stats['receiving_tds']} TD")
print(f"TD Bonuses: {td_40plus} 40+, {td_50plus} 50+ = {(td_40plus * 3) + (td_50plus * 5)} pts")
print(f"\nTotal Score: {score:.1f} pts (Expected: 520.3)")