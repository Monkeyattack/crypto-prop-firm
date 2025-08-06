#!/usr/bin/env python3
"""
Backtesting Engine - Analyze historical signal performance and optimize strategies
"""

import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BacktestingEngine:
    def __init__(self):
        self.db_path = 'trading.db'
        self.results = {}
        
        # Initialize results database
        self.init_results_database()
    
    def init_results_database(self):
        """Initialize database for backtest results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                exit_price REAL,
                take_profit REAL,
                stop_loss REAL,
                entry_time DATETIME,
                exit_time DATETIME,
                exit_reason TEXT,
                profit_loss REAL,
                profit_loss_pct REAL,
                trade_duration_hours REAL,
                max_favorable_excursion REAL,
                max_adverse_excursion REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimization_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT,
                parameter_set TEXT,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate REAL,
                total_pnl REAL,
                avg_win REAL,
                avg_loss REAL,
                profit_factor REAL,
                max_drawdown REAL,
                sharpe_ratio REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_historical_signals(self) -> pd.DataFrame:
        """Load historical signals from database"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT * FROM historical_signals 
            WHERE parsed_successfully = 1 
            AND symbol IS NOT NULL 
            AND side IS NOT NULL
            ORDER BY message_date
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Convert date column
        df['message_date'] = pd.to_datetime(df['message_date'])
        
        logger.info(f"Loaded {len(df)} historical signals for backtesting")
        return df
    
    def get_price_data(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Get historical price data for a symbol"""
        try:
            # Convert crypto symbols to Yahoo Finance format
            if symbol.upper().endswith('USDT'):
                yf_symbol = symbol.replace('USDT', '-USD')
            elif symbol.upper() in ['BTC', 'ETH', 'ADA', 'DOT', 'LINK', 'UNI']:
                yf_symbol = f"{symbol.upper()}-USD"
            else:
                yf_symbol = symbol
            
            # Download data with buffer for analysis
            buffer_start = start_date - timedelta(days=1)
            buffer_end = end_date + timedelta(days=1)
            
            data = yf.download(
                yf_symbol,
                start=buffer_start,
                end=buffer_end,
                interval='1h',
                progress=False
            )
            
            if data.empty:
                logger.warning(f"No price data found for {symbol}")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching price data for {symbol}: {e}")
            return None
    
    def simulate_trade(self, signal: dict, price_data: pd.DataFrame) -> dict:
        """Simulate a single trade based on signal and price data"""
        try:
            entry_time = pd.to_datetime(signal['message_date'])
            symbol = signal['symbol']
            side = signal['side'].upper()
            entry_price = float(signal['entry_price'])
            take_profit = float(signal['take_profit']) if signal['take_profit'] else None
            stop_loss = float(signal['stop_loss']) if signal['stop_loss'] else None
            
            # Find entry point in price data (next available hour after signal)
            entry_idx = price_data.index.searchsorted(entry_time)
            if entry_idx >= len(price_data):
                return None
            
            actual_entry_time = price_data.index[entry_idx]
            actual_entry_price = price_data.iloc[entry_idx]['Open']
            
            # Simulate trade execution
            exit_time = None
            exit_price = None
            exit_reason = None
            max_favorable = 0
            max_adverse = 0
            
            # Track trade for up to 7 days or until exit condition
            max_duration = min(168, len(price_data) - entry_idx)  # 168 hours = 7 days
            
            for i in range(entry_idx, entry_idx + max_duration):
                current_time = price_data.index[i]
                high = price_data.iloc[i]['High']
                low = price_data.iloc[i]['Low']
                close = price_data.iloc[i]['Close']
                
                # Calculate favorable and adverse excursions
                if side == 'BUY' or side == 'LONG':
                    favorable = high - actual_entry_price
                    adverse = actual_entry_price - low
                    
                    # Check take profit
                    if take_profit and high >= take_profit:
                        exit_time = current_time
                        exit_price = take_profit
                        exit_reason = 'take_profit'
                        break
                    
                    # Check stop loss
                    if stop_loss and low <= stop_loss:
                        exit_time = current_time
                        exit_price = stop_loss
                        exit_reason = 'stop_loss'
                        break
                        
                else:  # SELL or SHORT
                    favorable = actual_entry_price - low
                    adverse = high - actual_entry_price
                    
                    # Check take profit (price going down)
                    if take_profit and low <= take_profit:
                        exit_time = current_time
                        exit_price = take_profit
                        exit_reason = 'take_profit'
                        break
                    
                    # Check stop loss (price going up)
                    if stop_loss and high >= stop_loss:
                        exit_time = current_time
                        exit_price = stop_loss
                        exit_reason = 'stop_loss'
                        break
                
                # Update max excursions
                max_favorable = max(max_favorable, favorable)
                max_adverse = max(max_adverse, adverse)
            
            # If no exit condition was met, exit at market close after max duration
            if exit_time is None:
                exit_time = price_data.index[min(entry_idx + max_duration - 1, len(price_data) - 1)]
                exit_price = price_data.loc[exit_time, 'Close']
                exit_reason = 'time_exit'
            
            # Calculate P&L
            if side == 'BUY' or side == 'LONG':
                profit_loss = exit_price - actual_entry_price
            else:  # SELL or SHORT
                profit_loss = actual_entry_price - exit_price
            
            profit_loss_pct = (profit_loss / actual_entry_price) * 100
            trade_duration = (exit_time - actual_entry_time).total_seconds() / 3600  # hours
            
            return {
                'signal_id': signal['id'],
                'symbol': symbol,
                'side': side,
                'entry_price': actual_entry_price,
                'exit_price': exit_price,
                'take_profit': take_profit,
                'stop_loss': stop_loss,
                'entry_time': actual_entry_time,
                'exit_time': exit_time,
                'exit_reason': exit_reason,
                'profit_loss': profit_loss,
                'profit_loss_pct': profit_loss_pct,
                'trade_duration_hours': trade_duration,
                'max_favorable_excursion': max_favorable,
                'max_adverse_excursion': max_adverse
            }
            
        except Exception as e:
            logger.error(f"Error simulating trade for {signal['symbol']}: {e}")
            return None
    
    def run_backtest(self) -> pd.DataFrame:
        """Run complete backtest on historical signals"""
        signals_df = self.load_historical_signals()
        
        if signals_df.empty:
            logger.error("No historical signals found for backtesting")
            return pd.DataFrame()
        
        results = []
        processed_symbols = set()
        
        # Group signals by symbol for efficient data fetching
        for symbol in signals_df['symbol'].unique():
            if pd.isna(symbol) or symbol in processed_symbols:
                continue
                
            symbol_signals = signals_df[signals_df['symbol'] == symbol].copy()
            
            # Get date range for this symbol
            start_date = symbol_signals['message_date'].min()
            end_date = symbol_signals['message_date'].max()
            
            logger.info(f"Processing {len(symbol_signals)} signals for {symbol}")
            
            # Get price data
            price_data = self.get_price_data(symbol, start_date, end_date)
            
            if price_data is None or price_data.empty:
                logger.warning(f"Skipping {symbol} - no price data available")
                continue
            
            # Process each signal for this symbol
            for _, signal in symbol_signals.iterrows():
                trade_result = self.simulate_trade(signal.to_dict(), price_data)
                
                if trade_result:
                    results.append(trade_result)
                    
                    # Store result in database
                    self.store_backtest_result(trade_result)
            
            processed_symbols.add(symbol)
        
        results_df = pd.DataFrame(results)
        
        if not results_df.empty:
            logger.info(f"Backtest completed: {len(results_df)} trades simulated")
            self.analyze_results(results_df)
        
        return results_df
    
    def store_backtest_result(self, result: dict):
        """Store backtest result in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO backtest_results 
            (signal_id, symbol, side, entry_price, exit_price, take_profit, stop_loss,
             entry_time, exit_time, exit_reason, profit_loss, profit_loss_pct,
             trade_duration_hours, max_favorable_excursion, max_adverse_excursion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result['signal_id'], result['symbol'], result['side'],
            result['entry_price'], result['exit_price'], result['take_profit'], result['stop_loss'],
            result['entry_time'], result['exit_time'], result['exit_reason'],
            result['profit_loss'], result['profit_loss_pct'], result['trade_duration_hours'],
            result['max_favorable_excursion'], result['max_adverse_excursion']
        ))
        
        conn.commit()
        conn.close()
    
    def analyze_results(self, results_df: pd.DataFrame):
        """Analyze backtest results and generate insights"""
        if results_df.empty:
            return
        
        print("\n" + "="*60)
        print("BACKTEST RESULTS ANALYSIS")
        print("="*60)
        
        # Basic statistics
        total_trades = len(results_df)
        winning_trades = len(results_df[results_df['profit_loss'] > 0])
        losing_trades = len(results_df[results_df['profit_loss'] < 0])
        
        win_rate = (winning_trades / total_trades) * 100
        total_pnl = results_df['profit_loss_pct'].sum()
        avg_win = results_df[results_df['profit_loss'] > 0]['profit_loss_pct'].mean()
        avg_loss = results_df[results_df['profit_loss'] < 0]['profit_loss_pct'].mean()
        
        print(f"Total Trades: {total_trades}")
        print(f"Winning Trades: {winning_trades}")
        print(f"Losing Trades: {losing_trades}")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Total P&L: {total_pnl:.2f}%")
        print(f"Average Win: {avg_win:.2f}%")
        print(f"Average Loss: {avg_loss:.2f}%")
        
        # Profit factor
        if avg_loss != 0:
            profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades))
            print(f"Profit Factor: {profit_factor:.2f}")
        
        # Exit reason analysis
        print(f"\nExit Reasons:")
        exit_reasons = results_df['exit_reason'].value_counts()
        for reason, count in exit_reasons.items():
            pct = (count / total_trades) * 100
            print(f"  {reason}: {count} ({pct:.1f}%)")
        
        # Symbol performance
        print(f"\nTop Performing Symbols:")
        symbol_performance = results_df.groupby('symbol')['profit_loss_pct'].agg(['sum', 'mean', 'count']).round(2)
        symbol_performance = symbol_performance.sort_values('sum', ascending=False)
        print(symbol_performance.head(10))
        
        # Generate optimization recommendations
        self.generate_optimization_recommendations(results_df)
    
    def generate_optimization_recommendations(self, results_df: pd.DataFrame):
        """Generate recommendations for strategy optimization"""
        print(f"\n" + "="*60)
        print("OPTIMIZATION RECOMMENDATIONS")
        print("="*60)
        
        # Analyze stop loss effectiveness
        sl_hits = results_df[results_df['exit_reason'] == 'stop_loss']
        tp_hits = results_df[results_df['exit_reason'] == 'take_profit']
        
        if len(sl_hits) > 0:
            avg_sl_loss = sl_hits['profit_loss_pct'].mean()
            print(f"Average Stop Loss Hit: {avg_sl_loss:.2f}%")
        
        if len(tp_hits) > 0:
            avg_tp_gain = tp_hits['profit_loss_pct'].mean()
            print(f"Average Take Profit Hit: {avg_tp_gain:.2f}%")
        
        # Analyze trade duration
        avg_duration = results_df['trade_duration_hours'].mean()
        print(f"Average Trade Duration: {avg_duration:.1f} hours")
        
        # Quick wins duration analysis
        quick_wins = results_df[(results_df['profit_loss'] > 0) & (results_df['trade_duration_hours'] < 24)]
        if len(quick_wins) > 0:
            print(f"Quick Wins (<24h): {len(quick_wins)} trades, avg: {quick_wins['profit_loss_pct'].mean():.2f}%")
        
        # Risk/reward analysis
        print(f"\nRisk/Reward Analysis:")
        for side in ['BUY', 'SELL', 'LONG', 'SHORT']:
            side_data = results_df[results_df['side'] == side]
            if len(side_data) > 0:
                side_wr = (len(side_data[side_data['profit_loss'] > 0]) / len(side_data)) * 100
                side_pnl = side_data['profit_loss_pct'].sum()
                print(f"  {side}: {len(side_data)} trades, {side_wr:.1f}% win rate, {side_pnl:.2f}% total P&L")
        
        print(f"\nKey Recommendations:")
        print(f"1. Consider tighter stop losses if current avg SL loss > -3%")
        print(f"2. Evaluate extending take profits if current avg TP < 5%")
        print(f"3. Focus on symbols with consistent positive performance")
        print(f"4. Consider time-based exits for trades lasting > 48 hours")
    
    def optimize_parameters(self, results_df: pd.DataFrame):
        """Run parameter optimization analysis"""
        if results_df.empty:
            return
        
        print(f"\n" + "="*60)
        print("PARAMETER OPTIMIZATION")
        print("="*60)
        
        # Test different stop loss levels
        sl_levels = [0.02, 0.03, 0.05, 0.08, 0.10]  # 2%, 3%, 5%, 8%, 10%
        tp_levels = [0.05, 0.08, 0.10, 0.15, 0.20]  # 5%, 8%, 10%, 15%, 20%
        
        best_combo = None
        best_score = -float('inf')
        
        print("Testing Stop Loss / Take Profit combinations:")
        
        for sl in sl_levels:
            for tp in tp_levels:
                # Simulate with new parameters
                score = self.test_parameters(results_df, sl, tp)
                
                if score > best_score:
                    best_score = score
                    best_combo = (sl, tp)
                
                print(f"SL: {sl*100:.0f}%, TP: {tp*100:.0f}% -> Score: {score:.2f}")
        
        if best_combo:
            print(f"\nBest combination: SL {best_combo[0]*100:.0f}%, TP {best_combo[1]*100:.0f}% (Score: {best_score:.2f})")
    
    def test_parameters(self, results_df: pd.DataFrame, sl_pct: float, tp_pct: float) -> float:
        """Test specific SL/TP parameters and return performance score"""
        # This is a simplified version - you'd implement full re-simulation here
        # For now, we'll use the existing data to estimate performance
        
        modified_results = results_df.copy()
        
        # Estimate new exits based on max favorable/adverse excursions
        for idx, row in modified_results.iterrows():
            entry_price = row['entry_price']
            side = row['side']
            
            if side in ['BUY', 'LONG']:
                new_tp = entry_price * (1 + tp_pct)
                new_sl = entry_price * (1 - sl_pct)
                
                # Check if TP would have been hit
                if row['max_favorable_excursion'] >= (new_tp - entry_price):
                    modified_results.at[idx, 'profit_loss_pct'] = tp_pct * 100
                # Check if SL would have been hit
                elif row['max_adverse_excursion'] >= (entry_price - new_sl):
                    modified_results.at[idx, 'profit_loss_pct'] = -sl_pct * 100
            
            else:  # SELL, SHORT
                new_tp = entry_price * (1 - tp_pct)
                new_sl = entry_price * (1 + sl_pct)
                
                # Check if TP would have been hit
                if row['max_favorable_excursion'] >= (entry_price - new_tp):
                    modified_results.at[idx, 'profit_loss_pct'] = tp_pct * 100
                # Check if SL would have been hit
                elif row['max_adverse_excursion'] >= (new_sl - entry_price):
                    modified_results.at[idx, 'profit_loss_pct'] = -sl_pct * 100
        
        # Calculate performance score (weighted win rate and total return)
        win_rate = len(modified_results[modified_results['profit_loss_pct'] > 0]) / len(modified_results)
        total_return = modified_results['profit_loss_pct'].sum()
        
        # Score combines win rate and total return
        score = (win_rate * 50) + (total_return * 0.5)
        
        return score

def main():
    """Main function to run backtesting"""
    engine = BacktestingEngine()
    
    print("=== Crypto Paper Trading Backtesting Engine ===")
    print("This will analyze historical signals and optimize trading parameters")
    
    # Run backtest
    print("\nRunning backtest on historical signals...")
    results_df = engine.run_backtest()
    
    if not results_df.empty:
        # Run parameter optimization
        print("\nRunning parameter optimization...")
        engine.optimize_parameters(results_df)
        
        print(f"\n=== Analysis Complete ===")
        print(f"Results stored in database for further analysis")
        print(f"Consider updating your trading strategy based on the recommendations")
    else:
        print("No results generated - check if historical signals exist")

if __name__ == "__main__":
    main()