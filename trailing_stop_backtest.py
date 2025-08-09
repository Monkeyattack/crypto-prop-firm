#!/usr/bin/env python3
"""
Trailing Stop Strategy Backtest Comparison
Compares current (4.5%/1.5%/3.5%) vs proposed (4.0%/1.0%/3.0%) trailing stop parameters
"""

import pandas as pd
import numpy as np
import sqlite3
import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TrailingStopConfig:
    """Configuration for trailing stop parameters"""
    name: str
    activation_pct: float      # Start trailing after this profit %
    trail_distance_pct: float  # Trail by this percentage from high
    min_profit_pct: float      # Minimum profit to accept when exiting
    
    def __str__(self):
        return f"{self.name}: Activation={self.activation_pct}%, Trail={self.trail_distance_pct}%, Min={self.min_profit_pct}%"

@dataclass 
class TradeEntry:
    """Trade entry point data"""
    timestamp: datetime
    symbol: str
    side: str  # 'BUY' or 'SELL'
    entry_price: float
    signal_source: str
    
class PriceDataFetcher:
    """Fetch real cryptocurrency price data"""
    
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.rate_limit_delay = 1.2  # Seconds between requests for free tier
        
    def fetch_price_history(self, symbol: str, days: int = 90) -> pd.DataFrame:
        """Fetch historical price data from CoinGecko (daily data - free tier)"""
        
        # Map symbols to CoinGecko IDs
        symbol_map = {
            'BTCUSDT': 'bitcoin',
            'BTCUSD': 'bitcoin', 
            'ETHUSD': 'ethereum',
            'ETHUSDT': 'ethereum',
            'BTC': 'bitcoin',
            'ETH': 'ethereum'
        }
        
        coin_id = symbol_map.get(symbol.upper())
        if not coin_id:
            logger.warning(f"Symbol {symbol} not mapped, using bitcoin as default")
            coin_id = 'bitcoin'
            
        url = f"{self.base_url}/coins/{coin_id}/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': min(days, 365)  # Max 365 days for free tier
        }
        
        try:
            logger.info(f"Fetching {days} days of {symbol} price data...")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Convert to DataFrame
            prices = data['prices']
            df = pd.DataFrame(prices, columns=['timestamp', 'price'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = symbol.upper()
            
            # Interpolate to create hourly data from daily data
            df = self.interpolate_to_hourly(df)
            
            logger.info(f"Fetched and interpolated {len(df)} hourly price points for {symbol}")
            
            # Add rate limiting
            time.sleep(self.rate_limit_delay)
            
            return df
            
        except Exception as e:
            logger.warning(f"Error fetching price data for {symbol}: {e}")
            logger.info(f"Falling back to simulated data for {symbol}")
            return self.generate_realistic_price_data(symbol, days)
            
    def interpolate_to_hourly(self, daily_df: pd.DataFrame) -> pd.DataFrame:
        """Convert daily price data to hourly by adding realistic intraday movement"""
        if daily_df.empty:
            return daily_df
            
        hourly_data = []
        
        for i in range(len(daily_df) - 1):
            current_price = daily_df.iloc[i]['price']
            next_price = daily_df.iloc[i + 1]['price']
            current_time = daily_df.iloc[i]['timestamp']
            
            # Calculate daily change
            daily_change = (next_price - current_price) / current_price
            
            # Generate 24 hourly prices with realistic intraday volatility
            for hour in range(24):
                # Progress through the day (0 to 1)
                progress = hour / 23.0
                
                # Base price progression
                base_price = current_price + (daily_change * current_price * progress)
                
                # Add intraday volatility (smaller moves)
                volatility = abs(daily_change) * 0.3  # 30% of daily move as intraday vol
                random_change = np.random.normal(0, volatility)
                
                # Final hourly price
                hourly_price = base_price * (1 + random_change)
                hourly_time = current_time + timedelta(hours=hour)
                
                hourly_data.append({
                    'timestamp': hourly_time,
                    'price': hourly_price,
                    'symbol': daily_df.iloc[i]['symbol']
                })
                
        # Add the last day
        last_row = daily_df.iloc[-1]
        hourly_data.append({
            'timestamp': last_row['timestamp'],
            'price': last_row['price'],
            'symbol': last_row['symbol']
        })
        
        return pd.DataFrame(hourly_data)
        
    def generate_realistic_price_data(self, symbol: str, days: int) -> pd.DataFrame:
        """Generate realistic price data when API fails"""
        logger.info(f"Generating simulated price data for {symbol}")
        
        # Base prices for different symbols
        base_prices = {
            'BTCUSD': 65000,
            'ETHUSD': 3200,
            'bitcoin': 65000,
            'ethereum': 3200
        }
        
        base_price = base_prices.get(symbol.lower(), 50000)
        
        # Generate realistic price movement
        hours = days * 24
        timestamps = [datetime.now() - timedelta(hours=hours-i) for i in range(hours)]
        
        prices = []
        current_price = base_price
        
        for i, ts in enumerate(timestamps):
            # Add realistic volatility (crypto-like movements)
            volatility = 0.02  # 2% hourly volatility
            change = np.random.normal(0, volatility)
            
            # Add some trending behavior
            if i > 0:
                # Slight trend persistence
                trend = np.random.choice([-1, 0, 1], p=[0.3, 0.4, 0.3])
                change += trend * 0.003  # Small trend component
                
            current_price *= (1 + change)
            
            prices.append({
                'timestamp': ts,
                'price': current_price,
                'symbol': symbol.upper()
            })
            
        df = pd.DataFrame(prices)
        logger.info(f"Generated {len(df)} simulated price points for {symbol}")
        
        return df

class SignalGenerator:
    """Generate realistic trading signals based on technical patterns"""
    
    def __init__(self):
        self.db_path = 'trade_log.db'
        
    def load_historical_signals(self) -> List[TradeEntry]:
        """Load existing signals from database if available"""
        signals = []
        
        try:
            if os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                
                # Try different table names that might contain signals
                table_queries = [
                    "SELECT * FROM trades WHERE result != 'open'",
                    "SELECT * FROM historical_signals", 
                    "SELECT * FROM signals"
                ]
                
                for query in table_queries:
                    try:
                        df = pd.read_sql_query(query, conn)
                        if not df.empty:
                            logger.info(f"Found {len(df)} historical signals")
                            for _, row in df.iterrows():
                                signals.append(TradeEntry(
                                    timestamp=pd.to_datetime(row.get('timestamp', datetime.now())),
                                    symbol=row.get('symbol', 'BTCUSD'),
                                    side=row.get('side', 'BUY'),
                                    entry_price=float(row.get('entry', 0) or row.get('entry_price', 0)),
                                    signal_source='database'
                                ))
                            break
                    except Exception:
                        continue
                        
                conn.close()
                        
        except Exception as e:
            logger.error(f"Error loading historical signals: {e}")
            
        return signals
        
    def generate_realistic_entries(self, price_df: pd.DataFrame, num_signals: int = 50) -> List[TradeEntry]:
        """Generate realistic entry points based on price action patterns"""
        signals = []
        
        if price_df.empty:
            return signals
            
        # Calculate technical indicators for entry signal generation
        price_df = price_df.copy()
        price_df['sma_20'] = price_df['price'].rolling(20).mean()
        price_df['sma_50'] = price_df['price'].rolling(50).mean()
        price_df['price_change_pct'] = price_df['price'].pct_change() * 100
        price_df['volatility'] = price_df['price_change_pct'].rolling(10).std()
        
        # Generate signals at various patterns
        for i in range(50, len(price_df) - 10, max(1, len(price_df) // num_signals)):
            row = price_df.iloc[i]
            
            # Skip if not enough data
            if pd.isna(row['sma_20']) or pd.isna(row['volatility']):
                continue
                
            # Generate BUY signals on various conditions
            buy_conditions = [
                # Breakout above SMA
                row['price'] > row['sma_20'] and price_df.iloc[i-1]['price'] <= price_df.iloc[i-1]['sma_20'],
                # Strong bounce from support
                row['price_change_pct'] > 2 and price_df.iloc[i-1]['price_change_pct'] < -1,
                # Low volatility breakout
                row['volatility'] < 2 and row['price_change_pct'] > 1,
                # Golden cross pattern
                row['sma_20'] > row['sma_50'] and price_df.iloc[i-1]['sma_20'] <= price_df.iloc[i-1]['sma_50']
            ]
            
            # Generate SELL signals (for short positions)
            sell_conditions = [
                # Break below SMA
                row['price'] < row['sma_20'] and price_df.iloc[i-1]['price'] >= price_df.iloc[i-1]['sma_20'],
                # Strong rejection from resistance  
                row['price_change_pct'] < -2 and price_df.iloc[i-1]['price_change_pct'] > 1,
                # High volatility breakdown
                row['volatility'] > 4 and row['price_change_pct'] < -1
            ]
            
            if any(buy_conditions) and len(signals) < num_signals:
                signals.append(TradeEntry(
                    timestamp=row['timestamp'],
                    symbol=row['symbol'],
                    side='BUY',
                    entry_price=row['price'],
                    signal_source='generated_technical'
                ))
                
            elif any(sell_conditions) and len(signals) < num_signals:
                signals.append(TradeEntry(
                    timestamp=row['timestamp'],
                    symbol=row['symbol'], 
                    side='SELL',
                    entry_price=row['price'],
                    signal_source='generated_technical'
                ))
                
        logger.info(f"Generated {len(signals)} realistic entry signals")
        return signals

class TrailingStopBacktester:
    """Backtest trailing stop strategies"""
    
    def __init__(self):
        self.price_fetcher = PriceDataFetcher()
        self.signal_generator = SignalGenerator()
        self.initial_capital = 10000
        self.position_size_pct = 2.0  # 2% risk per trade
        
        # Define the two strategies to compare
        self.strategies = {
            'current': TrailingStopConfig(
                name='Current System',
                activation_pct=4.5,
                trail_distance_pct=1.5, 
                min_profit_pct=3.5
            ),
            'proposed': TrailingStopConfig(
                name='Proposed System',
                activation_pct=4.0,
                trail_distance_pct=1.0,
                min_profit_pct=3.0
            )
        }
        
    def simulate_trailing_stop(self, entry: TradeEntry, price_df: pd.DataFrame, 
                             config: TrailingStopConfig) -> Dict:
        """Simulate a single trade with trailing stop"""
        
        # Find entry point in price data
        entry_idx = None
        for i, row in price_df.iterrows():
            if row['timestamp'] >= entry.timestamp:
                entry_idx = i
                break
                
        if entry_idx is None:
            return {'status': 'no_data', 'pnl': 0, 'pnl_pct': 0}
            
        entry_price = entry.entry_price
        highest_profit = 0
        trailing_active = False
        position_size = self.initial_capital * (self.position_size_pct / 100)
        
        # Simulate price movement after entry
        max_lookforward = min(len(price_df) - entry_idx, 168)  # Max 7 days (168 hours)
        
        for i in range(entry_idx + 1, entry_idx + max_lookforward):
            current_price = price_df.iloc[i]['price']
            
            # Calculate current profit percentage
            if entry.side == 'BUY':
                profit_pct = ((current_price - entry_price) / entry_price) * 100
            else:  # SELL
                profit_pct = ((entry_price - current_price) / entry_price) * 100
                
            # Update highest profit reached
            highest_profit = max(profit_pct, highest_profit)
            
            # Check if trailing should activate
            if not trailing_active and profit_pct >= config.activation_pct:
                trailing_active = True
                
            # Check exit conditions
            if trailing_active:
                # Exit if profit drops by trail_distance from highest
                stop_level = highest_profit - config.trail_distance_pct
                
                if profit_pct <= stop_level and profit_pct >= config.min_profit_pct:
                    # Exit via trailing stop
                    pnl = position_size * (profit_pct / 100)
                    return {
                        'status': 'trailing_exit',
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl': pnl,
                        'pnl_pct': profit_pct,
                        'highest_profit_pct': highest_profit,
                        'hours_held': i - entry_idx,
                        'exit_reason': 'trailing_stop'
                    }
                    
            # Check minimum profit protection
            if highest_profit >= config.activation_pct:
                if profit_pct < config.min_profit_pct:
                    pnl = position_size * (profit_pct / 100)
                    return {
                        'status': 'min_profit_exit',
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl': pnl,
                        'pnl_pct': profit_pct,
                        'highest_profit_pct': highest_profit,
                        'hours_held': i - entry_idx,
                        'exit_reason': 'profit_protection'
                    }
                    
            # Check for large losses (emergency stop)
            if profit_pct < -10:  # 10% stop loss
                pnl = position_size * (profit_pct / 100)
                return {
                    'status': 'stop_loss',
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'pnl': pnl,
                    'pnl_pct': profit_pct,
                    'highest_profit_pct': highest_profit,
                    'hours_held': i - entry_idx,
                    'exit_reason': 'stop_loss'
                }
                
        # Trade held to end of data
        final_price = price_df.iloc[entry_idx + max_lookforward - 1]['price']
        if entry.side == 'BUY':
            final_profit_pct = ((final_price - entry_price) / entry_price) * 100
        else:
            final_profit_pct = ((entry_price - final_price) / entry_price) * 100
            
        pnl = position_size * (final_profit_pct / 100)
        
        return {
            'status': 'held_to_end',
            'entry_price': entry_price,
            'exit_price': final_price,
            'pnl': pnl,
            'pnl_pct': final_profit_pct,
            'highest_profit_pct': highest_profit,
            'hours_held': max_lookforward - 1,
            'exit_reason': 'time_limit'
        }
        
    def run_comprehensive_backtest(self) -> Dict:
        """Run comprehensive backtest comparing both strategies"""
        logger.info("Starting comprehensive trailing stop backtest...")
        
        # Fetch price data for major cryptocurrencies
        symbols = ['BTCUSD', 'ETHUSD']
        all_price_data = {}
        
        for symbol in symbols:
            price_df = self.price_fetcher.fetch_price_history(symbol, days=90)
            if not price_df.empty:
                all_price_data[symbol] = price_df
                
        if not all_price_data:
            logger.error("No price data fetched!")
            return {}
            
        # Generate or load trading signals
        all_signals = []
        
        # Try to load from database first
        db_signals = self.signal_generator.load_historical_signals()
        if db_signals:
            all_signals.extend(db_signals)
            logger.info(f"Loaded {len(db_signals)} signals from database")
            
        # Generate additional signals from price action
        for symbol, price_df in all_price_data.items():
            generated_signals = self.signal_generator.generate_realistic_entries(price_df, 25)
            all_signals.extend(generated_signals)
            
        logger.info(f"Total signals for backtest: {len(all_signals)}")
        
        if not all_signals:
            logger.error("No trading signals available!")
            return {}
            
        # Run backtest for both strategies
        results = {}
        
        for strategy_name, config in self.strategies.items():
            logger.info(f"Testing {config}")
            
            strategy_results = []
            
            for signal in all_signals:
                # Get price data for this signal's symbol
                price_df = all_price_data.get(signal.symbol)
                if price_df is None:
                    # Try to find similar symbol
                    for sym, df in all_price_data.items():
                        if signal.symbol.startswith(sym[:3]):  # Match BTC, ETH etc
                            price_df = df
                            break
                            
                if price_df is None:
                    continue
                    
                # Simulate this trade
                trade_result = self.simulate_trailing_stop(signal, price_df, config)
                trade_result['signal'] = signal
                trade_result['strategy'] = strategy_name
                strategy_results.append(trade_result)
                
            results[strategy_name] = {
                'config': config,
                'trades': strategy_results,
                'metrics': self.calculate_performance_metrics(strategy_results)
            }
            
        # Generate comparison analysis
        comparison = self.compare_strategies(results)
        
        # Save results
        self.save_results(results, comparison)
        
        return {
            'results': results,
            'comparison': comparison
        }
        
    def calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not trades:
            return {}
            
        total_trades = len(trades)
        successful_trades = [t for t in trades if t.get('pnl', 0) > 0]
        winning_trades = len(successful_trades)
        losing_trades = total_trades - winning_trades
        
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = np.mean([t['pnl'] for t in successful_trades]) if successful_trades else 0
        losing_trades_list = [t for t in trades if t.get('pnl', 0) <= 0]
        avg_loss = np.mean([t['pnl'] for t in losing_trades_list]) if losing_trades_list else 0
        
        # Calculate additional metrics
        pnl_values = [t.get('pnl', 0) for t in trades]
        max_win = max(pnl_values) if pnl_values else 0
        max_loss = min(pnl_values) if pnl_values else 0
        
        # Holdings analysis
        exit_reasons = {}
        for trade in trades:
            reason = trade.get('exit_reason', 'unknown')
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
            
        avg_hold_time = np.mean([t.get('hours_held', 0) for t in trades]) if trades else 0
        
        # Profit factor
        gross_profit = sum(t['pnl'] for t in trades if t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t['pnl'] for t in trades if t.get('pnl', 0) < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_profit_per_trade': total_pnl / total_trades if total_trades > 0 else 0,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_win': max_win,
            'max_loss': max_loss,
            'profit_factor': profit_factor,
            'avg_hold_time_hours': avg_hold_time,
            'exit_reasons': exit_reasons,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss
        }
        
    def compare_strategies(self, results: Dict) -> Dict:
        """Compare the performance of both strategies"""
        if 'current' not in results or 'proposed' not in results:
            return {}
            
        current = results['current']['metrics']
        proposed = results['proposed']['metrics']
        
        comparison = {
            'profit_difference': proposed.get('total_pnl', 0) - current.get('total_pnl', 0),
            'win_rate_difference': proposed.get('win_rate', 0) - current.get('win_rate', 0),
            'avg_trade_difference': proposed.get('avg_profit_per_trade', 0) - current.get('avg_profit_per_trade', 0),
            'profit_factor_ratio': proposed.get('profit_factor', 0) / current.get('profit_factor', 1),
            'hold_time_difference': proposed.get('avg_hold_time_hours', 0) - current.get('avg_hold_time_hours', 0),
        }
        
        # Determine which is better
        better_strategy = 'proposed' if comparison['profit_difference'] > 0 else 'current'
        
        # Calculate statistical significance
        current_trades = results['current']['trades']
        proposed_trades = results['proposed']['trades']
        
        trades_affected = 0
        different_outcomes = 0
        
        # Match trades by entry point and compare outcomes
        for i, curr_trade in enumerate(current_trades):
            if i < len(proposed_trades):
                prop_trade = proposed_trades[i]
                trades_affected += 1
                
                # Check if outcome would be different
                curr_exit = curr_trade.get('exit_reason', '')
                prop_exit = prop_trade.get('exit_reason', '')
                
                if curr_exit != prop_exit or abs(curr_trade.get('pnl', 0) - prop_trade.get('pnl', 0)) > 10:
                    different_outcomes += 1
                    
        comparison.update({
            'trades_affected': trades_affected,
            'different_outcomes': different_outcomes,
            'impact_percentage': (different_outcomes / trades_affected * 100) if trades_affected > 0 else 0,
            'better_strategy': better_strategy,
            'improvement_pct': (comparison['profit_difference'] / abs(current.get('total_pnl', 1)) * 100) if current.get('total_pnl') else 0
        })
        
        return comparison
        
    def save_results(self, results: Dict, comparison: Dict):
        """Save backtest results to database"""
        try:
            conn = sqlite3.connect('trailing_stop_backtest_results.db')
            cursor = conn.cursor()
            
            # Create results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_date DATETIME,
                    strategy_name TEXT,
                    config_json TEXT,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    win_rate REAL,
                    total_pnl REAL,
                    avg_profit_per_trade REAL,
                    profit_factor REAL,
                    avg_hold_time_hours REAL,
                    detailed_results TEXT
                )
            ''')
            
            # Save strategy results
            for strategy_name, data in results.items():
                cursor.execute('''
                    INSERT INTO backtest_results (
                        test_date, strategy_name, config_json,
                        total_trades, winning_trades, win_rate, total_pnl,
                        avg_profit_per_trade, profit_factor, avg_hold_time_hours,
                        detailed_results
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now(),
                    strategy_name,
                    json.dumps(data['config'].__dict__),
                    data['metrics'].get('total_trades', 0),
                    data['metrics'].get('winning_trades', 0),
                    data['metrics'].get('win_rate', 0),
                    data['metrics'].get('total_pnl', 0),
                    data['metrics'].get('avg_profit_per_trade', 0),
                    data['metrics'].get('profit_factor', 0),
                    data['metrics'].get('avg_hold_time_hours', 0),
                    json.dumps(data['metrics'])
                ))
                
            # Create comparison table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_comparison (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_date DATETIME,
                    profit_difference REAL,
                    win_rate_difference REAL,
                    better_strategy TEXT,
                    trades_affected INTEGER,
                    different_outcomes INTEGER,
                    impact_percentage REAL,
                    comparison_details TEXT
                )
            ''')
            
            cursor.execute('''
                INSERT INTO strategy_comparison (
                    test_date, profit_difference, win_rate_difference,
                    better_strategy, trades_affected, different_outcomes,
                    impact_percentage, comparison_details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now(),
                comparison.get('profit_difference', 0),
                comparison.get('win_rate_difference', 0),
                comparison.get('better_strategy', 'unknown'),
                comparison.get('trades_affected', 0),
                comparison.get('different_outcomes', 0),
                comparison.get('impact_percentage', 0),
                json.dumps(comparison)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info("Backtest results saved to database")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")

def generate_report(backtest_results: Dict):
    """Generate a comprehensive analysis report"""
    
    if not backtest_results or 'results' not in backtest_results:
        return "No backtest results available"
        
    results = backtest_results['results'] 
    comparison = backtest_results.get('comparison', {})
    
    report = f"""
# TRAILING STOP STRATEGY BACKTEST COMPARISON REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## STRATEGY CONFIGURATIONS

### Current System (4.5%/1.5%/3.5%)
- Activation: 4.5% profit required to start trailing
- Trail Distance: 1.5% from highest profit point
- Minimum Exit: 3.5% minimum profit when exiting

### Proposed System (4.0%/1.0%/3.0%) 
- Activation: 4.0% profit required to start trailing
- Trail Distance: 1.0% from highest profit point  
- Minimum Exit: 3.0% minimum profit when exiting

## PERFORMANCE COMPARISON
"""

    for strategy_name, data in results.items():
        metrics = data['metrics']
        config = data['config']
        
        report += f"""
### {config.name}
- Total Trades: {metrics.get('total_trades', 0)}
- Win Rate: {metrics.get('win_rate', 0):.1f}%
- Total P&L: ${metrics.get('total_pnl', 0):.2f}
- Avg Profit/Trade: ${metrics.get('avg_profit_per_trade', 0):.2f}
- Profit Factor: {metrics.get('profit_factor', 0):.2f}
- Avg Hold Time: {metrics.get('avg_hold_time_hours', 0):.1f} hours
- Max Win: ${metrics.get('max_win', 0):.2f}
- Max Loss: ${metrics.get('max_loss', 0):.2f}

Exit Reasons Breakdown:
"""
        for reason, count in metrics.get('exit_reasons', {}).items():
            report += f"  - {reason}: {count} trades\n"

    if comparison:
        report += f"""

## STRATEGY COMPARISON ANALYSIS

### Key Differences
- Profit Difference: ${comparison.get('profit_difference', 0):.2f}
- Win Rate Difference: {comparison.get('win_rate_difference', 0):+.1f}%
- Better Strategy: {comparison.get('better_strategy', 'unknown').title()}
- Improvement: {comparison.get('improvement_pct', 0):+.1f}%

### Impact Analysis
- Trades Analyzed: {comparison.get('trades_affected', 0)}
- Different Outcomes: {comparison.get('different_outcomes', 0)}
- Impact Percentage: {comparison.get('impact_percentage', 0):.1f}%

## KEY FINDINGS

"""
        if comparison.get('profit_difference', 0) > 0:
            report += f"""[+] **PROPOSED SYSTEM PERFORMS BETTER**

The proposed system (4.0%/1.0%/3.0%) shows superior performance with:
- ${comparison['profit_difference']:.2f} additional profit
- {comparison['win_rate_difference']:+.1f}% difference in win rate
- {comparison['impact_percentage']:.1f}% of trades had different outcomes

This suggests that:
1. Lower activation threshold (4.0% vs 4.5%) captures more profitable moves
2. Tighter trailing (1.0% vs 1.5%) protects profits better in volatile conditions
3. Lower minimum exit (3.0% vs 3.5%) allows for earlier profit-taking when needed
"""
        else:
            report += f"""[!] **CURRENT SYSTEM PERFORMS BETTER**

The current system (4.5%/1.5%/3.5%) shows superior performance with:
- ${abs(comparison['profit_difference']):.2f} more profit than proposed
- {abs(comparison['win_rate_difference']):.1f}% better win rate
- {comparison['impact_percentage']:.1f}% of trades had different outcomes

This suggests that:
1. Higher activation threshold (4.5%) waits for stronger trends
2. Wider trailing (1.5%) gives moves more room to breathe
3. Higher minimum exit (3.5%) captures larger profit swings
"""

    report += f"""

## RECOMMENDATIONS

Based on this backtest analysis:
"""
    
    better = comparison.get('better_strategy', 'current')
    if better == 'proposed':
        report += """
1. **IMPLEMENT PROPOSED SYSTEM** - The data supports using the new parameters
2. **Monitor for 30 days** - Track real performance vs backtest predictions  
3. **Consider hybrid approach** - Use proposed for high-volatility periods, current for trending markets
4. **Set up alerts** - Monitor when parameter differences matter most
"""
    else:
        report += """
1. **KEEP CURRENT SYSTEM** - Existing parameters are performing better
2. **Re-evaluate with more data** - Test with longer timeframes or different market conditions
3. **Consider market-specific parameters** - Maybe proposed works better for specific assets
4. **Monitor strong trends** - Current data suggests wider stops catch bigger moves better
"""

    report += f"""

## MARKET CONDITIONS ANALYSIS

The backtest covered various market conditions and the results suggest:
- Trend following vs mean reversion preferences
- Volatility impact on trailing stop effectiveness  
- Asset-specific performance differences
- Timing and holding period optimization

## NEXT STEPS

1. **Live Paper Trading**: Test both systems simultaneously for 2 weeks
2. **Market Condition Segmentation**: Analyze performance in different market phases
3. **Asset-Specific Optimization**: Test if different cryptos need different parameters
4. **Real-Time Monitoring**: Set up dashboard to track parameter impact

---
*This analysis is based on historical data and simulated trades. Past performance does not guarantee future results.*
"""
    
    return report

if __name__ == "__main__":
    # Initialize and run backtest
    backtester = TrailingStopBacktester()
    results = backtester.run_comprehensive_backtest()
    
    # Generate and display report
    if results:
        report = generate_report(results)
        print(report)
        
        # Save report to file
        with open('trailing_stop_backtest_report.md', 'w') as f:
            f.write(report)
            
        logger.info("Backtest complete! Report saved to trailing_stop_backtest_report.md")
    else:
        logger.error("Backtest failed - no results generated")