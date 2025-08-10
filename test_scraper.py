import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os

class FantasyProsScraperFixed:
    """Fixed scraper that handles FantasyPros' duplicate column names"""
    
    def __init__(self):
        self.base_url = "https://www.fantasypros.com/nfl/projections"
        self.cache_dir = "projection_cache"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def scrape_projections(self, position: str, week: int) -> list:
        """Scrape projections and return as list of dicts"""
        url = f"{self.base_url}/{position.lower()}.php?week={week}"
        print(f"\nScraping {position} from: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the main table
            tables = soup.find_all('table')
            main_table = None
            
            for table in tables:
                if table.find('a', class_='player-name'):
                    main_table = table
                    break
            
            if not main_table:
                print(f"No player table found for {position}")
                return []
            
            # Get the actual headers from the table
            thead = main_table.find('thead')
            if not thead:
                print("No thead found")
                return []
            
            # FantasyPros has nested headers, get the last row
            header_rows = thead.find_all('tr')
            if not header_rows:
                print("No header rows found")
                return []
            
            # Build column names based on position
            if position == 'QB':
                columns = ['player', 'team', 'pass_att', 'pass_cmp', 'pass_yds', 'pass_tds', 
                          'pass_int', 'rush_att', 'rush_yds', 'rush_tds', 'fl', 'fpts']
            elif position == 'RB':
                columns = ['player', 'team', 'rush_att', 'rush_yds', 'rush_tds', 
                          'rec', 'rec_yds', 'rec_tds', 'fl', 'fpts']
            elif position in ['WR', 'TE']:
                columns = ['player', 'team', 'rec', 'rec_yds', 'rec_tds', 
                          'rush_att', 'rush_yds', 'rush_tds', 'fl', 'fpts']
            else:
                columns = []
            
            # Parse the data rows
            tbody = main_table.find('tbody')
            if not tbody:
                print("No tbody found")
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
                    
                    # Get team - it's usually in a small tag or after the name
                    team_elem = first_cell.find('small')
                    if team_elem:
                        team_text = team_elem.text.strip()
                        # Extract team abbreviation (e.g., "BAL" from "BAL - QB")
                        if ' - ' in team_text:
                            row_data['team'] = team_text.split(' - ')[0]
                        else:
                            row_data['team'] = team_text
                    else:
                        row_data['team'] = ''
                    
                    # Get the rest of the stats
                    stat_cells = cells[1:]  # Skip the player cell
                    
                    # Map stats based on position
                    if position == 'QB' and len(stat_cells) >= 10:
                        row_data.update({
                            'pass_att': self.safe_float(stat_cells[0].text),
                            'pass_cmp': self.safe_float(stat_cells[1].text),
                            'pass_yds': self.safe_float(stat_cells[2].text),
                            'pass_tds': self.safe_float(stat_cells[3].text),
                            'pass_int': self.safe_float(stat_cells[4].text),
                            'rush_att': self.safe_float(stat_cells[5].text),
                            'rush_yds': self.safe_float(stat_cells[6].text),
                            'rush_tds': self.safe_float(stat_cells[7].text),
                            'fl': self.safe_float(stat_cells[8].text),
                            'position': 'QB'
                        })
                    elif position == 'RB' and len(stat_cells) >= 8:
                        row_data.update({
                            'rush_att': self.safe_float(stat_cells[0].text),
                            'rush_yds': self.safe_float(stat_cells[1].text),
                            'rush_tds': self.safe_float(stat_cells[2].text),
                            'rec': self.safe_float(stat_cells[3].text),
                            'rec_yds': self.safe_float(stat_cells[4].text),
                            'rec_tds': self.safe_float(stat_cells[5].text),
                            'fl': self.safe_float(stat_cells[6].text),
                            'position': 'RB'
                        })
                    elif position in ['WR', 'TE'] and len(stat_cells) >= 8:
                        row_data.update({
                            'rec': self.safe_float(stat_cells[0].text),
                            'rec_yds': self.safe_float(stat_cells[1].text),
                            'rec_tds': self.safe_float(stat_cells[2].text),
                            'rush_att': self.safe_float(stat_cells[3].text),
                            'rush_yds': self.safe_float(stat_cells[4].text),
                            'rush_tds': self.safe_float(stat_cells[5].text),
                            'fl': self.safe_float(stat_cells[6].text),
                            'position': position
                        })
                    
                    if len(row_data) > 2:  # Has more than just player and team
                        projections.append(row_data)
            
            print(f"Found {len(projections)} {position} projections")
            return projections
            
        except Exception as e:
            print(f"Error scraping {position}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def safe_float(self, value):
        """Safely convert string to float"""
        try:
            return float(value.strip())
        except:
            return 0.0


# Test the scraper
if __name__ == "__main__":
    scraper = FantasyProsScraperFixed()
    
    # Test each position
    for position in ['QB', 'RB', 'WR', 'TE']:
        projections = scraper.scrape_projections(position, week=1)
        
        if projections:
            print(f"\nFirst 3 {position} projections:")
            for i, proj in enumerate(projections[:3]):
                print(f"{i+1}. {proj.get('player', 'Unknown')} ({proj.get('team', '')})")
                if position == 'QB':
                    print(f"   Passing: {proj.get('pass_yds', 0)} yds, {proj.get('pass_tds', 0)} TDs")
                    print(f"   Rushing: {proj.get('rush_yds', 0)} yds, {proj.get('rush_tds', 0)} TDs")
                elif position == 'RB':
                    print(f"   Rushing: {proj.get('rush_yds', 0)} yds, {proj.get('rush_tds', 0)} TDs")
                    print(f"   Receiving: {proj.get('rec', 0)} rec, {proj.get('rec_yds', 0)} yds")
                else:
                    print(f"   Receiving: {proj.get('rec', 0)} rec, {proj.get('rec_yds', 0)} yds, {proj.get('rec_tds', 0)} TDs")
