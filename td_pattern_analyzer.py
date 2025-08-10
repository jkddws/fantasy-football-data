import pandas as pd
import nfl_data_py as nfl
import numpy as np
from collections import defaultdict

class HistoricalPatternAnalyzer:
    """Analyze historical patterns for TD lengths and FG distances"""
    
    def __init__(self, season=2024):
        self.season = season
        self.td_patterns = {}
        self.fg_patterns = {}
        
    def load_data(self):
        """Load play-by-play data"""
        print(f"Loading {self.season} play-by-play data...")
        self.pbp_data = nfl.import_pbp_data([self.season])
        # Filter to regular season only
        self.pbp_data = self.pbp_data[self.pbp_data['season_type'] == 'REG']
        print("Data loaded!")
    
    def analyze_td_patterns(self):
        """Analyze TD length patterns for each player"""
        print("\nAnalyzing TD patterns...")
        
        # Get all TDs
        tds = self.pbp_data[self.pbp_data['touchdown'] == 1].copy()
        
        # Use td_player_name which should have the actual scorer
        td_players = tds[tds['td_player_name'].notna()]
        
        for player in td_players['td_player_name'].unique():
            player_td_data = td_players[td_players['td_player_name'] == player]
            
            total_tds = len(player_td_data)
            if total_tds < 3:  # Skip players with very few TDs
                continue
            
            # Count TD lengths
            td_40_49 = len(player_td_data[(player_td_data['yards_gained'] >= 40) & 
                                          (player_td_data['yards_gained'] < 50)])
            td_50_plus = len(player_td_data[player_td_data['yards_gained'] >= 50])
            
            # Calculate percentages
            pct_40_49 = td_40_49 / total_tds
            pct_50_plus = td_50_plus / total_tds
            
            self.td_patterns[player] = {
                'total_tds': total_tds,
                'td_40_49': td_40_49,
                'td_50_plus': td_50_plus,
                'pct_40_49': pct_40_49,
                'pct_50_plus': pct_50_plus,
                'avg_td_length': player_td_data['yards_gained'].mean()
            }
        
        print(f"Analyzed TD patterns for {len(self.td_patterns)} players")
        
        # Show sample of player names for debugging
        print("Sample player names in data:")
        sample_players = list(self.td_patterns.keys())[:10]
        for p in sample_players:
            print(f"  {p}")
    
    def analyze_fg_patterns(self):
        """Analyze FG distance patterns for each kicker"""
        print("\nAnalyzing FG patterns...")
        
        # Get all FG attempts
        fgs = self.pbp_data[(self.pbp_data['field_goal_attempt'] == 1)].copy()
        
        for kicker in fgs['kicker_player_name'].unique():
            if pd.isna(kicker):
                continue
                
            kicker_fgs = fgs[fgs['kicker_player_name'] == kicker]
            made_fgs = kicker_fgs[kicker_fgs['field_goal_result'] == 'made']
            
            total_made = len(made_fgs)
            if total_made < 5:  # Skip kickers with few attempts
                continue
            
            # Count by distance
            fg_0_19 = len(made_fgs[made_fgs['kick_distance'] < 20])
            fg_20_29 = len(made_fgs[(made_fgs['kick_distance'] >= 20) & 
                                    (made_fgs['kick_distance'] < 30)])
            fg_30_39 = len(made_fgs[(made_fgs['kick_distance'] >= 30) & 
                                    (made_fgs['kick_distance'] < 40)])
            fg_40_49 = len(made_fgs[(made_fgs['kick_distance'] >= 40) & 
                                    (made_fgs['kick_distance'] < 50)])
            fg_50_plus = len(made_fgs[made_fgs['kick_distance'] >= 50])
            
            self.fg_patterns[kicker] = {
                'total_made': total_made,
                'fg_0_19': fg_0_19,
                'fg_20_29': fg_20_29,
                'fg_30_39': fg_30_39,
                'fg_40_49': fg_40_49,
                'fg_50_plus': fg_50_plus,
                'pct_0_19': fg_0_19 / total_made,
                'pct_20_29': fg_20_29 / total_made,
                'pct_30_39': fg_30_39 / total_made,
                'pct_40_49': fg_40_49 / total_made,
                'pct_50_plus': fg_50_plus / total_made,
                'avg_distance': made_fgs['kick_distance'].mean()
            }
        
        print(f"Analyzed FG patterns for {len(self.fg_patterns)} kickers")
    
    def get_player_td_bonus_expectation(self, player_name, projected_tds):
        """Calculate expected TD bonus points based on historical patterns"""
        if player_name not in self.td_patterns:
            # Use league average if player not found
            avg_40_49 = 0.05  # ~5% of TDs are 40-49 yards
            avg_50_plus = 0.03  # ~3% of TDs are 50+ yards
        else:
            pattern = self.td_patterns[player_name]
            avg_40_49 = pattern['pct_40_49']
            avg_50_plus = pattern['pct_50_plus']
        
        # Calculate expected bonus points
        expected_40_49_tds = projected_tds * avg_40_49
        expected_50_plus_tds = projected_tds * avg_50_plus
        
        # 40-49 yard TD = 3 bonus points, 50+ = 5 bonus points
        bonus_points = (expected_40_49_tds * 3) + (expected_50_plus_tds * 5)
        
        return round(bonus_points, 1)
    
    def get_kicker_fg_distribution(self, kicker_name, projected_fgs):
        """Calculate expected FG points based on historical patterns"""
        if kicker_name not in self.fg_patterns:
            # Use league average distribution
            distribution = {
                'fg_0_19': projected_fgs * 0.05,
                'fg_20_29': projected_fgs * 0.20,
                'fg_30_39': projected_fgs * 0.35,
                'fg_40_49': projected_fgs * 0.30,
                'fg_50_plus': projected_fgs * 0.10
            }
        else:
            pattern = self.fg_patterns[kicker_name]
            distribution = {
                'fg_0_19': projected_fgs * pattern['pct_0_19'],
                'fg_20_29': projected_fgs * pattern['pct_20_29'],
                'fg_30_39': projected_fgs * pattern['pct_30_39'],
                'fg_40_49': projected_fgs * pattern['pct_40_49'],
                'fg_50_plus': projected_fgs * pattern['pct_50_plus']
            }
        
        # Calculate points (0-49 = 3 points, 50+ = 5 points)
        points = (
            (distribution['fg_0_19'] + distribution['fg_20_29'] + 
             distribution['fg_30_39'] + distribution['fg_40_49']) * 3 +
            distribution['fg_50_plus'] * 5
        )
        
        return round(points, 1)
    
    def print_player_report(self, player_name):
        """Print detailed TD pattern report for a player"""
        if player_name in self.td_patterns:
            pattern = self.td_patterns[player_name]
            print(f"\n{player_name} TD Pattern ({self.season}):")
            print(f"  Total TDs: {pattern['total_tds']}")
            print(f"  40-49 yard TDs: {pattern['td_40_49']} ({pattern['pct_40_49']:.1%})")
            print(f"  50+ yard TDs: {pattern['td_50_plus']} ({pattern['pct_50_plus']:.1%})")
            print(f"  Average TD length: {pattern['avg_td_length']:.1f} yards")
        else:
            print(f"\nNo TD data found for {player_name}")
    
    def print_kicker_report(self, kicker_name):
        """Print detailed FG pattern report for a kicker"""
        if kicker_name in self.fg_patterns:
            pattern = self.fg_patterns[kicker_name]
            print(f"\n{kicker_name} FG Pattern ({self.season}):")
            print(f"  Total FGs made: {pattern['total_made']}")
            print(f"  0-19 yards: {pattern['fg_0_19']} ({pattern['pct_0_19']:.1%})")
            print(f"  20-29 yards: {pattern['fg_20_29']} ({pattern['pct_20_29']:.1%})")
            print(f"  30-39 yards: {pattern['fg_30_39']} ({pattern['pct_30_39']:.1%})")
            print(f"  40-49 yards: {pattern['fg_40_49']} ({pattern['pct_40_49']:.1%})")
            print(f"  50+ yards: {pattern['fg_50_plus']} ({pattern['pct_50_plus']:.1%})")
            print(f"  Average distance: {pattern['avg_distance']:.1f} yards")


# Test the analyzer
if __name__ == "__main__":
    analyzer = HistoricalPatternAnalyzer(season=2024)
    analyzer.load_data()
    analyzer.analyze_td_patterns()
    analyzer.analyze_fg_patterns()
    
    print("\n" + "="*60)
    print("SAMPLE PLAYER REPORTS")
    print("="*60)
    
    # First, let's see what Saquon is called in the data
    print("\nSearching for Saquon in TD data...")
    for player_name in analyzer.td_patterns.keys():
        if 'Saquon' in player_name or 'Barkley' in player_name:
            print(f"Found: {player_name}")
            analyzer.print_player_report(player_name)
    
    # Test with actual names from the data
    print("\nTesting with first few players who had 5+ TDs:")
    top_td_scorers = sorted(analyzer.td_patterns.items(), 
                           key=lambda x: x[1]['total_tds'], 
                           reverse=True)[:5]
    
    for player_name, stats in top_td_scorers:
        analyzer.print_player_report(player_name)
        # Simulate projected TDs
        projected_tds = 0.7  # Example for week 1
        bonus = analyzer.get_player_td_bonus_expectation(player_name, projected_tds)
        print(f"  Expected bonus points for {projected_tds} projected TDs: {bonus}")
    
    # Test kickers
    print("\n" + "="*60)
    print("KICKER REPORTS")
    print("="*60)
    
    print("\nTop kickers by FGs made:")
    top_kickers = sorted(analyzer.fg_patterns.items(), 
                        key=lambda x: x[1]['total_made'], 
                        reverse=True)[:5]
    
    for kicker_name, stats in top_kickers:
        analyzer.print_kicker_report(kicker_name)
        # Simulate projected FGs
        projected_fgs = 2.0  # Example for week 1
        points = analyzer.get_kicker_fg_distribution(kicker_name, projected_fgs)
        print(f"  Expected FG points for {projected_fgs} projected FGs: {points}")
