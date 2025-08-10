import nfl_data_py as nfl

pbp = nfl.import_pbp_data([2024])

# Filter to regular season only
reg_pbp = pbp[(pbp['season_type'] == 'REG') & (pbp['week'] <= 17)]

# Get Saquon TDs in regular season
saquon_tds = reg_pbp[(reg_pbp['td_player_name'] == 'S.Barkley') & (reg_pbp['touchdown'] == 1)]

print(f"Total TDs: {len(saquon_tds)}")
print(f"40+ yard TDs: {sum(saquon_tds['yards_gained'] >= 40)}")
print(f"50+ yard TDs: {sum(saquon_tds['yards_gained'] >= 50)}")

td_bonus = sum(saquon_tds['yards_gained'] >= 40) * 3 + sum(saquon_tds['yards_gained'] >= 50) * 5
print(f"TD bonus points: {td_bonus}")

# Show each TD
print("\nAll TDs:")
for _, td in saquon_tds.iterrows():
    print(f"Week {td['week']}: {td['yards_gained']} yards")
