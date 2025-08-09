#!/usr/bin/env python3
"""
Display the backtest results from the database
"""

import sqlite3
import json
from datetime import datetime

def display_results():
    """Display the backtest comparison results"""
    
    try:
        # Connect to results database
        conn = sqlite3.connect('trailing_stop_backtest_results.db')
        cursor = conn.cursor()
        
        print("\n" + "="*80)
        print("TRAILING STOP STRATEGY BACKTEST RESULTS")
        print("="*80)
        
        # Get strategy results
        cursor.execute('''
            SELECT strategy_name, config_json, total_trades, winning_trades, 
                   win_rate, total_pnl, avg_profit_per_trade, profit_factor,
                   avg_hold_time_hours, detailed_results
            FROM backtest_results 
            ORDER BY test_date DESC
        ''')
        
        results = cursor.fetchall()
        
        if not results:
            print("No backtest results found!")
            return
            
        strategy_data = {}
        
        for row in results:
            strategy_name, config_json, total_trades, winning_trades, win_rate, total_pnl, avg_profit, profit_factor, avg_hold_time, detailed_results = row
            
            config = json.loads(config_json)
            detailed = json.loads(detailed_results)
            
            strategy_data[strategy_name] = {
                'config': config,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_profit_per_trade': avg_profit,
                'profit_factor': profit_factor,
                'avg_hold_time_hours': avg_hold_time,
                'detailed': detailed
            }
            
            print(f"\n{config['name']}:")
            print(f"  Configuration: {config['activation_pct']}%/{config['trail_distance_pct']}%/{config['min_profit_pct']}%")
            print(f"  Total Trades: {total_trades}")
            print(f"  Win Rate: {win_rate:.1f}%")
            print(f"  Total P&L: ${total_pnl:.2f}")
            print(f"  Avg Profit/Trade: ${avg_profit:.2f}")
            print(f"  Profit Factor: {profit_factor:.2f}")
            print(f"  Avg Hold Time: {avg_hold_time:.1f} hours")
            
            print(f"  Exit Reasons:")
            exit_reasons = detailed.get('exit_reasons', {})
            for reason, count in exit_reasons.items():
                print(f"    {reason}: {count} trades")
            
        # Get comparison results
        cursor.execute('''
            SELECT profit_difference, win_rate_difference, better_strategy,
                   trades_affected, different_outcomes, impact_percentage,
                   comparison_details
            FROM strategy_comparison
            ORDER BY test_date DESC
            LIMIT 1
        ''')
        
        comparison_row = cursor.fetchone()
        
        if comparison_row:
            profit_diff, win_rate_diff, better_strategy, trades_affected, different_outcomes, impact_pct, comparison_details = comparison_row
            
            print(f"\n" + "-"*60)
            print("STRATEGY COMPARISON")
            print("-"*60)
            
            print(f"Profit Difference: ${profit_diff:.2f}")
            print(f"Win Rate Difference: {win_rate_diff:+.1f}%")
            print(f"Better Strategy: {better_strategy.title()}")
            print(f"Trades Affected: {trades_affected}")
            print(f"Different Outcomes: {different_outcomes}")
            print(f"Impact Percentage: {impact_pct:.1f}%")
            
            if profit_diff > 0:
                print(f"\n[RECOMMENDATION] IMPLEMENT PROPOSED SYSTEM")
                print(f"The proposed system shows ${profit_diff:.2f} better performance.")
            else:
                print(f"\n[RECOMMENDATION] KEEP CURRENT SYSTEM") 
                print(f"The current system shows ${abs(profit_diff):.2f} better performance.")
                
            # Calculate improvement percentage
            if 'current' in strategy_data and strategy_data['current']['total_pnl'] != 0:
                improvement_pct = (profit_diff / abs(strategy_data['current']['total_pnl'])) * 100
                print(f"Performance difference: {improvement_pct:+.1f}%")
                
        print(f"\n" + "="*80)
        print(f"Analysis completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        conn.close()
        
        return strategy_data, comparison_row
        
    except Exception as e:
        print(f"Error displaying results: {e}")
        return None, None

if __name__ == "__main__":
    display_results()