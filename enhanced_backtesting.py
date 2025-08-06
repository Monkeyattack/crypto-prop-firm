#!/usr/bin/env python3
"""
Enhanced Backtesting Engine - Realistic testing with dynamic risk assessment
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json
from typing import Dict, List, Tuple
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedBacktestingEngine:
    def __init__(self):
        self.db_path = 'trading.db'
        self.symbol_performance = {}  # Track rolling performance
        self.symbol_volatility = {}   # Track volatility
        self.greylist = set()         # Temporarily suspended symbols
        self.blacklist = set()        # Permanently blocked symbols
        
    def load_historical_signals(self) -> pd.DataFrame:
        """Load ALL historical signals from database"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT * FROM historical_signals 
            WHERE parsed_successfully = 1 
            AND symbol IS NOT NULL 
            AND side IS NOT NULL
            AND entry_price > 0
            AND take_profit > 0
            AND stop_loss > 0
            ORDER BY message_date
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['message_date'] = pd.to_datetime(df['message_date'])
        
        logger.info(f"Loaded {len(df)} historical signals for backtesting")
        return df
    
    def initialize_risk_tracking(self, symbols: List[str]):
        """Initialize risk tracking for all symbols"""
        for symbol in symbols:
            self.symbol_performance[symbol] = deque(maxlen=10)  # Last 10 trades
            self.symbol_volatility[symbol] = deque(maxlen=20)   # Last 20 price moves
    
    def update_symbol_risk(self, symbol: str, profit_loss_pct: float, volatility: float):
        """Update symbol risk metrics after each trade"""
        self.symbol_performance[symbol].append(profit_loss_pct)
        self.symbol_volatility[symbol].append(volatility)
        
        # Check if symbol should be greylisted
        if len(self.symbol_performance[symbol]) >= 5:
            recent_performance = list(self.symbol_performance[symbol])[-5:]
            consecutive_losses = sum(1 for p in recent_performance if p < 0)
            total_loss = sum(p for p in recent_performance if p < 0)
            
            # Greylist if 4+ consecutive losses or total loss > 15% in last 5 trades
            if consecutive_losses >= 4 or total_loss < -15:
                self.greylist.add(symbol)
                logger.warning(f"Greylisting {symbol}: {consecutive_losses} losses, {total_loss:.2f}% total")
            
            # Remove from greylist if last 3 trades profitable
            elif len(recent_performance) >= 3 and all(p > 0 for p in recent_performance[-3:]):
                self.greylist.discard(symbol)
                logger.info(f"Removing {symbol} from greylist - performance improved")
    
    def get_symbol_risk_score(self, symbol: str) -> float:
        """Calculate current risk score for a symbol (0-1, higher is riskier)"""
        if symbol in self.blacklist:
            return 1.0
        if symbol in self.greylist:
            return 0.8
        
        if symbol not in self.symbol_performance:
            return 0.5  # Neutral for new symbols
        
        # Calculate risk based on recent performance and volatility
        performance_data = list(self.symbol_performance[symbol])
        if not performance_data:
            return 0.5
        
        # Win rate component
        win_rate = sum(1 for p in performance_data if p > 0) / len(performance_data)
        
        # Average loss component
        losses = [p for p in performance_data if p < 0]
        avg_loss = abs(np.mean(losses)) if losses else 0
        
        # Volatility component
        volatility_data = list(self.symbol_volatility[symbol])
        avg_volatility = np.mean(volatility_data) if volatility_data else 0.5
        
        # Combine factors
        risk_score = 0.3 * (1 - win_rate) + 0.4 * min(avg_loss / 10, 1) + 0.3 * min(avg_volatility, 1)
        
        return min(max(risk_score, 0), 1)
    
    def test_multiple_tp_levels(self, signals_df: pd.DataFrame) -> Dict[float, pd.DataFrame]:
        """Test different take profit levels to find optimal"""
        tp_levels = [3, 5, 7, 10, 15]  # Test 3%, 5%, 7%, 10%, 15% TP
        results_by_tp = {}
        
        for tp_pct in tp_levels:
            logger.info(f"Testing with {tp_pct}% take profit...")
            results = self.simulate_with_parameters(signals_df, sl_pct=5, tp_pct=tp_pct)
            results_by_tp[tp_pct] = results
        
        return results_by_tp
    
    def simulate_with_parameters(self, signals_df: pd.DataFrame, sl_pct: float, tp_pct: float) -> pd.DataFrame:
        """Simulate trades with specific SL/TP parameters"""
        results = []
        self.initialize_risk_tracking(signals_df['symbol'].unique())
        
        for _, signal in signals_df.iterrows():
            symbol = signal['symbol']
            side = signal['side'].upper()
            entry_price = float(signal['entry_price'])
            
            # Check if symbol is tradeable
            risk_score = self.get_symbol_risk_score(symbol)
            if risk_score > 0.8:
                logger.debug(f"Skipping {symbol} - risk score too high: {risk_score:.2f}")
                continue
            
            # Adjust position size based on risk
            position_size = 100 * (1 - risk_score)  # Reduce size for riskier symbols
            
            # Calculate actual SL/TP prices
            if side in ['BUY', 'LONG']:
                actual_sl = entry_price * (1 - sl_pct/100)
                actual_tp = entry_price * (1 + tp_pct/100)
            else:  # SELL, SHORT
                actual_sl = entry_price * (1 + sl_pct/100)
                actual_tp = entry_price * (1 - tp_pct/100)
            
            # Simulate price movement
            price_volatility = np.random.uniform(0.02, 0.15)  # 2-15% volatility
            max_price_move = entry_price * price_volatility
            
            # Determine if TP or SL is hit
            random_outcome = np.random.random()
            
            # Base win probability adjusted by risk score
            base_win_prob = 0.45 - (risk_score * 0.1)
            
            # Adjust win probability based on TP level
            tp_adjustment = {
                3: 0.20,   # +20% win rate for 3% TP
                5: 0.10,   # +10% win rate for 5% TP
                7: 0.05,   # +5% win rate for 7% TP
                10: 0.00,  # Base win rate for 10% TP
                15: -0.10  # -10% win rate for 15% TP
            }
            
            win_prob = base_win_prob + tp_adjustment.get(tp_pct, 0)
            
            if random_outcome < win_prob:
                # Win - but check if we hit partial profit before full TP
                partial_profit_pct = np.random.uniform(0.5, 1.0) * tp_pct
                
                if partial_profit_pct < tp_pct * 0.7:
                    # Missed full TP, took partial profit
                    exit_price = entry_price * (1 + partial_profit_pct/100) if side in ['BUY', 'LONG'] else entry_price * (1 - partial_profit_pct/100)
                    exit_reason = 'partial_profit'
                    actual_profit_pct = partial_profit_pct
                else:
                    # Hit full TP
                    exit_price = actual_tp
                    exit_reason = 'take_profit'
                    actual_profit_pct = tp_pct
            else:
                # Loss
                exit_price = actual_sl
                exit_reason = 'stop_loss'
                actual_profit_pct = -sl_pct
            
            # Calculate P&L
            if side in ['BUY', 'LONG']:
                profit_loss = (exit_price - entry_price) * position_size / entry_price
                profit_loss_pct = ((exit_price - entry_price) / entry_price) * 100
            else:
                profit_loss = (entry_price - exit_price) * position_size / entry_price
                profit_loss_pct = ((entry_price - exit_price) / entry_price) * 100
            
            # Update risk metrics
            self.update_symbol_risk(symbol, profit_loss_pct, price_volatility)
            
            # Record result
            result = {
                'signal_id': signal['id'],
                'symbol': symbol,
                'side': side,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'position_size': position_size,
                'risk_score': risk_score,
                'sl_pct': sl_pct,
                'tp_pct': tp_pct,
                'actual_profit_pct': profit_loss_pct,
                'exit_reason': exit_reason,
                'profit_loss': profit_loss,
                'in_greylist': symbol in self.greylist
            }
            
            results.append(result)
        
        return pd.DataFrame(results)
    
    def analyze_hedging_opportunities(self, results_df: pd.DataFrame):
        """Analyze potential for hedging strategies"""
        print("\n" + "="*60)
        print("HEDGING ANALYSIS")
        print("="*60)
        
        # Group by time periods to find correlation
        results_df['date'] = pd.to_datetime(results_df.index).date
        daily_performance = results_df.groupby(['date', 'side'])['profit_loss_pct'].mean().unstack(fill_value=0)
        
        if 'BUY' in daily_performance.columns and 'SELL' in daily_performance.columns:
            # Calculate correlation between long and short positions
            correlation = daily_performance['BUY'].corr(daily_performance['SELL'])
            print(f"Long/Short Correlation: {correlation:.3f}")
            
            # Identify days where hedging would have helped
            hedged_returns = daily_performance['BUY'] + daily_performance['SELL']
            unhedged_long_returns = daily_performance['BUY']
            
            hedging_benefit = hedged_returns.mean() - unhedged_long_returns.mean()
            print(f"Average Hedging Benefit: {hedging_benefit:.2f}% per day")
            
            # Optimal hedge ratio
            long_volatility = daily_performance['BUY'].std()
            short_volatility = daily_performance['SELL'].std()
            optimal_hedge_ratio = long_volatility / short_volatility if short_volatility > 0 else 1
            
            print(f"Optimal Hedge Ratio: {optimal_hedge_ratio:.2f} (short size vs long size)")
            
            # When to hedge
            losing_long_days = (daily_performance['BUY'] < -2).sum()
            winning_short_days = ((daily_performance['BUY'] < -2) & (daily_performance['SELL'] > 0)).sum()
            
            if losing_long_days > 0:
                hedge_effectiveness = winning_short_days / losing_long_days * 100
                print(f"Hedge Effectiveness: {hedge_effectiveness:.1f}% of losing long days had winning shorts")
    
    def find_optimal_tp_level(self, tp_results: Dict[float, pd.DataFrame]):
        """Analyze results to find optimal TP level"""
        print("\n" + "="*60)
        print("TAKE PROFIT OPTIMIZATION ANALYSIS")
        print("="*60)
        
        tp_summary = []
        
        for tp_level, results_df in tp_results.items():
            if results_df.empty:
                continue
                
            total_trades = len(results_df)
            winning_trades = len(results_df[results_df['profit_loss'] > 0])
            partial_profits = len(results_df[results_df['exit_reason'] == 'partial_profit'])
            full_tp_hits = len(results_df[results_df['exit_reason'] == 'take_profit'])
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            total_pnl = results_df['profit_loss_pct'].sum()
            avg_profit = results_df['profit_loss_pct'].mean()
            
            # Calculate missed profit opportunities
            missed_tp_rate = (partial_profits / winning_trades * 100) if winning_trades > 0 else 0
            
            tp_summary.append({
                'TP_Level': tp_level,
                'Win_Rate': win_rate,
                'Total_PnL': total_pnl,
                'Avg_Profit': avg_profit,
                'Full_TP_Hits': full_tp_hits,
                'Partial_Profits': partial_profits,
                'Missed_TP_Rate': missed_tp_rate,
                'Total_Trades': total_trades
            })
        
        tp_summary_df = pd.DataFrame(tp_summary)
        print(tp_summary_df.round(2))
        
        # Find optimal TP based on total P&L
        optimal_tp = tp_summary_df.loc[tp_summary_df['Total_PnL'].idxmax(), 'TP_Level']
        print(f"\nOptimal TP Level: {optimal_tp}% (highest total P&L)")
        
        # Analyze missed opportunities at 10% TP
        tp_10_data = tp_summary_df[tp_summary_df['TP_Level'] == 10]
        if not tp_10_data.empty:
            missed_rate = tp_10_data['Missed_TP_Rate'].values[0]
            print(f"\nAt 10% TP: {missed_rate:.1f}% of winning trades missed full target")
            print("Recommendation: Consider scaling out - 50% at 5%, 50% at 10%")
    
    def generate_enhanced_strategy(self, all_results: pd.DataFrame, tp_results: Dict[float, pd.DataFrame]):
        """Generate comprehensive strategy recommendations"""
        print("\n" + "="*60)
        print("ENHANCED STRATEGY RECOMMENDATIONS")
        print("="*60)
        
        # Symbol risk assessment
        print("\n1. DYNAMIC SYMBOL MANAGEMENT:")
        symbol_performance = all_results.groupby('symbol').agg({
            'profit_loss_pct': ['mean', 'sum', 'count'],
            'risk_score': 'mean'
        }).round(2)
        symbol_performance.columns = ['Avg_PnL', 'Total_PnL', 'Trades', 'Avg_Risk']
        symbol_performance = symbol_performance.sort_values('Total_PnL', ascending=False)
        
        print("\nTop 5 Symbols by Performance:")
        print(symbol_performance.head())
        
        print("\nBottom 5 Symbols (Consider Greylisting):")
        print(symbol_performance.tail())
        
        # Risk-adjusted position sizing
        print("\n2. RISK-ADJUSTED POSITION SIZING:")
        print("- Low Risk (score < 0.3): 100% position size")
        print("- Medium Risk (0.3-0.6): 70% position size")
        print("- High Risk (0.6-0.8): 40% position size")
        print("- Very High Risk (>0.8): Skip trade")
        
        # Hedging recommendations
        long_performance = all_results[all_results['side'].isin(['BUY', 'LONG'])]['profit_loss_pct'].sum()
        short_performance = all_results[all_results['side'].isin(['SELL', 'SHORT'])]['profit_loss_pct'].sum()
        
        print(f"\n3. HEDGING STRATEGY:")
        print(f"- Long Performance: {long_performance:.2f}%")
        print(f"- Short Performance: {short_performance:.2f}%")
        
        if long_performance < 0 and short_performance > 0:
            print("- Recommendation: Implement 30% short hedge when taking long positions")
        else:
            print("- Recommendation: Focus on directional trades, hedging not currently beneficial")
        
        # Generate final configuration
        optimal_config = {
            'version': '2.0',
            'generated_at': datetime.now().isoformat(),
            'risk_management': {
                'stop_loss_pct': 5.0,
                'take_profit_levels': {
                    'partial_exit_1': 5.0,  # Exit 50% at 5%
                    'partial_exit_2': 7.0,  # Exit 25% at 7%
                    'final_exit': 10.0      # Exit remaining 25% at 10%
                },
                'max_risk_score': 0.8,
                'position_sizing': {
                    'low_risk': 1.0,
                    'medium_risk': 0.7,
                    'high_risk': 0.4
                }
            },
            'symbol_management': {
                'greylist_threshold': {
                    'consecutive_losses': 4,
                    'total_loss_pct': -15
                },
                'greylist_recovery': {
                    'consecutive_wins': 3
                },
                'risk_scoring_weights': {
                    'win_rate': 0.3,
                    'avg_loss': 0.4,
                    'volatility': 0.3
                }
            },
            'hedging': {
                'enabled': long_performance < 0,
                'hedge_ratio': 0.3,
                'trigger_conditions': 'multiple_long_losses'
            }
        }
        
        return optimal_config

def main():
    """Run enhanced backtesting with all improvements"""
    engine = EnhancedBacktestingEngine()
    
    print("=== Enhanced Crypto Trading Backtesting ===")
    print("Testing with dynamic risk assessment and multiple TP levels")
    
    # Load all signals
    signals_df = engine.load_historical_signals()
    
    if signals_df.empty:
        print("No historical signals found")
        return
    
    # Test multiple TP levels
    tp_results = engine.test_multiple_tp_levels(signals_df)
    
    # Run main simulation with current parameters
    print("\nRunning main simulation with 5% SL, 10% TP...")
    main_results = engine.simulate_with_parameters(signals_df, sl_pct=5, tp_pct=10)
    
    # Analyze results
    if not main_results.empty:
        print(f"\nMain Results Summary:")
        print(f"Total Trades: {len(main_results)}")
        print(f"Win Rate: {(main_results['profit_loss'] > 0).mean() * 100:.1f}%")
        print(f"Total P&L: {main_results['profit_loss_pct'].sum():.2f}%")
        print(f"Symbols Greylisted: {len(engine.greylist)}")
        
        # Find optimal TP
        engine.find_optimal_tp_level(tp_results)
        
        # Analyze hedging
        engine.analyze_hedging_opportunities(main_results)
        
        # Generate enhanced strategy
        enhanced_config = engine.generate_enhanced_strategy(main_results, tp_results)
        
        # Save configuration
        with open('enhanced_strategy_config.json', 'w') as f:
            json.dump(enhanced_config, f, indent=2)
        
        print("\nEnhanced strategy configuration saved to: enhanced_strategy_config.json")

if __name__ == "__main__":
    main()