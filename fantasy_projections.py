import pandas as pd
import nfl_data_py as nfl
import numpy as np
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
from typing import Dict, List, Tuple
from collections import defaultdict

class HistoricalPatternAnalyzer:
    """Analyze historical patterns for TD lengths and FG distances"""
    
    def __init__(self, season=2024):
        self.season = season
        self.td_patterns = {}
        self.fg_patterns = {}
        self.data_loaded = False
        
    def load_data(self):
        """Load play-by-play data"""
        if not self.data_loaded:
            print(f"Loading {self.season} historical data for bonus calculations...")
            self.pbp_data = nfl.import_pbp_data([self.season])
            self.pbp_data = self.pbp_data[self.pbp_data['season_type'] == 'REG']
            self.analyze_td_patterns()
            self.analyze_fg_patterns()
            self.data_loaded = True
    
    def analyze_td_patterns(self):
        """Analyze TD length patterns for each player"""
        tds = self.pbp_data[self.pbp_data['touchdown'] == 1].copy()
        td_players = tds[tds['td_player_name'].notna()]
        
        for player in td_players['td_player_name'].unique():
            player_td_data = td_players[td_players['td_player_name'] == player]
            total_tds = len(player_td_data)
            
            if total_tds < 3:
                continue
            
            td_40_49 = len(player_td_data[(player_td_data['yards_gained'] >= 40) & 
                                          (player_td_data['yards_gained'] < 50)])
            td_50_plus = len(player_td_data[player_td_data['yards_gained'] >= 50])
            
            self.td_patterns[player] = {
                'pct_40_49': td_40_49 / total_tds,
                'pct_50_plus': td_50_plus / total_tds
            }
    
    def analyze_fg_patterns(self):
        """Analyze FG distance patterns for each kicker"""
        fgs = self.pbp_data[(self.pbp_data['field_goal_attempt'] == 1)].copy()
        
        for kicker in fgs['kicker_player_name'].unique():
            if pd.isna(kicker):
                continue
                
            kicker_fgs = fgs[fgs['kicker_player_name'] == kicker]
            made_fgs = kicker_fgs[kicker_fgs['field_goal_result'] == 'made']
            total_made = len(made_fgs)
            
            if total_made < 5:
                continue
            
            self.fg_patterns[kicker] = {
                'pct_0_29': len(made_fgs[made_fgs['kick_distance'] < 30]) / total_made,
                'pct_30_39': len(made_fgs[(made_fgs['kick_distance'] >= 30) & 
                                         (made_fgs['kick_distance'] < 40)]) / total_made,
                'pct_40_49': len(made_fgs[(made_fgs['kick_distance'] >= 40) & 
                                         (made_fgs['kick_distance'] < 50)]) / total_made,
                'pct_50_plus': len(made_fgs[made_fgs['kick_distance'] >= 50]) / total_made
            }
    
    def get_player_td_bonus(self, player_name, projected_tds):
        """Calculate expected TD bonus points"""
        # Convert name format (e.g., "Joe Burrow" to "J.Burrow")
        if ' ' in player_name:
            parts = player_name.split()
            short_name = f"{parts[0][0]}.{parts[1]}"
            if short_name in self.td_patterns:
                pattern = self.td_patterns[short_name]
                bonus = (projected_tds * pattern['pct_40_49'] * 3 + 
                        projected_tds * pattern['pct_50_plus'] * 5)
                return round(bonus, 1)
        
        # Default percentages if player not found
        return round(projected_tds * 0.05 * 3 + projected_tds * 0.03 * 5, 1)
    
    def get_kicker_points(self, kicker_name, projected_fgs, projected_pats):
        """Calculate expected kicker points based on distance distribution"""
        pat_points = projected_pats * 1
        
        # Convert name format
        if ' ' in kicker_name:
            parts = kicker_name.split()
            short_name = f"{parts[0][0]}.{parts[1]}"
            if short_name in self.fg_patterns:
                pattern = self.fg_patterns[short_name]
                fg_points = (projected_fgs * (pattern['pct_0_29'] + pattern['pct_30_39'] + 
                                             pattern['pct_40_49']) * 3 +
                           projected_fgs * pattern['pct_50_plus'] * 5)
                return round(pat_points + fg_points, 1)
        
        # Default distribution if kicker not found
        fg_points = projected_fgs * 3.3  # Assume average
        return round(pat_points + fg_points, 1)


class DefenseReturnAnalyzer:
    """Analyze return yards allowed by each team"""
    
    def __init__(self, season=2024):
        self.season = season
        self.return_yards_allowed = {}
        self.data_loaded = False
        self.league_avg = 62.5
        
    def load_data(self):
        """Load return yards data"""
        if not self.data_loaded:
            print("Loading historical return yards data...")
            pbp_data = nfl.import_pbp_data([self.season])
            pbp_data = pbp_data[pbp_data['season_type'] == 'REG']
            
            # Analyze return yards allowed
            returns = pbp_data[
                (pbp_data['kickoff_attempt'] == 1) | 
                (pbp_data['punt_attempt'] == 1)
            ].copy()
            
            team_games = defaultdict(int)
            team_return_yards_allowed = defaultdict(float)
            
            # Count return yards allowed
            for _, play in returns.iterrows():
                if pd.notna(play['return_yards']) and play['return_yards'] > 0:
                    kicking_team = play['posteam']
                    if pd.notna(kicking_team):
                        team_return_yards_allowed[kicking_team] += play['return_yards']
            
            # Count games
            all_games = pbp_data.groupby(['game_id', 'home_team', 'away_team']).first().reset_index()
            for _, game in all_games.iterrows():
                team_games[game['home_team']] += 1
                team_games[game['away_team']] += 1
            
            # Calculate averages
            for team in team_return_yards_allowed:
                if team in team_games and team_games[team] > 0:
                    avg_allowed = team_return_yards_allowed[team] / team_games[team]
                    self.return_yards_allowed[team] = round(avg_allowed, 1)
            
            self.data_loaded = True
    
    def get_expected_return_yards(self, opponent_team):
        """Get expected return yards against a specific opponent"""
        if opponent_team in self.return_yards_allowed:
            return self.return_yards_allowed[opponent_team]
        return self.league_avg


class FinalLeagueScorer:
    """Base scorer for offensive positions (QB, RB, WR, TE)"""
    def __init__(self):
        self.scoring_rules = {
            # Passing
            'completion': 1,
            'passing_yard': 1/25,
            'passing_td': 4,
            'interception': -2,
            'sack': -1,
            'passing_300_399_bonus': 3,
            'passing_400plus_bonus': 5,
            'passing_td_40_49_bonus': 3,
            'passing_td_50plus_bonus': 5,
            
            # Rushing
            'rushing_attempt': 0.2,
            'rushing_yard': 1/10,
            'rushing_td': 6,
            'rushing_td_40_49_bonus': 3,
            'rushing_td_50plus_bonus': 5,
            'rushing_100_199_bonus': 5,
            'rushing_200plus_bonus': 10,
            
            # Receiving
            'reception': 1,
            'receiving_yard': 1/10,
            'receiving_td': 6,
            'receiving_td_40_49_bonus': 3,
            'receiving_td_50plus_bonus': 5,
            'receiving_100_199_bonus': 5,
            'receiving_200plus_bonus': 10,
            
            # Returns
            'return_yard': 1/10,
            'return_td': 5,
            
            # Other
            'fumble_recovered_td': 6,
            'fumble_lost': -2,
            'two_point_conversion': 2
        }
    
    def calculate_projected_score(self, proj_data: Dict) -> float:
        """Calculate fantasy score from projection data"""
        score = 0
        
        # Passing
        if 'completions' in proj_data:
            score += proj_data['completions'] * self.scoring_rules['completion']
        if 'passing_yards' in proj_data:
            yards = proj_data['passing_yards']
            score += yards * self.scoring_rules['passing_yard']
            # Yardage bonuses
            if yards >= 400:
                score += self.scoring_rules['passing_400plus_bonus']
            elif yards >= 300:
                score += self.scoring_rules['passing_300_399_bonus']
        if 'passing_tds' in proj_data:
            score += proj_data['passing_tds'] * self.scoring_rules['passing_td']
        if 'interceptions' in proj_data:
            score += proj_data['interceptions'] * self.scoring_rules['interception']
        if 'sacks' in proj_data:
            score += proj_data['sacks'] * self.scoring_rules['sack']
        
        # Rushing
        if 'rushing_attempts' in proj_data:
            score += proj_data['rushing_attempts'] * self.scoring_rules['rushing_attempt']
        if 'rushing_yards' in proj_data:
            yards = proj_data['rushing_yards']
            score += yards * self.scoring_rules['rushing_yard']
            # Yardage bonuses (cumulative)
            if yards >= 100:
                score += self.scoring_rules['rushing_100_199_bonus']
            if yards >= 200:
                score += self.scoring_rules['rushing_200plus_bonus']
        if 'rushing_tds' in proj_data:
            score += proj_data['rushing_tds'] * self.scoring_rules['rushing_td']
        
        # Receiving
        if 'receptions' in proj_data:
            score += proj_data['receptions'] * self.scoring_rules['reception']
        if 'receiving_yards' in proj_data:
            yards = proj_data['receiving_yards']
            score += yards * self.scoring_rules['receiving_yard']
            # Yardage bonuses (cumulative)
            if yards >= 100:
                score += self.scoring_rules['receiving_100_199_bonus']
            if yards >= 200:
                score += self.scoring_rules['receiving_200plus_bonus']
        if 'receiving_tds' in proj_data:
            score += proj_data['receiving_tds'] * self.scoring_rules['receiving_td']
        
        # Other
        if 'fumbles_lost' in proj_data:
            score += proj_data['fumbles_lost'] * self.scoring_rules['fumble_lost']
        
        return round(score, 1)


class KickerScorer:
    """Scorer for kickers"""
    def __init__(self):
        self.scoring_rules = {
            'pat_made': 1,
            'fg_0_19': 3,
            'fg_20_29': 3,
            'fg_30_39': 3,
            'fg_40_49': 3,
            'fg_50plus': 5
        }
    
    def calculate_projected_score(self, proj_data: Dict) -> float:
        """Calculate kicker fantasy score"""
        score = 0
        
        if 'pat' in proj_data:
            score += proj_data['pat'] * self.scoring_rules['pat_made']
        
        # Field goals by distance
        if 'fg_0_19' in proj_data:
            score += proj_data['fg_0_19'] * self.scoring_rules['fg_0_19']
        if 'fg_20_29' in proj_data:
            score += proj_data['fg_20_29'] * self.scoring_rules['fg_20_29']
        if 'fg_30_39' in proj_data:
            score += proj_data['fg_30_39'] * self.scoring_rules['fg_30_39']
        if 'fg_40_49' in proj_data:
            score += proj_data['fg_40_49'] * self.scoring_rules['fg_40_49']
        if 'fg_50plus' in proj_data:
            score += proj_data['fg_50plus'] * self.scoring_rules['fg_50plus']
        
        # If only total FG is provided, assume distribution
        if 'fg' in proj_data and 'fg_0_19' not in proj_data:
            # Assume average distribution
            total_fg = proj_data['fg']
            score += total_fg * 3.2  # Weighted average
        
        return round(score, 1)


class DefenseScorer:
    """Scorer for team defenses"""
    def __init__(self):
        self.scoring_rules = {
            'sack': 1,
            'interception': 2,
            'fumble_recovery': 2,
            'fumble_forced': 1,
            'safety': 2,
            'defensive_td': 6,
            'blocked_kick': 2,
            'return_td': 6,
            'return_yard': 1/10,
            'two_point_return': 2
        }
        
        self.points_allowed_scoring = {
            (0, 0): 10,
            (1, 6): 7,
            (7, 13): 4,
            (14, 20): 1,
            (21, 27): 0,
            (28, 34): -1,
            (35, 100): -4
        }
        
        self.yards_allowed_bonus = {
            (0, 99): 3
        }
    
    def calculate_projected_score(self, proj_data: Dict) -> float:
        """Calculate defense fantasy score"""
        score = 0
        
        # Basic defensive stats
        score += proj_data.get('sacks', 0) * self.scoring_rules['sack']
        score += proj_data.get('interceptions', 0) * self.scoring_rules['interception']
        score += proj_data.get('fumble_recoveries', 0) * self.scoring_rules['fumble_recovery']
        score += proj_data.get('fumbles_forced', 0) * self.scoring_rules['fumble_forced']
        score += proj_data.get('safeties', 0) * self.scoring_rules['safety']
        score += proj_data.get('defensive_tds', 0) * self.scoring_rules['defensive_td']
        score += proj_data.get('blocked_kicks', 0) * self.scoring_rules['blocked_kick']
        
        # Points allowed
        pa = proj_data.get('points_allowed', 20)  # Default to 20 if missing
        for (low, high), points in self.points_allowed_scoring.items():
            if low <= pa <= high:
                score += points
                break
        
        # Yards allowed bonus
        ya = proj_data.get('yards_allowed', 300)  # Default to 300 if missing
        for (low, high), points in self.yards_allowed_bonus.items():
            if low <= ya <= high:
                score += points
                break
        
        return round(score, 1)


class FantasyProsProjectionScraper:
    """Scrape projections from FantasyPros"""
    
    def __init__(self, use_cached=True):
        self.base_url = "https://www.fantasypros.com/nfl/projections"
        self.use_cached = use_cached
        self.cache_dir = "projection_cache"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def safe_float(self, value):
        """Safely convert string to float"""
        try:
            return float(value.strip())
        except:
            return 0.0
    
    def get_projections(self, position: str, week: int, force_refresh: bool = False) -> pd.DataFrame:
        """Get projections for a position and week"""
        projections = self.scrape_projections(position, week)
        return pd.DataFrame(projections)
    
    def scrape_projections(self, position: str, week: int) -> list:
        """Scrape projections and return as list of dicts"""
        url = f"{self.base_url}/{position.lower()}.php?week={week}"
        print(f"Scraping {position} from: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the main table
            tables = soup.find_all('table')
            main_table = None
            
            # Debug for kickers
            if position == 'K':
                print(f"Found {len(tables)} tables on kicker page")
            
            for table in tables:
                if table.find('a', class_='player-name'):
                    main_table = table
                    break
            
            if not main_table:
                print(f"No player table found for {position}")
                return []
            
            # Parse the data rows
            tbody = main_table.find('tbody')
            if not tbody:
                return []
            
            projections = []
            
            for row in tbody.find_all('tr'):
                cells = row.find_all('td')
                if not cells:
                    continue
                
                # Extract data
                row_data = {}
                
                # First cell has player name and team
                first_cell = cells[0]
                player_link = first_cell.find('a', class_='player-name')
                if player_link:
                    row_data['player'] = player_link.text.strip()
                    
                    # Try to get team from the cell text
                    cell_text = first_cell.get_text(strip=True)
                    # Remove player name to find team
                    remaining = cell_text.replace(row_data['player'], '').strip()
                    if remaining:
                        # Team is usually the first word after player name
                        team_parts = remaining.split()
                        if team_parts:
                            row_data['team'] = team_parts[0]
                    else:
                        row_data['team'] = ''
                    
                    # Get the rest of the stats
                    stat_cells = cells[1:]  # Skip the player cell
                    
                    # Map stats based on position
                    if position == 'QB' and len(stat_cells) >= 10:
                        row_data.update({
                            'passing_attempts': self.safe_float(stat_cells[0].text),
                            'completions': self.safe_float(stat_cells[1].text),
                            'passing_yards': self.safe_float(stat_cells[2].text),
                            'passing_tds': self.safe_float(stat_cells[3].text),
                            'interceptions': self.safe_float(stat_cells[4].text),
                            'rushing_attempts': self.safe_float(stat_cells[5].text),
                            'rushing_yards': self.safe_float(stat_cells[6].text),
                            'rushing_tds': self.safe_float(stat_cells[7].text),
                            'fumbles_lost': self.safe_float(stat_cells[8].text),
                            'position': 'QB'
                        })
                    elif position == 'RB' and len(stat_cells) >= 8:
                        row_data.update({
                            'rushing_attempts': self.safe_float(stat_cells[0].text),
                            'rushing_yards': self.safe_float(stat_cells[1].text),
                            'rushing_tds': self.safe_float(stat_cells[2].text),
                            'receptions': self.safe_float(stat_cells[3].text),
                            'receiving_yards': self.safe_float(stat_cells[4].text),
                            'receiving_tds': self.safe_float(stat_cells[5].text),
                            'fumbles_lost': self.safe_float(stat_cells[6].text),
                            'position': 'RB'
                        })
                    elif position in ['WR', 'TE'] and len(stat_cells) >= 4:
                        # TE page has fewer columns - just REC, YDS, TDS, FL
                        row_data.update({
                            'receptions': self.safe_float(stat_cells[0].text),
                            'receiving_yards': self.safe_float(stat_cells[1].text),
                            'receiving_tds': self.safe_float(stat_cells[2].text),
                            'rushing_attempts': 0,  # TEs rarely rush
                            'rushing_yards': 0,
                            'rushing_tds': 0,
                            'fumbles_lost': self.safe_float(stat_cells[3].text) if len(stat_cells) > 3 else 0,
                            'position': position
                        })
                    elif position == 'K' and len(stat_cells) >= 4:
                        # Kicker: FG, FGA, XPT, FPTS
                        row_data.update({
                            'fg_made': self.safe_float(stat_cells[0].text),
                            'fg_att': self.safe_float(stat_cells[1].text),
                            'pat_made': self.safe_float(stat_cells[2].text),
                            'position': 'K'
                        })
                    elif position == 'DST' and len(stat_cells) >= 6:
                        # Defense: SACK, INT, FR, FF, TD, SAFETY, PA, YDS
                        row_data.update({
                            'sacks': self.safe_float(stat_cells[0].text),
                            'interceptions': self.safe_float(stat_cells[1].text),
                            'fumble_recoveries': self.safe_float(stat_cells[2].text),
                            'fumbles_forced': self.safe_float(stat_cells[3].text),
                            'defensive_tds': self.safe_float(stat_cells[4].text),
                            'safeties': self.safe_float(stat_cells[5].text),
                            'points_allowed': self.safe_float(stat_cells[6].text) if len(stat_cells) > 6 else 20,
                            'yards_allowed': self.safe_float(stat_cells[7].text) if len(stat_cells) > 7 else 300,
                            'position': 'DST'
                        })
                    
                    if len(row_data) > 2:  # Has more than just player and team
                        projections.append(row_data)
            
            print(f"Found {len(projections)} {position} projections")
            return projections
            
        except Exception as e:
            print(f"Error scraping {position}: {e}")
            return []
    
    def parse_offensive_projections(self, df: pd.DataFrame, position: str) -> List[Dict]:
        """Convert DataFrame to list of dicts with calculated fantasy points"""
        # Since we're already returning dicts from scrape_projections, just return as list
        return df.to_dict('records')


class ProjectionAnalyzer:
    """Main class to analyze projections and create recommendations"""
    
    def __init__(self):
        self.offensive_scorer = FinalLeagueScorer()
        self.kicker_scorer = KickerScorer()
        self.defense_scorer = DefenseScorer()
        self.scraper = FantasyProsProjectionScraper()
        self.pattern_analyzer = HistoricalPatternAnalyzer()
        self.return_analyzer = DefenseReturnAnalyzer()
        self.accuracy_file = "projection_accuracy.json"
        
    def get_week_projections(self, week: int) -> pd.DataFrame:
        """Get all projections for a week with custom scoring"""
        # Load historical patterns if not already loaded
        self.pattern_analyzer.load_data()
        
        all_projections = []
        
        # Offensive positions
        for position in ['QB', 'RB', 'WR', 'TE']:
            df = self.scraper.get_projections(position, week)
            if not df.empty:
                projections = df.to_dict('records')
                for proj in projections:
                    # Base points
                    base_points = self.offensive_scorer.calculate_projected_score(proj)
                    
                    # Add TD length bonus based on historical patterns
                    total_tds = (proj.get('passing_tds', 0) + 
                               proj.get('rushing_tds', 0) + 
                               proj.get('receiving_tds', 0))
                    
                    if total_tds > 0:
                        td_bonus = self.pattern_analyzer.get_player_td_bonus(
                            proj['player'], total_tds
                        )
                        proj['projected_points'] = round(base_points + td_bonus, 1)
                        proj['td_bonus'] = td_bonus
                    else:
                        proj['projected_points'] = base_points
                        proj['td_bonus'] = 0
                    
                all_projections.extend(projections)
        
        # Kickers with accurate distance-based scoring
        k_df = self.scraper.get_projections('K', week)
        if not k_df.empty:
            k_projections = k_df.to_dict('records')
            for proj in k_projections:
                proj['projected_points'] = self.pattern_analyzer.get_kicker_points(
                    proj['player'],
                    proj.get('fg_made', 0),
                    proj.get('pat_made', 0)
                )
            all_projections.extend(k_projections)
        
        # Defenses with return yards projections
        dst_df = self.scraper.get_projections('DST', week)
        if not dst_df.empty:
            dst_projections = dst_df.to_dict('records')
            
            # Load return yards data
            self.return_analyzer.load_data()
            
            for proj in dst_projections:
                # Base defensive scoring
                base_points = self.defense_scorer.calculate_projected_score(proj)
                
                # Add expected return yards based on opponent
                # For now, use team name as opponent (would need schedule integration)
                # Using league average as fallback
                expected_return_yards = self.return_analyzer.league_avg
                
                # Try to get specific opponent data if available
                # This would need to be enhanced with actual schedule data
                return_points = round(expected_return_yards / 10, 1)
                
                proj['projected_points'] = round(base_points + return_points, 1)
                proj['expected_return_yards'] = expected_return_yards
                proj['return_points'] = return_points
                
            all_projections.extend(dst_projections)
        
        return pd.DataFrame(all_projections)
    
    def get_optimal_lineup(self, projections_df: pd.DataFrame) -> Dict:
        """Determine optimal lineup based on projections"""
        lineup = {
            'QB': [],
            'RB': [],
            'WR': [],
            'TE': [],
            'FLEX': [],
            'K': [],
            'DEF': []
        }
        
        # Sort by projected points
        projections_df = projections_df.sort_values('projected_points', ascending=False)
        
        # Track used players
        used_players = set()
        
        # Fill positions
        for _, player in projections_df.iterrows():
            player_name = player['player']
            if player_name in used_players:
                continue
                
            pos = player['position']
            
            if pos == 'QB' and len(lineup['QB']) < 1:
                lineup['QB'].append(player.to_dict())
                used_players.add(player_name)
            elif pos == 'RB' and len(lineup['RB']) < 2:
                lineup['RB'].append(player.to_dict())
                used_players.add(player_name)
            elif pos == 'WR' and len(lineup['WR']) < 2:
                lineup['WR'].append(player.to_dict())
                used_players.add(player_name)
            elif pos == 'TE' and len(lineup['TE']) < 1:
                lineup['TE'].append(player.to_dict())
                used_players.add(player_name)
        
        # Fill FLEX with best remaining RB/WR/TE
        for _, player in projections_df.iterrows():
            if player['player'] not in used_players and player['position'] in ['RB', 'WR', 'TE']:
                if len(lineup['FLEX']) < 1:
                    lineup['FLEX'].append(player.to_dict())
                    used_players.add(player['player'])
                    break
        
        return lineup
    
    def display_projections(self, week: int):
        """Main function to display all projections and recommendations"""
        print(f"\n{'='*70}")
        print(f"FANTASY FOOTBALL PROJECTIONS - WEEK {week}")
        print(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*70}\n")
        
        # Get projections
        projections_df = self.get_week_projections(week)
        
        if projections_df.empty:
            print("No projections found. Check your connection or try again.")
            return
        
        # Display by position
        for position in ['QB', 'RB', 'WR', 'TE', 'K', 'DST']:
            pos_df = projections_df[projections_df['position'] == position].copy()
            pos_df = pos_df.sort_values('projected_points', ascending=False)
            
            if len(pos_df) > 0:
                print(f"\n=== TOP {position}s ===")
                if position == 'DST':
                    print(f"{'Rank':<5} {'Team':<25} {'Base':<6} {'Ret':<6} {'Total':<10}")
                    print("-" * 55)
                    
                    for i, (_, team) in enumerate(pos_df.head(20).iterrows(), 1):
                        base_pts = team['projected_points'] - team.get('return_points', 0)
                        ret_pts = team.get('return_points', 0)
                        print(f"{i:<5} {team['player']:<25} {base_pts:<6.1f} {ret_pts:<6.1f} {team['projected_points']:<10.1f}")
                else:
                    print(f"{'Rank':<5} {'Player':<25} {'Team':<5} {'Proj Pts':<10}")
                    print("-" * 50)
                    
                    for i, (_, player) in enumerate(pos_df.head(20).iterrows(), 1):
                        team = player.get('team', 'FA')
                        print(f"{i:<5} {player['player']:<25} {team:<5} {player['projected_points']:<10.1f}")
        
        # Get optimal lineup
        lineup = self.get_optimal_lineup(projections_df)
        
        print(f"\n{'='*70}")
        print("YOUR OPTIMAL LINEUP")
        print(f"{'='*70}")
        
        total_proj = 0
        for pos, players in lineup.items():
            for player in players:
                if player is not None and isinstance(player, dict):
                    team = player.get('team', 'FA')
                    print(f"{pos:<5}: {player['player']:<25} {team:<5} ({player['projected_points']:.1f} pts)")
                    total_proj += player['projected_points']
        
        print(f"\nTotal Projected Points: {total_proj:.1f}")
    
    def get_my_roster_projections(self, my_roster: List[str], projections_df: pd.DataFrame):
        """Get projections for YOUR specific roster"""
        print(f"\n{'='*70}")
        print("YOUR ROSTER PROJECTIONS")
        print(f"{'='*70}\n")
        
        my_players = []
        for player_name in my_roster:
            # Find player in projections (case-insensitive partial match)
            matches = projections_df[
                projections_df['player'].str.contains(player_name, case=False, na=False)
            ]
            if len(matches) > 0:
                player = matches.iloc[0].to_dict()
                my_players.append(player)
                print(f"{player['position']:<5} {player['player']:<25} {player.get('team', 'FA'):<5} {player['projected_points']:>6.1f} pts")
            else:
                print(f"???   {player_name:<25} {'???':<5} {'0.0':>6} pts (NOT FOUND)")
        
        # Show optimal lineup from YOUR roster
        print(f"\n{'='*70}")
        print("YOUR OPTIMAL LINEUP")
        print(f"{'='*70}\n")
        
        lineup = self.get_optimal_lineup_from_roster(my_players)
        total = 0
        for pos, player in lineup.items():
            if player:
                print(f"{pos:<5}: {player['player']:<25} {player.get('team', 'FA'):<5} {player['projected_points']:>6.1f} pts")
                total += player['projected_points']
            else:
                print(f"{pos:<5}: {'EMPTY':<25} {'---':<5} {'0.0':>6} pts")
        
        print(f"\nTotal Projected Points: {total:.1f}")
        
        # Show bench
        bench_players = [p for p in my_players if not any(
            p['player'] == lineup_player['player'] 
            for lineup_player in lineup.values() if lineup_player
        )]
        
        if bench_players:
            print(f"\n{'='*70}")
            print("BENCH")
            print(f"{'='*70}\n")
            bench_players.sort(key=lambda x: x['projected_points'], reverse=True)
            for player in bench_players:
                print(f"{player['position']:<5} {player['player']:<25} {player.get('team', 'FA'):<5} {player['projected_points']:>6.1f} pts")
    
    def get_optimal_lineup_from_roster(self, my_players: List[Dict]) -> Dict:
        """Get optimal lineup from specific roster"""
        lineup = {
            'QB': None, 'RB1': None, 'RB2': None, 
            'WR1': None, 'WR2': None, 'TE': None,
            'FLEX': None, 'K': None, 'DST': None
        }
        
        # Sort by points
        my_players.sort(key=lambda x: x['projected_points'], reverse=True)
        used = set()
        
        # Fill starters
        for player in my_players:
            if player['player'] in used:
                continue
                
            pos = player['position']
            if pos == 'QB' and not lineup['QB']:
                lineup['QB'] = player
                used.add(player['player'])
            elif pos == 'RB':
                if not lineup['RB1']:
                    lineup['RB1'] = player
                    used.add(player['player'])
                elif not lineup['RB2']:
                    lineup['RB2'] = player
                    used.add(player['player'])
            elif pos == 'WR':
                if not lineup['WR1']:
                    lineup['WR1'] = player
                    used.add(player['player'])
                elif not lineup['WR2']:
                    lineup['WR2'] = player
                    used.add(player['player'])
            elif pos == 'TE' and not lineup['TE']:
                lineup['TE'] = player
                used.add(player['player'])
            elif pos == 'K' and not lineup['K']:
                lineup['K'] = player
                used.add(player['player'])
            elif pos == 'DST' and not lineup['DST']:
                lineup['DST'] = player
                used.add(player['player'])
        
        # Fill FLEX with best remaining RB/WR/TE
        for player in my_players:
            if player['player'] not in used and player['position'] in ['RB', 'WR', 'TE']:
                lineup['FLEX'] = player
                break
        
        return lineup


def export_for_web(analyzer, week=1):
    """Export all fantasy data as JSON files for web display"""
    
    # Create web_export directory if it doesn't exist
    export_dir = "web_export"
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    
    print(f"\nExporting data for web...")
    
    # Get all projections
    projections = analyzer.get_week_projections(week)
    
    # Get my roster projections
    my_roster = [
        "Joe Burrow", "Bo Nix",
        "Bucky Irving", "Alvin Kamara", "Chuba Hubbard", "Rachaad White", "Christian McCaffrey",
        "Justin Jefferson", "Tee Higgins", "Davante Adams", "George Pickens",
        "Sam LaPorta", "Zach Ertz",
        "Chase McLaughlin",
        "Philadelphia"
    ]
    
    # Get my players from projections
    my_players = []
    for player_name in my_roster:
        matches = projections[projections['player'].str.contains(player_name, case=False, na=False)]
        if len(matches) > 0:
            player_dict = matches.iloc[0].to_dict()
            my_players.append(player_dict)
    
    # Get optimal lineup
    lineup = analyzer.get_optimal_lineup_from_roster(my_players)
    
    # Calculate totals
    starter_total = sum(p['projected_points'] for p in lineup.values() if p)
    
    # Prepare bench players
    lineup_players = [p['player'] for p in lineup.values() if p]
    bench = [p for p in my_players if p['player'] not in lineup_players]
    
    # 1. Export current week projections
    current_week_data = {
        "metadata": {
            "week": week,
            "year": 2025,
            "lastUpdated": datetime.now().isoformat(),
            "totalPlayers": len(projections)
        },
        "myTeam": {
            "roster": my_players,
            "optimalLineup": {pos: player for pos, player in lineup.items() if player},
            "bench": bench,
            "projectedTotal": round(starter_total, 1)
        },
        "allProjections": {
            "QB": projections[projections['position'] == 'QB'].head(30).to_dict('records'),
            "RB": projections[projections['position'] == 'RB'].head(50).to_dict('records'),
            "WR": projections[projections['position'] == 'WR'].head(50).to_dict('records'),
            "TE": projections[projections['position'] == 'TE'].head(30).to_dict('records'),
            "K": projections[projections['position'] == 'K'].head(20).to_dict('records'),
            "DST": projections[projections['position'] == 'DST'].head(20).to_dict('records')
        },
        "topPlayers": {
            "overall": projections.nlargest(20, 'projected_points').to_dict('records'),
            "byPosition": {
                pos: projections[projections['position'] == pos].nlargest(5, 'projected_points').to_dict('records')
                for pos in ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
            }
        }
    }
    
    # Save current week data
    with open(f"{export_dir}/current_week.json", 'w') as f:
        json.dump(current_week_data, f, indent=2)
    
    # 2. Export position summaries for quick loading
    position_summary = {}
    for pos in ['QB', 'RB', 'WR', 'TE', 'K', 'DST']:
        pos_df = projections[projections['position'] == pos].copy()
        position_summary[pos] = {
            "top10": pos_df.head(10).to_dict('records'),
            "count": len(pos_df),
            "avgPoints": round(pos_df['projected_points'].mean(), 1),
            "maxPoints": round(pos_df['projected_points'].max(), 1)
        }
    
    with open(f"{export_dir}/position_summary.json", 'w') as f:
        json.dump(position_summary, f, indent=2)
    
    # 3. Create a simple index file
    index_data = {
        "lastUpdated": datetime.now().isoformat(),
        "currentWeek": week,
        "dataFiles": [
            "current_week.json",
            "position_summary.json"
        ]
    }
    
    with open(f"{export_dir}/index.json", 'w') as f:
        json.dump(index_data, f, indent=2)
    
    print(f"✓ Exported {len(projections)} player projections")
    print(f"✓ Exported optimal lineup (projected: {starter_total:.1f} pts)")
    print(f"✓ Files saved to: {export_dir}/")
    print("\nNext steps:")
    print("1. cd web_export")
    print("2. git add .")
    print("3. git commit -m 'Week X update'")
    print("4. git push")


# Example usage
if __name__ == "__main__":
    analyzer = ProjectionAnalyzer()
    
    # For 2025 Week 1 projections
    current_week = 1
    
    print("Note: 2025 Week 1 projections may not be available until late August.")
    print("Using Week 1 projections...\n")
    
    # Display all projections
    analyzer.display_projections(current_week)
    
    # YOUR ROSTER - Replace with your actual players!
    my_roster = [
        # QBs
        "Joe Burrow",
        "Bo Nix",
        # RBs
        "Bucky Irving",
        "Alvin Kamara",
        "Chuba Hubbard",
        "Rachaad White",
        "Christian McCaffrey",
        # WRs
        "Justin Jefferson",
        "Tee Higgins",
        "Davante Adams",
        "George Pickens",
        # TEs
        "Sam LaPorta",
        "Zach Ertz",
        # K
        "Chase McLaughlin",
        # DST
        "Philadelphia"
    ]
    
    # Get projections for YOUR roster
    projections = analyzer.get_week_projections(current_week)
    analyzer.get_my_roster_projections(my_roster, projections)
    
    # EXPORT FOR WEB
    export_for_web(analyzer, current_week)
