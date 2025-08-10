import pandas as pd
import nfl_data_py as nfl
import numpy as np
from collections import defaultdict

class DefenseReturnAnalyzer:
    """Analyze return yards allowed by each team"""
    
    def __init__(self, season=2024):
        self.season = season
        self.return_yards_allowed = {}
        self.team_return_yards = {}
        self.league_avg_return_yards = 0
        
    def load_data(self):
        """Load play-by-play data"""
        print(f"Loading {self.season} return data...")
        self.pbp_data = nfl.import_pbp_data([self.season])
        self.pbp_data = self.pbp_data[self.pbp_data['season_type'] == 'REG']
        print("Data loaded!")
    
    def analyze_return_yards(self):
        """Analyze return yards allowed by each team"""
        print("\nAnalyzing return yards allowed...")
        
        # Get all kickoff and punt returns
        returns = self.pbp_data[
            (self.pbp_data['kickoff_attempt'] == 1) | 
            (self.pbp_data['punt_attempt'] == 1)
        ].copy()
        
        # Track return yards by kicking team (they "allowed" the return)
        team_games = defaultdict(int)
        team_return_yards_allowed = defaultdict(float)
        
        for _, play in returns.iterrows():
            if pd.notna(play['return_yards']) and play['return_yards'] > 0:
                # The kicking/punting team "allowed" these return yards
                kicking_team = play['posteam']  # Team that kicked/punted
                if pd.notna(kicking_team):
                    team_return_yards_allowed[kicking_team] += play['return_yards']
        
        # Count games played by each team
        all_games = self.pbp_data.groupby(['game_id', 'home_team', 'away_team']).first().reset_index()
        for _, game in all_games.iterrows():
            team_games[game['home_team']] += 1
            team_games[game['away_team']] += 1
        
        # Calculate average return yards allowed per game
        for team in team_return_yards_allowed:
            if team in team_games and team_games[team] > 0:
                avg_allowed = team_return_yards_allowed[team] / team_games[team]
                self.return_yards_allowed[team] = round(avg_allowed, 1)
        
        # Calculate league average
        if len(self.return_yards_allowed) > 0:
            self.league_avg_return_yards = round(
                sum(self.return_yards_allowed.values()) / len(self.return_yards_allowed), 1
            )
        
        print(f"League average return yards allowed per game: {self.league_avg_return_yards}")
        
        # Also track return yards BY each team's defense/ST
        team_return_yards_gained = defaultdict(float)
        
        for _, play in returns.iterrows():
            if pd.notna(play['return_yards']) and play['return_yards'] > 0:
                # The returning team gained these yards
                returning_team = play['defteam']  # Team that returned
                if pd.notna(returning_team):
                    team_return_yards_gained[returning_team] += play['return_yards']
        
        # Calculate average return yards gained per game
        for team in team_return_yards_gained:
            if team in team_games and team_games[team] > 0:
                avg_gained = team_return_yards_gained[team] / team_games[team]
                self.team_return_yards[team] = round(avg_gained, 1)
    
    def get_expected_return_yards(self, defense_team, opponent_team):
        """Get expected return yards for a defense against a specific opponent"""
        
        # Method 1: Use opponent's average return yards allowed
        if opponent_team in self.return_yards_allowed:
            return self.return_yards_allowed[opponent_team]
        
        # Method 2: Use league average if no specific data
        return self.league_avg_return_yards
    
    def get_defense_return_tendency(self, defense_team):
        """Get a defense's tendency to gain return yards"""
        if defense_team in self.team_return_yards:
            return self.team_return_yards[defense_team]
        return self.league_avg_return_yards
    
    def print_report(self):
        """Print analysis report"""
        print("\n" + "="*60)
        print("RETURN YARDS ANALYSIS")
        print("="*60)
        
        print("\nTeams that allow the MOST return yards (worst for opposing DST):")
        sorted_allowed = sorted(self.return_yards_allowed.items(), 
                               key=lambda x: x[1], reverse=True)[:5]
        for team, yards in sorted_allowed:
            print(f"  {team}: {yards} yards/game allowed")
        
        print("\nTeams that allow the LEAST return yards (best for opposing DST):")
        sorted_allowed_least = sorted(self.return_yards_allowed.items(), 
                                     key=lambda x: x[1])[:5]
        for team, yards in sorted_allowed_least:
            print(f"  {team}: {yards} yards/game allowed")
        
        print("\nBest return teams (gain most return yards):")
        sorted_gained = sorted(self.team_return_yards.items(), 
                              key=lambda x: x[1], reverse=True)[:5]
        for team, yards in sorted_gained:
            print(f"  {team}: {yards} yards/game gained")
    
    def get_week_matchups(self, week, season=2025):
        """Get expected return yards for all DSTs in a given week"""
        # This would need the 2025 schedule
        # For now, return example matchups
        example_matchups = {
            'MIN': 'NYG',
            'PHI': 'GB',
            'PIT': 'ATL',
            'DEN': 'SEA',
            'CIN': 'NE'
        }
        
        projections = {}
        for defense, opponent in example_matchups.items():
            expected_yards = self.get_expected_return_yards(defense, opponent)
            projections[defense] = {
                'opponent': opponent,
                'expected_return_yards': expected_yards,
                'expected_return_points': round(expected_yards / 10, 1)
            }
        
        return projections


# Test the analyzer
if __name__ == "__main__":
    analyzer = DefenseReturnAnalyzer(season=2024)
    analyzer.load_data()
    analyzer.analyze_return_yards()
    analyzer.print_report()
    
    # Test specific matchup
    print("\n" + "="*60)
    print("SPECIFIC MATCHUP EXAMPLES")
    print("="*60)
    
    test_matchups = [
        ('MIN', 'DET'),
        ('PHI', 'DAL'),
        ('PIT', 'BAL')
    ]
    
    for defense, opponent in test_matchups:
        yards = analyzer.get_expected_return_yards(defense, opponent)
        points = round(yards / 10, 1)
        print(f"\n{defense} vs {opponent}:")
        print(f"  Expected return yards: {yards}")
        print(f"  Expected return points: {points}")
    
    # Show Week 1 projections example
    print("\n" + "="*60)
    print("WEEK 1 RETURN PROJECTIONS (Example)")
    print("="*60)
    
    week1_projections = analyzer.get_week_matchups(1)
    for defense, proj in sorted(week1_projections.items(), 
                               key=lambda x: x[1]['expected_return_points'], 
                               reverse=True):
        print(f"{defense} vs {proj['opponent']}: "
              f"{proj['expected_return_yards']} yards "
              f"({proj['expected_return_points']} points)")
