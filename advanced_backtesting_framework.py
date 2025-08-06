#!/usr/bin/env python3
"""
Advanced Backtesting Framework - Risk-Based Position Sizing & Micro-Profit Analysis
"""

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedBacktestingFramework:
    def __init__(self):
        self.db_path = 'trading.db'
        self.initial_capital = 10000  # Starting with $10k
        
        # Coinbase One fee structure
        self.fee_structure = {
            'maker_fee': 0.0,      # 0% with Coinbase One
            'taker_fee': 0.006,    # 0.6% reduced taker fee
            'preferred_maker': True # Always try to be maker
        }
        
        # Coin categories
        self.blue_chips = ['BTCUSDT', 'ETHUSDT']
        self.quality_alts = ['SOLUSDT', 'ADAUSDT', 'DOTUSDT', 'MATICUSDT']
        
        # Test strategies
        self.strategies = {
            'ultra_micro': {
                'name': 'Ultra Micro (0.1-0.3%)',
                'tp_range': [0.1, 0.2, 0.3],
                'risk_reward_ratios': [(1, 1), (1, 2), (1, 3)],  # Risk 0.1% for 0.1% reward, etc.
                'max_loss_multiplier': 100,  # Max 10% loss for 0.1% target
                'hold_indefinite': False,
                'max_hold_days': 1
            },
            'micro': {
                'name': 'Micro (0.5-1%)',
                'tp_range': [0.5, 0.75, 1.0],
                'risk_reward_ratios': [(1, 1), (1, 2), (1, 3)],
                'max_loss_multiplier': 20,  # Max 10-20% loss
                'hold_indefinite': False,
                'max_hold_days': 3
            },
            'balanced_micro': {
                'name': 'Balanced Micro (1-2%)',
                'tp_range': [1.0, 1.5, 2.0],
                'risk_reward_ratios': [(2, 1), (3, 1), (4, 1)],
                'max_loss_multiplier': 10,
                'hold_indefinite': False,
                'max_hold_days': 7
            },
            'adaptive': {
                'name': 'Adaptive (Blue Chip vs Alt)',
                'blue_chip_config': {
                    'tp_range': [0.5, 1.0, 2.0],
                    'sl_range': [5, 10, 20],  # Wider stops for blue chips
                    'position_size_multiplier': 2,  # 2x position size
                    'hold_indefinite': True
                },
                'alt_config': {
                    'tp_range': [1.0, 2.0, 3.0],
                    'sl_range': [3, 5, 7],  # Tighter stops for alts
                    'position_size_multiplier': 0.5,  # 0.5x position size
                    'hold_indefinite': False,
                    'max_hold_days': 5
                }
            }
        }
        
        self.init_results_tables()
    
    def init_results_tables(self):
        """Initialize backtesting results tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_results_advanced (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT,
                test_date DATETIME,
                parameters TEXT,
                
                -- Performance metrics
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                held_positions INTEGER,
                win_rate REAL,
                
                -- Financial metrics
                total_profit_pct REAL,
                avg_profit_per_trade REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                
                -- Fee analysis
                total_fees_paid REAL,
                avg_fee_per_trade REAL,
                profit_after_fees REAL,
                
                -- Risk metrics
                avg_position_size REAL,
                max_position_size REAL,
                avg_exposure_pct REAL,
                max_exposure_pct REAL,
                
                -- Time metrics
                avg_trade_duration_hours REAL,
                trades_per_day REAL,
                
                -- Detailed results
                trade_log TEXT,
                equity_curve TEXT,
                coin_performance TEXT
            )
        ''')
        
        # Parameter optimization table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parameter_optimization (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT,
                tp_pct REAL,
                sl_pct REAL,
                risk_reward_ratio REAL,
                position_size_pct REAL,
                max_exposure_pct REAL,
                
                -- Results
                win_rate REAL,
                avg_profit REAL,
                sharpe_ratio REAL,
                profit_after_fees REAL,
                
                -- Ranking
                score REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def calculate_position_size(self, capital: float, tp_pct: float, sl_pct: float, 
                              symbol: str, strategy: str) -> Dict:
        """Calculate position size based on risk/reward"""
        
        # Base position size (% of capital)
        base_position_pct = 2.0  # Start with 2% base
        
        # Adjust for risk/reward ratio
        risk_reward = tp_pct / sl_pct if sl_pct > 0 else 1
        
        if risk_reward < 0.1:  # Very poor R:R (e.g., 0.1% TP, 10% SL)
            position_multiplier = 0.1  # Only risk 0.2% of capital
        elif risk_reward < 0.5:
            position_multiplier = 0.25
        elif risk_reward < 1:
            position_multiplier = 0.5
        elif risk_reward < 2:
            position_multiplier = 1.0
        else:  # Great R:R
            position_multiplier = 1.5
        
        # Adjust for coin type
        if symbol in self.blue_chips:
            coin_multiplier = 2.0  # Double position for blue chips
            max_position_pct = 20.0  # Can go up to 20% per position
        elif symbol in self.quality_alts:
            coin_multiplier = 1.0
            max_position_pct = 10.0
        else:
            coin_multiplier = 0.5  # Half position for unknown alts
            max_position_pct = 5.0
        
        # Calculate final position size
        position_pct = base_position_pct * position_multiplier * coin_multiplier
        position_pct = min(position_pct, max_position_pct)
        
        position_size = capital * (position_pct / 100)
        
        # Calculate maximum acceptable loss
        max_loss = position_size * (sl_pct / 100)
        
        return {
            'position_size': position_size,
            'position_pct': position_pct,
            'max_loss': max_loss,
            'risk_reward': risk_reward,
            'coin_category': 'blue_chip' if symbol in self.blue_chips else 
                           'quality_alt' if symbol in self.quality_alts else 'other'
        }
    
    def simulate_micro_profit_strategy(self, signals_df: pd.DataFrame, 
                                     tp_pct: float, sl_pct: float,
                                     max_exposure_pct: float = 50) -> Dict:
        """Simulate a micro-profit strategy with given parameters"""
        
        capital = self.initial_capital
        trades = []
        open_positions = {}
        equity_curve = [capital]
        
        for _, signal in signals_df.iterrows():
            current_time = signal['message_date']
            symbol = signal['symbol']
            
            # Check if we can open new position
            total_exposure = sum(pos['size'] for pos in open_positions.values())
            exposure_pct = (total_exposure / capital) * 100
            
            if exposure_pct < max_exposure_pct:
                # Calculate position size
                pos_info = self.calculate_position_size(capital, tp_pct, sl_pct, symbol, 'micro')
                
                # Check if we have enough capital
                if capital >= pos_info['position_size']:
                    # Open position
                    entry_price = signal['entry_price'] if 'entry_price' in signal else signal.get('entry', 0)
                    
                    if entry_price > 0:
                        # Calculate TP/SL prices
                        if signal['side'] in ['BUY', 'LONG']:
                            tp_price = entry_price * (1 + tp_pct / 100)
                            sl_price = entry_price * (1 - sl_pct / 100)
                        else:
                            tp_price = entry_price * (1 - tp_pct / 100)
                            sl_price = entry_price * (1 + sl_pct / 100)
                        
                        position_id = f"{symbol}_{current_time}"
                        open_positions[position_id] = {
                            'symbol': symbol,
                            'side': signal['side'],
                            'entry_price': entry_price,
                            'tp_price': tp_price,
                            'sl_price': sl_price,
                            'size': pos_info['position_size'],
                            'entry_time': current_time,
                            'category': pos_info['coin_category']
                        }
            
            # Simulate price movement and check exits
            # (In real backtesting, we'd use actual price data)
            positions_to_close = []
            
            for pos_id, pos in open_positions.items():
                # Simulate with historical probabilities
                days_held = (current_time - pos['entry_time']).days if isinstance(current_time, datetime) else 0
                
                # Micro profits hit quickly
                if tp_pct <= 0.5:
                    tp_hit_prob = 0.7  # 70% chance for 0.5% move
                elif tp_pct <= 1.0:
                    tp_hit_prob = 0.6  # 60% chance for 1% move
                else:
                    tp_hit_prob = 0.5  # 50% chance for larger moves
                
                # Adjust for time held
                tp_hit_prob += days_held * 0.05  # 5% more likely each day
                
                if np.random.random() < tp_hit_prob:
                    # Take profit hit
                    pnl_pct = tp_pct
                    exit_reason = 'tp'
                elif pos['category'] != 'blue_chip' and days_held > 5:
                    # Force exit for non-blue chips
                    current_pnl = np.random.uniform(-sl_pct/2, tp_pct/2)
                    pnl_pct = current_pnl
                    exit_reason = 'time_exit'
                else:
                    continue  # Position stays open
                
                # Calculate fees
                entry_fee = pos['size'] * self.fee_structure['taker_fee']
                exit_fee = pos['size'] * self.fee_structure['maker_fee']  # Try to be maker on exit
                total_fees = entry_fee + exit_fee
                
                # Calculate profit/loss
                pnl = pos['size'] * (pnl_pct / 100) - total_fees
                capital += pnl
                
                trades.append({
                    'symbol': pos['symbol'],
                    'side': pos['side'],
                    'entry_time': pos['entry_time'],
                    'exit_time': current_time,
                    'position_size': pos['size'],
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'fees': total_fees,
                    'exit_reason': exit_reason,
                    'days_held': days_held
                })
                
                positions_to_close.append(pos_id)
            
            # Remove closed positions
            for pos_id in positions_to_close:
                del open_positions[pos_id]
            
            equity_curve.append(capital)
        
        # Calculate metrics
        if trades:
            trades_df = pd.DataFrame(trades)
            winning_trades = len(trades_df[trades_df['pnl'] > 0])
            total_fees = trades_df['fees'].sum()
            
            results = {
                'total_trades': len(trades),
                'winning_trades': winning_trades,
                'win_rate': winning_trades / len(trades) * 100,
                'total_profit_pct': ((capital - self.initial_capital) / self.initial_capital) * 100,
                'avg_profit_per_trade': trades_df['pnl'].mean(),
                'total_fees_paid': total_fees,
                'profit_after_fees': capital - self.initial_capital,
                'avg_trade_duration': trades_df['days_held'].mean(),
                'trades_df': trades_df,
                'equity_curve': equity_curve
            }
        else:
            results = {
                'total_trades': 0,
                'winning_trades': 0,
                'win_rate': 0,
                'total_profit_pct': 0,
                'avg_profit_per_trade': 0,
                'total_fees_paid': 0,
                'profit_after_fees': 0,
                'avg_trade_duration': 0,
                'trades_df': pd.DataFrame(),
                'equity_curve': equity_curve
            }
        
        return results
    
    def run_comprehensive_backtest(self):
        """Run all strategy backtests and save results"""
        logger.info("Starting comprehensive backtesting...")
        
        # Load historical signals
        conn = sqlite3.connect(self.db_path)
        signals_df = pd.read_sql_query('''
            SELECT * FROM historical_signals 
            WHERE parsed_successfully = 1
            ORDER BY message_date
        ''', conn)
        conn.close()
        
        if signals_df.empty:
            logger.error("No historical signals found")
            return
        
        all_results = []
        
        # Test each strategy
        for strategy_key, strategy in self.strategies.items():
            if strategy_key == 'adaptive':
                # Special handling for adaptive strategy
                continue
            
            logger.info(f"Testing {strategy['name']}...")
            
            # Test different parameter combinations
            for tp in strategy['tp_range']:
                for rr_ratio in strategy['risk_reward_ratios']:
                    # Calculate stop loss based on risk/reward
                    sl = tp * rr_ratio[0] / rr_ratio[1]
                    
                    # Limit stop loss
                    max_sl = tp * strategy['max_loss_multiplier']
                    sl = min(sl, max_sl)
                    
                    # Test different exposure levels
                    for max_exposure in [30, 50, 70]:
                        results = self.simulate_micro_profit_strategy(
                            signals_df, tp, sl, max_exposure
                        )
                        
                        # Save results
                        test_result = {
                            'strategy_name': strategy['name'],
                            'tp_pct': tp,
                            'sl_pct': sl,
                            'risk_reward_ratio': tp / sl,
                            'max_exposure_pct': max_exposure,
                            **results
                        }
                        
                        all_results.append(test_result)
                        
                        # Log to database
                        self.save_backtest_result(test_result)
        
        # Find optimal parameters
        self.analyze_and_rank_results(all_results)
        
        logger.info("Backtesting complete!")
        return all_results
    
    def save_backtest_result(self, result: Dict):
        """Save individual backtest result to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Prepare data
        parameters = {
            'tp_pct': result['tp_pct'],
            'sl_pct': result['sl_pct'],
            'risk_reward_ratio': result['risk_reward_ratio'],
            'max_exposure_pct': result['max_exposure_pct']
        }
        
        # Save to main results table
        cursor.execute('''
            INSERT INTO backtest_results_advanced (
                strategy_name, test_date, parameters,
                total_trades, winning_trades, win_rate,
                total_profit_pct, avg_profit_per_trade,
                total_fees_paid, profit_after_fees,
                avg_trade_duration_hours
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result['strategy_name'],
            datetime.now(),
            json.dumps(parameters),
            result['total_trades'],
            result['winning_trades'],
            result['win_rate'],
            result['total_profit_pct'],
            result['avg_profit_per_trade'],
            result['total_fees_paid'],
            result['profit_after_fees'],
            result['avg_trade_duration'] * 24  # Convert days to hours
        ))
        
        # Save to optimization table
        cursor.execute('''
            INSERT INTO parameter_optimization (
                strategy_name, tp_pct, sl_pct, risk_reward_ratio,
                position_size_pct, max_exposure_pct,
                win_rate, avg_profit, profit_after_fees
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result['strategy_name'],
            result['tp_pct'],
            result['sl_pct'],
            result['risk_reward_ratio'],
            2.0,  # Base position size
            result['max_exposure_pct'],
            result['win_rate'],
            result['avg_profit_per_trade'],
            result['profit_after_fees']
        ))
        
        conn.commit()
        conn.close()
    
    def analyze_and_rank_results(self, results: List[Dict]):
        """Analyze results and find optimal parameters"""
        results_df = pd.DataFrame(results)
        
        # Calculate score for each strategy
        # Weighted scoring: 40% profit, 30% win rate, 20% consistency, 10% low drawdown
        for idx, row in results_df.iterrows():
            profit_score = row['profit_after_fees'] / 1000  # Normalize to score
            win_rate_score = row['win_rate'] / 100
            consistency_score = 1 / (1 + abs(row['avg_profit_per_trade']))  # Prefer consistent small profits
            
            total_score = (profit_score * 0.4 + 
                         win_rate_score * 0.3 + 
                         consistency_score * 0.2 +
                         0.1)  # Drawdown placeholder
            
            results_df.at[idx, 'score'] = total_score
        
        # Find top strategies
        top_strategies = results_df.nlargest(10, 'score')
        
        logger.info("\n=== TOP STRATEGIES ===")
        for _, strategy in top_strategies.iterrows():
            logger.info(f"""
            Strategy: {strategy['strategy_name']}
            TP: {strategy['tp_pct']}% | SL: {strategy['sl_pct']}%
            Win Rate: {strategy['win_rate']:.1f}%
            Profit After Fees: ${strategy['profit_after_fees']:.2f}
            Score: {strategy['score']:.3f}
            """)
        
        # Save rankings
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for _, row in results_df.iterrows():
            cursor.execute('''
                UPDATE parameter_optimization 
                SET score = ? 
                WHERE strategy_name = ? AND tp_pct = ? AND sl_pct = ?
            ''', (row['score'], row['strategy_name'], row['tp_pct'], row['sl_pct']))
        
        conn.commit()
        conn.close()
        
        return top_strategies

if __name__ == "__main__":
    framework = AdvancedBacktestingFramework()
    results = framework.run_comprehensive_backtest()