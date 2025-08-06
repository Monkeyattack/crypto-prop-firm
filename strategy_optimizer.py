#!/usr/bin/env python3
"""
Strategy Optimizer - Advanced optimization of trading strategies based on backtesting results
"""

import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import optimize
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StrategyOptimizer:
    def __init__(self):
        self.db_path = 'trading.db'
        self.results_cache = {}
        
        # Initialize optimizer database
        self.init_optimizer_database()
    
    def init_optimizer_database(self):
        """Initialize database for optimization results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_optimizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                optimization_name TEXT,
                strategy_params TEXT,
                win_rate REAL,
                total_pnl REAL,
                profit_factor REAL,
                max_drawdown REAL,
                sharpe_ratio REAL,
                total_trades INTEGER,
                avg_trade_duration REAL,
                best_symbols TEXT,
                recommendations TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimized_strategy_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_name TEXT UNIQUE,
                base_config TEXT,
                optimized_config TEXT,
                performance_improvement REAL,
                active BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_backtest_results(self) -> pd.DataFrame:
        """Load backtest results from database"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT * FROM backtest_results 
            ORDER BY entry_time
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['entry_time'] = pd.to_datetime(df['entry_time'])
            df['exit_time'] = pd.to_datetime(df['exit_time'])
        
        logger.info(f"Loaded {len(df)} backtest results for optimization")
        return df
    
    def analyze_signal_timing(self, results_df: pd.DataFrame) -> dict:
        """Analyze optimal timing for signal entry"""
        timing_analysis = {}
        
        # Group by hour of day
        results_df['entry_hour'] = results_df['entry_time'].dt.hour
        hourly_performance = results_df.groupby('entry_hour').agg({
            'profit_loss_pct': ['mean', 'sum', 'count'],
            'profit_loss': ['mean']
        }).round(3)
        
        # Find best and worst hours
        best_hours = hourly_performance['profit_loss_pct']['mean'].nlargest(5)
        worst_hours = hourly_performance['profit_loss_pct']['mean'].nsmallest(5)
        
        timing_analysis['hourly_performance'] = hourly_performance
        timing_analysis['best_hours'] = best_hours.to_dict()
        timing_analysis['worst_hours'] = worst_hours.to_dict()
        
        # Day of week analysis
        results_df['entry_day'] = results_df['entry_time'].dt.day_name()
        daily_performance = results_df.groupby('entry_day').agg({
            'profit_loss_pct': ['mean', 'sum', 'count']
        }).round(3)
        
        timing_analysis['daily_performance'] = daily_performance
        
        return timing_analysis
    
    def optimize_stop_loss_take_profit(self, results_df: pd.DataFrame) -> dict:
        """Optimize stop loss and take profit levels using grid search"""
        logger.info("Optimizing stop loss and take profit levels...")
        
        # Define parameter ranges
        sl_range = np.arange(0.01, 0.15, 0.005)  # 1% to 15% in 0.5% steps
        tp_range = np.arange(0.02, 0.30, 0.01)   # 2% to 30% in 1% steps
        
        optimization_results = []
        
        for sl in sl_range:
            for tp in tp_range:
                # Skip if risk/reward ratio is too poor
                if tp / sl < 1.5:
                    continue
                
                performance = self.simulate_sl_tp_strategy(results_df, sl, tp)
                
                if performance:
                    performance['sl_level'] = sl
                    performance['tp_level'] = tp
                    performance['risk_reward_ratio'] = tp / sl
                    optimization_results.append(performance)
        
        # Convert to DataFrame and find optimal parameters
        opt_df = pd.DataFrame(optimization_results)
        
        if opt_df.empty:
            return {}
        
        # Define optimization criteria (weighted score)
        opt_df['score'] = (
            opt_df['win_rate'] * 0.3 +
            opt_df['profit_factor'] * 0.3 +
            opt_df['total_pnl_pct'] * 0.2 +
            (100 - opt_df['max_drawdown_pct']) * 0.1 +
            opt_df['sharpe_ratio'] * 0.1
        )
        
        # Find best parameters
        best_params = opt_df.loc[opt_df['score'].idxmax()]
        
        return {
            'optimal_sl': best_params['sl_level'],
            'optimal_tp': best_params['tp_level'],
            'optimal_score': best_params['score'],
            'expected_win_rate': best_params['win_rate'],
            'expected_profit_factor': best_params['profit_factor'],
            'risk_reward_ratio': best_params['risk_reward_ratio'],
            'all_results': opt_df.to_dict('records')
        }
    
    def simulate_sl_tp_strategy(self, results_df: pd.DataFrame, sl_pct: float, tp_pct: float) -> dict:
        """Simulate strategy with specific SL/TP levels"""
        try:
            modified_results = []
            
            for _, row in results_df.iterrows():
                entry_price = row['entry_price']
                side = row['side']
                max_favorable = row['max_favorable_excursion']
                max_adverse = row['max_adverse_excursion']
                
                # Calculate new SL/TP levels
                if side in ['BUY', 'LONG']:
                    new_tp_price = entry_price * (1 + tp_pct)
                    new_sl_price = entry_price * (1 - sl_pct)
                    
                    tp_target = new_tp_price - entry_price
                    sl_target = entry_price - new_sl_price
                    
                    # Determine exit
                    if max_favorable >= tp_target:
                        pnl_pct = tp_pct * 100
                        exit_reason = 'take_profit'
                    elif max_adverse >= sl_target:
                        pnl_pct = -sl_pct * 100
                        exit_reason = 'stop_loss'
                    else:
                        # Use original exit
                        pnl_pct = row['profit_loss_pct']
                        exit_reason = row['exit_reason']
                
                else:  # SELL, SHORT
                    new_tp_price = entry_price * (1 - tp_pct)
                    new_sl_price = entry_price * (1 + sl_pct)
                    
                    tp_target = entry_price - new_tp_price
                    sl_target = new_sl_price - entry_price
                    
                    # Determine exit
                    if max_favorable >= tp_target:
                        pnl_pct = tp_pct * 100
                        exit_reason = 'take_profit'
                    elif max_adverse >= sl_target:
                        pnl_pct = -sl_pct * 100
                        exit_reason = 'stop_loss'
                    else:
                        # Use original exit
                        pnl_pct = row['profit_loss_pct']
                        exit_reason = row['exit_reason']
                
                modified_results.append({
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                    'trade_duration': row['trade_duration_hours']
                })
            
            # Calculate performance metrics
            mod_df = pd.DataFrame(modified_results)
            
            total_trades = len(mod_df)
            winning_trades = len(mod_df[mod_df['pnl_pct'] > 0])
            losing_trades = len(mod_df[mod_df['pnl_pct'] < 0])
            
            if total_trades == 0:
                return None
            
            win_rate = (winning_trades / total_trades) * 100
            total_pnl_pct = mod_df['pnl_pct'].sum()
            
            if winning_trades > 0 and losing_trades > 0:
                avg_win = mod_df[mod_df['pnl_pct'] > 0]['pnl_pct'].mean()
                avg_loss = abs(mod_df[mod_df['pnl_pct'] < 0]['pnl_pct'].mean())
                profit_factor = (avg_win * winning_trades) / (avg_loss * losing_trades)
            else:
                profit_factor = float('inf') if losing_trades == 0 else 0
            
            # Calculate max drawdown
            cumulative_pnl = mod_df['pnl_pct'].cumsum()
            running_max = cumulative_pnl.expanding().max()
            drawdown = cumulative_pnl - running_max
            max_drawdown_pct = abs(drawdown.min())
            
            # Calculate Sharpe ratio (simplified)
            if mod_df['pnl_pct'].std() > 0:
                sharpe_ratio = mod_df['pnl_pct'].mean() / mod_df['pnl_pct'].std() * np.sqrt(252)  # Annualized
            else:
                sharpe_ratio = 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl_pct': total_pnl_pct,
                'profit_factor': profit_factor,
                'max_drawdown_pct': max_drawdown_pct,
                'sharpe_ratio': sharpe_ratio,
                'avg_trade_duration': mod_df['trade_duration'].mean()
            }
            
        except Exception as e:
            logger.error(f"Error in SL/TP simulation: {e}")
            return None
    
    def analyze_symbol_performance(self, results_df: pd.DataFrame) -> dict:
        """Analyze performance by symbol to identify best performing assets"""
        symbol_analysis = {}
        
        symbol_stats = results_df.groupby('symbol').agg({
            'profit_loss_pct': ['count', 'mean', 'sum', 'std'],
            'profit_loss': ['sum'],
            'trade_duration_hours': ['mean']
        }).round(3)
        
        # Calculate win rates by symbol
        win_rates = results_df.groupby('symbol').apply(
            lambda x: (x['profit_loss_pct'] > 0).sum() / len(x) * 100
        ).round(2)
        
        # Combine statistics
        for symbol in symbol_stats.index:
            symbol_analysis[symbol] = {
                'total_trades': symbol_stats.loc[symbol, ('profit_loss_pct', 'count')],
                'win_rate': win_rates[symbol],
                'avg_pnl_pct': symbol_stats.loc[symbol, ('profit_loss_pct', 'mean')],
                'total_pnl_pct': symbol_stats.loc[symbol, ('profit_loss_pct', 'sum')],
                'volatility': symbol_stats.loc[symbol, ('profit_loss_pct', 'std')],
                'avg_duration': symbol_stats.loc[symbol, ('trade_duration_hours', 'mean')]
            }
        
        # Rank symbols by performance score
        performance_scores = {}
        for symbol, stats in symbol_analysis.items():
            if stats['total_trades'] >= 3:  # Minimum trades for reliability
                score = (
                    stats['win_rate'] * 0.4 +
                    stats['avg_pnl_pct'] * 10 * 0.3 +
                    stats['total_pnl_pct'] * 0.2 +
                    (50 / max(stats['volatility'], 1)) * 0.1  # Lower volatility is better
                )
                performance_scores[symbol] = score
        
        # Sort by performance
        top_symbols = sorted(performance_scores.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'symbol_analysis': symbol_analysis,
            'top_symbols': top_symbols[:10],
            'total_symbols': len(symbol_analysis)
        }
    
    def optimize_entry_timing(self, results_df: pd.DataFrame) -> dict:
        """Optimize entry timing based on signal delay analysis"""
        timing_optimization = {}
        
        # Analyze different entry delays (0 to 6 hours after signal)
        delay_results = []
        
        for delay_hours in range(0, 7):
            # This would require re-simulation with delayed entry
            # For now, we'll estimate based on existing data patterns
            
            # Analyze trades that naturally had this delay
            delay_threshold = timedelta(hours=delay_hours)
            
            # Simplified analysis - in real implementation, you'd re-simulate
            estimated_performance = self.estimate_delay_performance(results_df, delay_hours)
            
            if estimated_performance:
                delay_results.append({
                    'delay_hours': delay_hours,
                    **estimated_performance
                })
        
        timing_optimization['delay_analysis'] = delay_results
        
        # Find optimal entry delay
        if delay_results:
            best_delay = max(delay_results, key=lambda x: x.get('score', 0))
            timing_optimization['optimal_delay'] = best_delay
        
        return timing_optimization
    
    def estimate_delay_performance(self, results_df: pd.DataFrame, delay_hours: int) -> dict:
        """Estimate performance with entry delay (simplified)"""
        # This is a simplified estimation
        # In practice, you'd need to re-fetch price data and re-simulate
        
        try:
            # Adjust performance based on delay patterns observed in data
            base_performance = {
                'win_rate': (results_df['profit_loss_pct'] > 0).mean() * 100,
                'avg_pnl': results_df['profit_loss_pct'].mean(),
                'total_pnl': results_df['profit_loss_pct'].sum()
            }
            
            # Apply delay adjustment (this is a simplified model)
            delay_factor = max(0.95 - (delay_hours * 0.02), 0.8)  # Performance degrades with delay
            
            adjusted_performance = {
                'win_rate': base_performance['win_rate'] * delay_factor,
                'avg_pnl': base_performance['avg_pnl'] * delay_factor,
                'total_pnl': base_performance['total_pnl'] * delay_factor,
                'score': base_performance['win_rate'] * delay_factor + base_performance['avg_pnl'] * 10
            }
            
            return adjusted_performance
            
        except Exception as e:
            logger.error(f"Error estimating delay performance: {e}")
            return None
    
    def generate_optimized_strategy(self, results_df: pd.DataFrame) -> dict:
        """Generate complete optimized strategy configuration"""
        logger.info("Generating optimized strategy configuration...")
        
        # Run all optimizations
        sl_tp_optimization = self.optimize_stop_loss_take_profit(results_df)
        symbol_analysis = self.analyze_symbol_performance(results_df)
        timing_analysis = self.analyze_signal_timing(results_df)
        entry_timing = self.optimize_entry_timing(results_df)
        
        # Generate strategy configuration
        optimized_strategy = {
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'risk_management': {
                'stop_loss_pct': sl_tp_optimization.get('optimal_sl', 0.05) * 100,
                'take_profit_pct': sl_tp_optimization.get('optimal_tp', 0.10) * 100,
                'risk_reward_ratio': sl_tp_optimization.get('risk_reward_ratio', 2.0),
                'max_position_size': 100,  # Paper trading
                'max_daily_trades': 10
            },
            'entry_criteria': {
                'optimal_entry_delay_hours': entry_timing.get('optimal_delay', {}).get('delay_hours', 0),
                'preferred_entry_hours': list(timing_analysis.get('best_hours', {}).keys())[:3],
                'avoid_entry_hours': list(timing_analysis.get('worst_hours', {}).keys())[:3]
            },
            'symbol_selection': {
                'top_symbols': [symbol for symbol, score in symbol_analysis.get('top_symbols', [])[:10]],
                'min_trades_for_inclusion': 3,
                'min_win_rate': 40
            },
            'performance_targets': {
                'expected_win_rate': sl_tp_optimization.get('expected_win_rate', 50),
                'expected_profit_factor': sl_tp_optimization.get('expected_profit_factor', 1.5),
                'max_drawdown_tolerance': 20
            }
        }
        
        # Store optimized configuration
        self.store_optimized_strategy(optimized_strategy)
        
        return optimized_strategy
    
    def store_optimized_strategy(self, strategy_config: dict):
        """Store optimized strategy configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Store in database
        cursor.execute('''
            INSERT OR REPLACE INTO optimized_strategy_config 
            (config_name, optimized_config, active)
            VALUES (?, ?, ?)
        ''', (
            f"optimized_strategy_{datetime.now().strftime('%Y%m%d_%H%M')}",
            json.dumps(strategy_config, indent=2),
            1  # Set as active
        ))
        
        # Deactivate previous configurations
        cursor.execute('''
            UPDATE optimized_strategy_config 
            SET active = 0 
            WHERE config_name != ?
        ''', (f"optimized_strategy_{datetime.now().strftime('%Y%m%d_%H%M')}",))
        
        conn.commit()
        conn.close()
        
        # Also save to file
        with open('optimized_strategy_config.json', 'w') as f:
            json.dump(strategy_config, f, indent=2)
        
        logger.info("Optimized strategy configuration saved")
    
    def generate_optimization_report(self, results_df: pd.DataFrame) -> str:
        """Generate comprehensive optimization report"""
        report_lines = []
        
        report_lines.append("=" * 80)
        report_lines.append("CRYPTO PAPER TRADING - STRATEGY OPTIMIZATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Based on {len(results_df)} historical trades")
        report_lines.append("")
        
        # Current performance baseline
        baseline_win_rate = (results_df['profit_loss_pct'] > 0).mean() * 100
        baseline_pnl = results_df['profit_loss_pct'].sum()
        baseline_avg_trade = results_df['profit_loss_pct'].mean()
        
        report_lines.append("BASELINE PERFORMANCE:")
        report_lines.append(f"  Win Rate: {baseline_win_rate:.2f}%")
        report_lines.append(f"  Total P&L: {baseline_pnl:.2f}%")
        report_lines.append(f"  Average Trade: {baseline_avg_trade:.2f}%")
        report_lines.append("")
        
        # Optimization results
        optimization = self.generate_optimized_strategy(results_df)
        
        report_lines.append("OPTIMIZED STRATEGY PARAMETERS:")
        report_lines.append(f"  Stop Loss: {optimization['risk_management']['stop_loss_pct']:.1f}%")
        report_lines.append(f"  Take Profit: {optimization['risk_management']['take_profit_pct']:.1f}%")
        report_lines.append(f"  Risk/Reward: {optimization['risk_management']['risk_reward_ratio']:.2f}")
        report_lines.append("")
        
        report_lines.append("SYMBOL RECOMMENDATIONS:")
        for symbol in optimization['symbol_selection']['top_symbols'][:5]:
            report_lines.append(f"  - {symbol}")
        report_lines.append("")
        
        report_lines.append("TIMING RECOMMENDATIONS:")
        report_lines.append(f"  Best Entry Hours: {optimization['entry_criteria']['preferred_entry_hours']}")
        report_lines.append(f"  Avoid Hours: {optimization['entry_criteria']['avoid_entry_hours']}")
        report_lines.append("")
        
        report_lines.append("EXPECTED IMPROVEMENTS:")
        report_lines.append(f"  Target Win Rate: {optimization['performance_targets']['expected_win_rate']:.1f}%")
        report_lines.append(f"  Target Profit Factor: {optimization['performance_targets']['expected_profit_factor']:.2f}")
        report_lines.append("")
        
        report_lines.append("IMPLEMENTATION RECOMMENDATIONS:")
        report_lines.append("1. Update signal_processor.py with new SL/TP levels")
        report_lines.append("2. Add symbol filtering based on top performers")
        report_lines.append("3. Implement entry timing filters")
        report_lines.append("4. Set up automated performance monitoring")
        report_lines.append("5. Review and reoptimize monthly")
        
        report_content = "\n".join(report_lines)
        
        # Save report to file
        with open('optimization_report.txt', 'w') as f:
            f.write(report_content)
        
        return report_content

def main():
    """Main function to run strategy optimization"""
    optimizer = StrategyOptimizer()
    
    print("=== Crypto Paper Trading Strategy Optimizer ===")
    print("This will analyze backtest results and optimize trading parameters")
    
    # Load backtest results
    results_df = optimizer.load_backtest_results()
    
    if results_df.empty:
        print("No backtest results found. Please run backtesting_engine.py first.")
        return
    
    print(f"\nAnalyzing {len(results_df)} historical trades...")
    
    # Generate optimization report
    report = optimizer.generate_optimization_report(results_df)
    
    print("\n" + report)
    
    print(f"\n=== Optimization Complete ===")
    print(f"Optimized strategy saved to: optimized_strategy_config.json")
    print(f"Full report saved to: optimization_report.txt")

if __name__ == "__main__":
    main()