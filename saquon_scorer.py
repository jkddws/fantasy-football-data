import pandas as pd
import nfl_data_py as nfl
import numpy as np

class FinalLeagueScorer:
    def __init__(self):
        """Initialize with exact league scoring rules"""
        self.scoring_rules = {
            # Passing
            'completion': 1,
            'passing_yard': 1/25,
            'passing_td': 4,
            'interception': -2,
            'sack': -1,
            'passing_300_399_bonus': 3,    # PER GAME
            'passing_400plus_bonus': 5,     # PER GAME
            'passing_td_40_49_bonus': 3,    # PER TD - NOT cumulative
            'passing_td_50plus_bonus': 5,   # PER TD - NOT cumulative
            
            # Rushing
            'rushing_attempt': 0.2,
            'rushing_yard': 1/10,
            'rushing_td': 6,
            'rushing_td_40_49_bonus': 3,    # PER TD - NOT cumulative
            'rushing_td_50plus_bonus': 5,   # PER TD - NOT cumulative
            'rushing_100_199_bonus': 5,     # PER GAME - NOT cumulative
            'rushing_200plus_bonus': 10,    # PER GAME - NOT cumulative
            
            # Receiving
            'reception': 1,
            'receiving_yard': 1/10,
            'receiving_td': 6,
            'receiving_td_40_49_bonus': 3,  # PER TD - NOT cumulative
            'receiving_td_50plus_bonus': 5, # PER TD - NOT cumulative
            'receiving_100_199_bonus': 5,   # PER GAME - NOT cumulative
            'receiving_200plus_bonus': 10,  # PER GAME - NOT cumulative
            
            # Returns
            'return_yard': 1/10,
            'return_td': 5,
            
            # Other
            'fumble_recovered_td': 6,
            'fumble_lost': -2,
            'two_point_conversion': 2
        }
    
    def load_data(self, seasons=[2024]):
        """Load NFL data"""
        print("Loading NFL data...")
        self.weekly_data = nfl.import_weekly_data(seasons)
        self.pbp_data = nfl.import_pbp_data(seasons)
        
        # Filter to regular season
        self.weekly_reg = self.weekly_data[self.weekly_data['season_type'] == 'REG'].copy()
        self.pbp_reg = self.pbp_data[self.pbp_data['season_type'] == 'REG'].copy()
        print("Data loaded!")
    
    def get_fumbles_from_pbp(self, player_name, week):
        """Get fumbles lost from play-by-play data since weekly data is incomplete"""
        week_pbp = self.pbp_reg[self.pbp_reg['week'] == week]
        
        # Check for fumbles by this player
        fumbles = week_pbp[
            (week_pbp['fumbled_1_player_name'] == player_name) & 
            (week_pbp['fumble_lost'] == 1)
        ]
        
        return len(fumbles)
    
    def get_weekly_td_bonuses(self, player_name, week):
        """Calculate TD length bonuses for a specific week - NOT CUMULATIVE"""
        week_pbp = self.pbp_reg[self.pbp_reg['week'] == week]
        player_tds = week_pbp[
            (week_pbp['td_player_name'] == player_name) & 
            (week_pbp['touchdown'] == 1)
        ].copy()
        
        if len(player_tds) == 0:
            return 0, {}
        
        total_bonus = 0
        td_details = []
        
        for _, td in player_tds.iterrows():
            yards = td['yards_gained']
            play_type = td['play_type']
            td_bonus = 0
            
            # NON-CUMULATIVE TD bonuses
            if play_type == 'run':
                if yards >= 50:
                    td_bonus = self.scoring_rules['rushing_td_50plus_bonus']  # 5 points only
                elif yards >= 40:
                    td_bonus = self.scoring_rules['rushing_td_40_49_bonus']   # 3 points only
            elif play_type == 'pass':
                if yards >= 50:
                    td_bonus = self.scoring_rules['receiving_td_50plus_bonus']  # 5 points only
                elif yards >= 40:
                    td_bonus = self.scoring_rules['receiving_td_40_49_bonus']   # 3 points only
            
            if td_bonus > 0:
                td_details.append({
                    'yards': yards,
                    'type': play_type,
                    'bonus': td_bonus
                })
                total_bonus += td_bonus
        
        return total_bonus, {'week': week, 'tds': td_details, 'total_bonus': total_bonus}
    
    def get_weekly_yardage_bonuses(self, rushing_yards, receiving_yards, week):
        """Calculate yardage bonuses for a specific week - CUMULATIVE"""
        bonus = 0
        breakdown = {'week': week}
        
        # Rushing bonuses - CUMULATIVE
        if rushing_yards >= 100:
            bonus += self.scoring_rules['rushing_100_199_bonus']   # 5 pts
            breakdown['rushing_100_199'] = self.scoring_rules['rushing_100_199_bonus']
        if rushing_yards >= 200:
            bonus += self.scoring_rules['rushing_200plus_bonus']   # 10 pts (total 15)
            breakdown['rushing_200plus'] = self.scoring_rules['rushing_200plus_bonus']
        
        # Receiving bonuses - CUMULATIVE  
        if receiving_yards >= 100:
            bonus += self.scoring_rules['receiving_100_199_bonus']  # 5 pts
            breakdown['receiving_100_199'] = self.scoring_rules['receiving_100_199_bonus']
        if receiving_yards >= 200:
            bonus += self.scoring_rules['receiving_200plus_bonus']  # 10 pts (total 15)
            breakdown['receiving_200plus'] = self.scoring_rules['receiving_200plus_bonus']
        
        return bonus, breakdown
    
    def get_weekly_passing_bonuses(self, passing_yards, week):
        """Calculate passing yardage bonuses for a specific week"""
        bonus = 0
        breakdown = {'week': week}
        
        if passing_yards >= 400:
            bonus = self.scoring_rules['passing_400plus_bonus']
            breakdown['passing_400plus'] = bonus
        elif passing_yards >= 300:
            bonus = self.scoring_rules['passing_300_399_bonus']
            breakdown['passing_300_399'] = bonus
        
        return bonus, breakdown
    
    def get_two_point_conversions(self, player_weekly):
        """Get 2-point conversions from available columns"""
        two_pt = 0
        possible_cols = [
            'passing_2pt_conversions',
            'rushing_2pt_conversions', 
            'receiving_2pt_conversions'
        ]
        
        for col in possible_cols:
            if col in player_weekly.columns:
                two_pt += player_weekly[col].fillna(0).sum()
        
        return two_pt
    
    def calculate_weekly_score(self, player_name, week):
        """Calculate fantasy score for a player in a specific week"""
        # Get weekly stats
        player_week = self.weekly_reg[
            (self.weekly_reg['player_name'] == player_name) & 
            (self.weekly_reg['week'] == week)
        ].copy()
        
        if len(player_week) == 0:
            return 0, {}
        
        # Extract stats for this week
        stats = {}
        basic_stats = [
            'completions', 'passing_yards', 'passing_tds', 'interceptions', 'sacks',
            'carries', 'rushing_yards', 'rushing_tds',
            'receptions', 'receiving_yards', 'receiving_tds',
            'fumbles_lost'
        ]
        
        for stat in basic_stats:
            if stat in player_week.columns:
                stats[stat] = player_week[stat].fillna(0).iloc[0]
            else:
                stats[stat] = 0
        
        # Check ALL fumble columns (rushing_fumbles_lost, receiving_fumbles_lost, etc.)
        total_fumbles_lost = 0
        fumble_columns = ['fumbles_lost', 'rushing_fumbles_lost', 'receiving_fumbles_lost', 'sack_fumbles_lost']
        for col in fumble_columns:
            if col in player_week.columns:
                fumbles_in_col = player_week[col].fillna(0).iloc[0]
                if fumbles_in_col > 0:
                    total_fumbles_lost += fumbles_in_col
                    print(f"  NOTE: Found {fumbles_in_col} in {col} for week {week}")
        
        # Also check play-by-play for fumbles as backup
        fumbles_lost_pbp = self.get_fumbles_from_pbp(player_name, week)
        if fumbles_lost_pbp > 0 and total_fumbles_lost == 0:
            total_fumbles_lost = fumbles_lost_pbp
            print(f"  NOTE: Found {fumbles_lost_pbp} fumbles lost in play-by-play data for week {week}")
        
        stats['fumbles_lost'] = total_fumbles_lost
        
        # 2-point conversions
        stats['two_point_conversions'] = self.get_two_point_conversions(player_week)
        
        # Store player_week for debug
        self.debug_player_week = player_week
        
        # Calculate base scoring
        score = 0
        breakdown = {'week': week}
        
        # Passing
        if stats['completions'] > 0:
            breakdown['completions'] = stats['completions'] * self.scoring_rules['completion']
            score += breakdown['completions']
        
        if stats['passing_yards'] > 0:
            breakdown['passing_yards'] = stats['passing_yards'] * self.scoring_rules['passing_yard']
            score += breakdown['passing_yards']
            
            # Weekly passing bonuses
            pass_bonus, _ = self.get_weekly_passing_bonuses(stats['passing_yards'], week)
            if pass_bonus > 0:
                breakdown['passing_yardage_bonus'] = pass_bonus
                score += pass_bonus
        
        if stats['passing_tds'] > 0:
            breakdown['passing_tds'] = stats['passing_tds'] * self.scoring_rules['passing_td']
            score += breakdown['passing_tds']
        
        if stats['interceptions'] > 0:
            breakdown['interceptions'] = stats['interceptions'] * self.scoring_rules['interception']
            score += breakdown['interceptions']
        
        # Only apply sacks for QBs
        if stats['sacks'] > 0:
            player_position = player_week['position'].iloc[0] if 'position' in player_week.columns else None
            if player_position == 'QB':
                breakdown['sacks'] = stats['sacks'] * self.scoring_rules['sack']
                score += breakdown['sacks']
        
        # Rushing
        if stats['carries'] > 0:
            breakdown['carries'] = stats['carries'] * self.scoring_rules['rushing_attempt']
            score += breakdown['carries']
        
        if stats['rushing_yards'] > 0:
            breakdown['rushing_yards'] = stats['rushing_yards'] * self.scoring_rules['rushing_yard']
            score += breakdown['rushing_yards']
        
        if stats['rushing_tds'] > 0:
            breakdown['rushing_tds'] = stats['rushing_tds'] * self.scoring_rules['rushing_td']
            score += breakdown['rushing_tds']
        
        # Receiving
        if stats['receptions'] > 0:
            breakdown['receptions'] = stats['receptions'] * self.scoring_rules['reception']
            score += breakdown['receptions']
        
        if stats['receiving_yards'] > 0:
            breakdown['receiving_yards'] = stats['receiving_yards'] * self.scoring_rules['receiving_yard']
            score += breakdown['receiving_yards']
        
        if stats['receiving_tds'] > 0:
            breakdown['receiving_tds'] = stats['receiving_tds'] * self.scoring_rules['receiving_td']
            score += breakdown['receiving_tds']
        
        # Other
        if stats['two_point_conversions'] > 0:
            breakdown['two_point_conversions'] = stats['two_point_conversions'] * self.scoring_rules['two_point_conversion']
            score += breakdown['two_point_conversions']
        
        if stats['fumbles_lost'] > 0:
            breakdown['fumbles_lost'] = stats['fumbles_lost'] * self.scoring_rules['fumble_lost']
            score += breakdown['fumbles_lost']
        
        # Weekly TD Length Bonuses (NOT cumulative)
        td_bonus, td_breakdown = self.get_weekly_td_bonuses(player_name, week)
        if td_bonus > 0:
            breakdown['td_length_bonuses'] = td_bonus
            breakdown['td_details'] = td_breakdown
            score += td_bonus
        
        # Weekly Yardage Bonuses (NOT cumulative)
        yardage_bonus, yardage_breakdown = self.get_weekly_yardage_bonuses(
            stats['rushing_yards'], stats['receiving_yards'], week
        )
        if yardage_bonus > 0:
            breakdown['yardage_bonuses'] = yardage_bonus
            breakdown['yardage_details'] = yardage_breakdown
            score += yardage_bonus
        
        return score, {
            'week_score': score,
            'stats': stats,
            'breakdown': breakdown
        }

def test_saquon_fixed():
    """Test Saquon with all fixes applied"""
    scorer = FinalLeagueScorer()
    scorer.load_data([2024])
    
    print("=== SAQUON BARKLEY 2024 - FIXED SCORING ===\n")
    
    # Expected scores for each week
    expected_scores = {
        1: 45.0,
        2: 22.0,
        3: 50.0,
        4: 15.6,
        6: 11.0,
        7: 35.1,
        8: 21.5,
        9: 43.3,
        10: 12.6,
        11: 44.0,
        12: 77.4,
        13: 31.3,
        14: 23.4,
        15: 13.2,
        16: 44.8,
        17: 30.1
    }
    
    player_weeks = scorer.weekly_reg[scorer.weekly_reg['player_name'] == 'S.Barkley']['week'].unique()
    
    total_calculated = 0
    total_expected = 0
    
    for week in sorted(player_weeks):
        score, details = scorer.calculate_weekly_score('S.Barkley', week)
        expected = expected_scores.get(week, 0)
        
        print(f"Week {week}: {score:.1f} (expected: {expected:.1f}) - Diff: {expected - score:.1f}")
        
        total_calculated += score
        total_expected += expected
    
    print(f"\n{'='*50}")
    print(f"TOTAL CALCULATED: {total_calculated:.1f}")
    print(f"TOTAL EXPECTED: {total_expected:.1f} (should be 520.3)")
    print(f"DIFFERENCE: {total_expected - total_calculated:.1f}")

def debug_all_problem_weeks():
    """Deep dive into all weeks with discrepancies"""
    scorer = FinalLeagueScorer()
    scorer.load_data([2024])
    
    problem_weeks = [1, 3, 10, 12, 13, 16]
    
    for week in problem_weeks:
        print(f"\n=== WEEK {week} ANALYSIS ===")
        
        # Get weekly data
        week_data = scorer.weekly_reg[
            (scorer.weekly_reg['player_name'] == 'S.Barkley') & 
            (scorer.weekly_reg['week'] == week)
        ]
        
        if not week_data.empty:
            # Check all fumble columns
            print("Fumble-related columns:")
            fumble_cols = ['fumbles', 'fumbles_lost', 'rushing_fumbles', 'rushing_fumbles_lost', 
                          'receiving_fumbles', 'receiving_fumbles_lost', 'sack_fumbles', 'sack_fumbles_lost']
            for col in fumble_cols:
                if col in week_data.columns:
                    val = week_data[col].iloc[0]
                    if pd.notna(val) and val != 0:
                        print(f"  {col}: {val}")
            
            # Check special teams
            special_cols = ['special_teams_tds', 'kick_returns', 'kick_return_yards', 
                           'punt_returns', 'punt_return_yards']
            print("\nSpecial teams columns:")
            found_special = False
            for col in special_cols:
                if col in week_data.columns:
                    val = week_data[col].iloc[0]
                    if pd.notna(val) and val != 0:
                        print(f"  {col}: {val}")
                        found_special = True
            if not found_special:
                print("  No special teams stats found")
            
            # Check play-by-play for TDs
            week_pbp = scorer.pbp_reg[scorer.pbp_reg['week'] == week]
            saquon_tds = week_pbp[
                (week_pbp['td_player_name'] == 'S.Barkley') & 
                (week_pbp['touchdown'] == 1)
            ]
            print(f"\nTouchdowns ({len(saquon_tds)} total):")
            for _, td in saquon_tds.iterrows():
                print(f"  {td['play_type']} for {td['yards_gained']} yards")
            
            # Calculate what we get vs expected
            score, details = scorer.calculate_weekly_score('S.Barkley', week)
            expected = {1: 45.0, 3: 50.0, 10: 12.6, 12: 77.4, 13: 31.3, 16: 44.8}[week]
            print(f"\nCalculated: {score:.1f}, Expected: {expected:.1f}, Diff: {expected - score:.1f}")

def find_all_fumbles():
    """Find ALL fumbles for Saquon in 2024"""
    scorer = FinalLeagueScorer()
    scorer.load_data([2024])
    
    print("=== SEARCHING FOR ALL SAQUON FUMBLES ===\n")
    
    # Check play-by-play for ALL fumbles (lost or not)
    all_fumbles = scorer.pbp_reg[
        (scorer.pbp_reg['fumbled_1_player_name'] == 'S.Barkley') |
        (scorer.pbp_reg['fumbled_2_player_name'] == 'S.Barkley' if 'fumbled_2_player_name' in scorer.pbp_reg.columns else False)
    ]
    
    print(f"Total fumbles found: {len(all_fumbles)}")
    for _, fumble in all_fumbles.iterrows():
        print(f"\nWeek {fumble['week']}:")
        print(f"  Fumble lost: {fumble.get('fumble_lost', 'N/A')}")
        print(f"  Recovery team: {fumble.get('fumble_recovery_1_team', 'N/A')}")
        print(f"  Play: {fumble['desc'][:100]}...")
    
    # Check weekly data for fumbles
    print("\n=== WEEKLY DATA FUMBLE COLUMNS ===")
    saquon_all_weeks = scorer.weekly_reg[scorer.weekly_reg['player_name'] == 'S.Barkley']
    
    fumble_cols = ['fumbles', 'fumbles_lost', 'rushing_fumbles', 'rushing_fumbles_lost', 
                   'receiving_fumbles', 'receiving_fumbles_lost']
    
    for week in sorted(saquon_all_weeks['week'].unique()):
        week_data = saquon_all_weeks[saquon_all_weeks['week'] == week]
        fumbles_found = False
        for col in fumble_cols:
            if col in week_data.columns:
                val = week_data[col].iloc[0]
                if pd.notna(val) and val > 0:
                    if not fumbles_found:
                        print(f"\nWeek {week}:")
                        fumbles_found = True
                    print(f"  {col}: {val}")

if __name__ == "__main__":
    test_saquon_fixed()
    print("\n" + "="*70 + "\n")
    find_all_fumbles()
    print("\n" + "="*70 + "\n")
    debug_all_problem_weeks()
