import pandas as pd
import nfl_data_py as nfl
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np

class AccuracyTracker:
    """Track and analyze fantasy projection accuracy"""
    
    def __init__(self, data_dir="fantasy_tracking"):
        self.data_dir = data_dir
        self.projections_dir = os.path.join(data_dir, "projections")
        self.results_dir = os.path.join(data_dir, "results")
        self.analysis_dir = os.path.join(data_dir, "analysis")
        
        # Create directories if they don't exist
        for dir_path in [self.projections_dir, self.results_dir, self.analysis_dir]:
            os.makedirs(dir_path, exist_ok=True)
    
    def save_weekly_projections(self, week: int, year: int, projections_df: pd.DataFrame, 
                               my_lineup: Dict = None):
        """Save projections before games start"""
        filename = f"{year}_week{week}_projections.json"
        filepath = os.path.join(self.projections_dir, filename)
        
        # Convert DataFrame to dict for JSON storage
        projections_data = {
            'week': week,
            'year': year,
            'timestamp': datetime.now().isoformat(),
            'projections': projections_df.to_dict('records'),
            'my_lineup': my_lineup
        }
        
        with open(filepath, 'w') as f:
            json.dump(projections_data, f, indent=2)
        
        print(f"✓ Saved projections for Week {week}, {year}")
        return filepath
    
    def fetch_actual_results(self, week: int, year: int):
        """Fetch actual fantasy points after games complete"""
        print(f"Fetching actual results for Week {week}, {year}...")
        
        # Load the saved projections
        proj_filename = f"{year}_week{week}_projections.json"
        proj_filepath = os.path.join(self.projections_dir, proj_filename)
        
        if not os.path.exists(proj_filepath):
            print(f"No projections found for Week {week}, {year}")
            return None
        
        with open(proj_filepath, 'r') as f:
            proj_data = json.load(f)
        
        # Load actual stats from nfl_data_py
        weekly_data = nfl.import_weekly_data([year])
        week_data = weekly_data[
            (weekly_data['week'] == week) & 
            (weekly_data['season_type'] == 'REG')
        ]
        
        # Calculate actual fantasy points for each player
        results = []
        projections = proj_data['projections']
        
        for proj in projections:
            player_name = proj['player']
            position = proj['position']
            projected_pts = proj['projected_points']
            
            # Find actual stats (handle different name formats)
            actual_pts = self._calculate_actual_points(player_name, position, week_data)
            
            results.append({
                'player': player_name,
                'position': position,
                'team': proj.get('team', ''),
                'projected_points': projected_pts,
                'actual_points': actual_pts,
                'difference': round(actual_pts - projected_pts, 1),
                'accuracy_pct': round((1 - abs(actual_pts - projected_pts) / max(projected_pts, 1)) * 100, 1)
            })
        
        # Save results
        results_filename = f"{year}_week{week}_results.json"
        results_filepath = os.path.join(self.results_dir, results_filename)
        
        results_data = {
            'week': week,
            'year': year,
            'timestamp': datetime.now().isoformat(),
            'results': results
        }
        
        with open(results_filepath, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"✓ Saved actual results for Week {week}, {year}")
        return results
    
    def _calculate_actual_points(self, player_name: str, position: str, week_data: pd.DataFrame) -> float:
        """Calculate actual fantasy points using our scoring system"""
        # This would use your FinalLeagueScorer to calculate actual points
        # For now, returning placeholder
        # In real implementation, this would match player names and calculate points
        return 0.0
    
    def show_weekly_accuracy(self, week: int, year: int):
        """Show accuracy report for a specific week"""
        results_filename = f"{year}_week{week}_results.json"
        results_filepath = os.path.join(self.results_dir, results_filename)
        
        if not os.path.exists(results_filepath):
            print(f"No results found for Week {week}, {year}")
            return
        
        with open(results_filepath, 'r') as f:
            results_data = json.load(f)
        
        results_df = pd.DataFrame(results_data['results'])
        
        print(f"\n{'='*70}")
        print(f"WEEK {week} ACCURACY REPORT - {year}")
        print(f"{'='*70}\n")
        
        # Overall accuracy
        avg_accuracy = results_df['accuracy_pct'].mean()
        print(f"Overall Accuracy: {avg_accuracy:.1f}%")
        
        # By position
        print("\nAccuracy by Position:")
        position_accuracy = results_df.groupby('position').agg({
            'accuracy_pct': 'mean',
            'difference': lambda x: np.mean(np.abs(x))
        }).round(1)
        
        for pos, row in position_accuracy.iterrows():
            print(f"  {pos:<4}: {row['accuracy_pct']:>5.1f}% accurate (avg error: {row['difference']:>4.1f} pts)")
        
        # Best projections
        print("\nMost Accurate Projections:")
        best = results_df.nlargest(5, 'accuracy_pct')[['player', 'position', 'projected_points', 
                                                        'actual_points', 'accuracy_pct']]
        for _, player in best.iterrows():
            print(f"  {player['player']:<20} ({player['position']}): "
                  f"{player['projected_points']:.1f} proj, {player['actual_points']:.1f} actual "
                  f"({player['accuracy_pct']:.1f}% accurate)")
        
        # Worst projections
        print("\nLeast Accurate Projections:")
        worst = results_df.nsmallest(5, 'accuracy_pct')[['player', 'position', 'projected_points', 
                                                          'actual_points', 'difference']]
        for _, player in worst.iterrows():
            print(f"  {player['player']:<20} ({player['position']}): "
                  f"{player['projected_points']:.1f} proj, {player['actual_points']:.1f} actual "
                  f"({player['difference']:+.1f} pts off)")
    
    def show_player_history(self, player_name: str):
        """Show projection accuracy history for a specific player"""
        all_results = []
        
        # Load all results files
        for filename in os.listdir(self.results_dir):
            if filename.endswith('_results.json'):
                with open(os.path.join(self.results_dir, filename), 'r') as f:
                    data = json.load(f)
                    for result in data['results']:
                        if player_name.lower() in result['player'].lower():
                            result['week'] = data['week']
                            result['year'] = data['year']
                            all_results.append(result)
        
        if not all_results:
            print(f"No history found for {player_name}")
            return
        
        results_df = pd.DataFrame(all_results)
        
        print(f"\n{'='*70}")
        print(f"PROJECTION HISTORY: {player_name}")
        print(f"{'='*70}\n")
        
        # Summary stats
        avg_projected = results_df['projected_points'].mean()
        avg_actual = results_df['actual_points'].mean()
        avg_accuracy = results_df['accuracy_pct'].mean()
        avg_error = results_df['difference'].abs().mean()
        
        print(f"Average Projected: {avg_projected:.1f} pts")
        print(f"Average Actual: {avg_actual:.1f} pts")
        print(f"Average Accuracy: {avg_accuracy:.1f}%")
        print(f"Average Error: {avg_error:.1f} pts")
        
        if avg_actual > avg_projected:
            print(f"\n→ Tends to EXCEED projections by {avg_actual - avg_projected:.1f} pts")
        else:
            print(f"\n→ Tends to FALL SHORT of projections by {avg_projected - avg_actual:.1f} pts")
        
        # Week by week
        print("\nWeek-by-Week Performance:")
        print(f"{'Week':<6} {'Proj':<6} {'Actual':<8} {'Diff':<7} {'Accuracy':<10}")
        print("-" * 40)
        
        for _, row in results_df.iterrows():
            print(f"W{row['week']:<4} {row['projected_points']:>6.1f} {row['actual_points']:>7.1f} "
                  f"{row['difference']:>+6.1f} {row['accuracy_pct']:>8.1f}%")
    
    def calculate_confidence_intervals(self):
        """Calculate confidence intervals based on historical accuracy"""
        all_results = []
        
        # Load all results
        for filename in os.listdir(self.results_dir):
            if filename.endswith('_results.json'):
                with open(os.path.join(self.results_dir, filename), 'r') as f:
                    data = json.load(f)
                    all_results.extend(data['results'])
        
        if not all_results:
            return {}
        
        results_df = pd.DataFrame(all_results)
        
        # Calculate confidence intervals by position
        confidence_intervals = {}
        
        for position in results_df['position'].unique():
            pos_data = results_df[results_df['position'] == position]
            
            # Calculate standard deviation of errors
            errors = pos_data['difference'].values
            std_error = np.std(errors)
            
            # 68% confidence interval (1 std dev)
            # 95% confidence interval (2 std dev)
            confidence_intervals[position] = {
                '68_pct': round(std_error, 1),
                '95_pct': round(2 * std_error, 1),
                'avg_error': round(np.mean(np.abs(errors)), 1)
            }
        
        return confidence_intervals
    
    def generate_season_report(self, year: int):
        """Generate comprehensive season accuracy report"""
        all_results = []
        weeks_tracked = []
        
        # Load all results for the year
        for filename in os.listdir(self.results_dir):
            if filename.startswith(f"{year}_") and filename.endswith('_results.json'):
                with open(os.path.join(self.results_dir, filename), 'r') as f:
                    data = json.load(f)
                    all_results.extend(data['results'])
                    weeks_tracked.append(data['week'])
        
        if not all_results:
            print(f"No results found for {year} season")
            return
        
        results_df = pd.DataFrame(all_results)
        
        print(f"\n{'='*70}")
        print(f"{year} SEASON ACCURACY REPORT")
        print(f"{'='*70}\n")
        
        print(f"Weeks Tracked: {sorted(weeks_tracked)}")
        print(f"Total Projections: {len(results_df)}")
        print(f"Overall Accuracy: {results_df['accuracy_pct'].mean():.1f}%")
        
        # Position rankings by accuracy
        print("\nPosition Accuracy Rankings:")
        pos_stats = results_df.groupby('position').agg({
            'accuracy_pct': 'mean',
            'difference': [lambda x: np.mean(np.abs(x)), 'std']
        }).round(1)
        
        pos_stats.columns = ['avg_accuracy', 'avg_error', 'std_error']
        pos_stats = pos_stats.sort_values('avg_accuracy', ascending=False)
        
        for i, (pos, row) in enumerate(pos_stats.iterrows(), 1):
            print(f"  {i}. {pos:<4}: {row['avg_accuracy']:>5.1f}% (±{row['std_error']:.1f} pts)")
        
        # Most reliable players
        print("\nMost Reliable Players (min 5 projections):")
        player_stats = results_df.groupby('player').agg({
            'accuracy_pct': ['mean', 'count'],
            'difference': lambda x: np.mean(np.abs(x))
        }).round(1)
        
        player_stats.columns = ['avg_accuracy', 'count', 'avg_error']
        reliable = player_stats[player_stats['count'] >= 5].sort_values('avg_accuracy', ascending=False).head(10)
        
        for i, (player, row) in enumerate(reliable.iterrows(), 1):
            print(f"  {i}. {player:<20}: {row['avg_accuracy']:>5.1f}% accurate "
                  f"({int(row['count'])} weeks, ±{row['avg_error']:.1f} pts)")


# Integration with main projection system
class EnhancedProjectionAnalyzer:
    """Enhanced analyzer with accuracy tracking"""
    
    def __init__(self, base_analyzer):
        self.base_analyzer = base_analyzer
        self.accuracy_tracker = AccuracyTracker()
        
    def display_projections_with_confidence(self, week: int, year: int = 2025):
        """Display projections with confidence intervals"""
        # Get base projections
        projections_df = self.base_analyzer.get_week_projections(week)
        
        # Get confidence intervals
        confidence = self.accuracy_tracker.calculate_confidence_intervals()
        
        # Add confidence to projections
        for idx, row in projections_df.iterrows():
            position = row['position']
            if position in confidence:
                conf_68 = confidence[position]['68_pct']
                conf_95 = confidence[position]['95_pct']
                
                # Add confidence columns
                projections_df.loc[idx, 'conf_68_low'] = row['projected_points'] - conf_68
                projections_df.loc[idx, 'conf_68_high'] = row['projected_points'] + conf_68
                projections_df.loc[idx, 'conf_95_low'] = row['projected_points'] - conf_95
                projections_df.loc[idx, 'conf_95_high'] = row['projected_points'] + conf_95
        
        # Save projections
        self.accuracy_tracker.save_weekly_projections(week, year, projections_df)
        
        # Display with confidence
        print(f"\n{'='*70}")
        print(f"WEEK {week} PROJECTIONS WITH CONFIDENCE INTERVALS")
        print(f"{'='*70}\n")
        
        for position in ['QB', 'RB', 'WR', 'TE']:
            pos_df = projections_df[projections_df['position'] == position].head(10)
            
            print(f"\n=== TOP {position}s ===")
            print(f"{'Player':<20} {'Proj':<6} {'68% Range':<15} {'95% Range':<15}")
            print("-" * 60)
            
            for _, player in pos_df.iterrows():
                if 'conf_68_low' in player:
                    range_68 = f"{player['conf_68_low']:.1f}-{player['conf_68_high']:.1f}"
                    range_95 = f"{player['conf_95_low']:.1f}-{player['conf_95_high']:.1f}"
                else:
                    range_68 = "N/A"
                    range_95 = "N/A"
                
                print(f"{player['player']:<20} {player['projected_points']:<6.1f} "
                      f"{range_68:<15} {range_95:<15}")


# Example usage
if __name__ == "__main__":
    tracker = AccuracyTracker()
    
    # Simulate saving projections (would be done before games)
    sample_projections = pd.DataFrame([
        {'player': 'Saquon Barkley', 'position': 'RB', 'team': 'PHI', 'projected_points': 28.1},
        {'player': 'Justin Jefferson', 'position': 'WR', 'team': 'MIN', 'projected_points': 18.2},
        {'player': 'Joe Burrow', 'position': 'QB', 'team': 'CIN', 'projected_points': 44.2}
    ])
    
    # Save projections
    tracker.save_weekly_projections(week=1, year=2025, projections_df=sample_projections)
    
    # After games complete, fetch actual results
    # tracker.fetch_actual_results(week=1, year=2025)
    
    # View reports
    # tracker.show_weekly_accuracy(week=1, year=2025)
    # tracker.show_player_history("Saquon Barkley")
    # tracker.generate_season_report(2025)
    
    print("\nAccuracy tracking system initialized!")
    print("Functions available:")
    print("- save_weekly_projections(): Save before games")
    print("- fetch_actual_results(): Update after games")
    print("- show_weekly_accuracy(): Week report")
    print("- show_player_history(): Player trends")
    print("- generate_season_report(): Season summary")
