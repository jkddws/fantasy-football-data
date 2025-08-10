"""
Enhanced Fantasy Football Projection System
Now with accuracy tracking and confidence intervals!

Usage:
1. Before games: python fantasy_projections_enhanced.py --save
2. After games:  python fantasy_projections_enhanced.py --update-actuals
3. View reports: python fantasy_projections_enhanced.py --report
"""

import sys
import argparse
from datetime import datetime

# Import your existing projection system
from fantasy_projections import ProjectionAnalyzer
from accuracy_tracking import AccuracyTracker

class EnhancedFantasySystem:
    """Complete fantasy system with projections and accuracy tracking"""
    
    def __init__(self):
        self.projector = ProjectionAnalyzer()
        self.tracker = AccuracyTracker()
        self.current_week = 1  # Update this each week
        self.current_year = 2025
        
        # Your roster
        self.my_roster = [
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
    
    def run_weekly_projections(self, save=True):
        """Run projections for current week with confidence intervals"""
        print(f"\n{'='*70}")
        print(f"ENHANCED FANTASY PROJECTIONS - WEEK {self.current_week}")
        print(f"{'='*70}\n")
        
        # Get projections
        projections = self.projector.get_week_projections(self.current_week)
        
        # Add confidence intervals if we have historical data
        confidence = self.tracker.calculate_confidence_intervals()
        
        if confidence:
            print("Applying confidence intervals based on historical accuracy...\n")
            
            for idx, row in projections.iterrows():
                position = row['position']
                if position in confidence:
                    std_68 = confidence[position]['68_pct']
                    std_95 = confidence[position]['95_pct']
                    base_pts = row['projected_points']
                    
                    projections.loc[idx, 'range_68'] = f"{base_pts-std_68:.1f}-{base_pts+std_68:.1f}"
                    projections.loc[idx, 'range_95'] = f"{base_pts-std_95:.1f}-{base_pts+std_95:.1f}"
        
        # Display projections
        self.projector.display_projections(self.current_week)
        
        # Show your roster with confidence
        print(f"\n{'='*70}")
        print("YOUR ROSTER WITH CONFIDENCE INTERVALS")
        print(f"{'='*70}\n")
        
        my_players = []
        for player_name in self.my_roster:
            matches = projections[
                projections['player'].str.contains(player_name, case=False, na=False)
            ]
            if len(matches) > 0:
                player = matches.iloc[0]
                my_players.append(player.to_dict())
                
                conf_range = player.get('range_68', 'N/A')
                print(f"{player['position']:<5} {player['player']:<20} "
                      f"{player['projected_points']:>6.1f} pts  "
                      f"(likely: {conf_range})")
        
        # Get optimal lineup
        lineup = self.projector.get_optimal_lineup_from_roster(my_players)
        
        # Save if requested
        if save:
            # Extract just the starting lineup players
            my_lineup = {pos: player['player'] if player else None 
                        for pos, player in lineup.items()}
            
            self.tracker.save_weekly_projections(
                week=self.current_week,
                year=self.current_year,
                projections_df=projections,
                my_lineup=my_lineup
            )
            print(f"\n✓ Projections saved for Week {self.current_week}")
    
    def update_actual_results(self):
        """Fetch and save actual results after games complete"""
        print(f"\nUpdating actual results for Week {self.current_week}...")
        
        # This would need to be enhanced to actually calculate fantasy points
        # For now, it's a placeholder
        results = self.tracker.fetch_actual_results(
            week=self.current_week,
            year=self.current_year
        )
        
        if results:
            print(f"✓ Updated {len(results)} player results")
            
            # Show quick summary
            results_df = pd.DataFrame(results)
            avg_accuracy = results_df['accuracy_pct'].mean()
            print(f"\nWeek {self.current_week} Overall Accuracy: {avg_accuracy:.1f}%")
    
    def show_reports(self, report_type='weekly'):
        """Show various accuracy reports"""
        if report_type == 'weekly':
            self.tracker.show_weekly_accuracy(self.current_week, self.current_year)
        elif report_type == 'season':
            self.tracker.generate_season_report(self.current_year)
        elif report_type == 'player':
            player = input("Enter player name: ")
            self.tracker.show_player_history(player)
    
    def show_my_lineup_performance(self):
        """Show how your actual lineup performed vs optimal"""
        # Load saved projections with your lineup
        proj_file = f"{self.current_year}_week{self.current_week}_projections.json"
        results_file = f"{self.current_year}_week{self.current_week}_results.json"
        
        # This would compare your chosen lineup vs the optimal lineup
        print(f"\nYour Lineup Performance - Week {self.current_week}")
        print("Coming soon: See how your decisions compared to optimal!")


def main():
    parser = argparse.ArgumentParser(description='Enhanced Fantasy Football System')
    parser.add_argument('--week', type=int, help='Week number (default: current)')
    parser.add_argument('--save', action='store_true', help='Save projections')
    parser.add_argument('--update-actuals', action='store_true', help='Update with actual results')
    parser.add_argument('--report', choices=['weekly', 'season', 'player'], help='Show reports')
    parser.add_argument('--my-performance', action='store_true', help='Show your lineup performance')
    
    args = parser.parse_args()
    
    system = EnhancedFantasySystem()
    
    # Update week if specified
    if args.week:
        system.current_week = args.week
    
    # Run appropriate function
    if args.update_actuals:
        system.update_actual_results()
    elif args.report:
        system.show_reports(args.report)
    elif args.my_performance:
        system.show_my_lineup_performance()
    else:
        # Default: show projections
        system.run_weekly_projections(save=args.save)


if __name__ == "__main__":
    # If no arguments, just run projections
    if len(sys.argv) == 1:
        system = EnhancedFantasySystem()
        system.run_weekly_projections(save=True)
    else:
        main()
