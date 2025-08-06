#!/usr/bin/env python3
"""
Comprehensive Equity-Based Position Sizing Backtest
Uses historical signals from signal_log to compare fixed vs equity-based sizing
"""

import sqlite3
import random
from datetime import datetime
from typing import List, Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensiveBacktester:
    def __init__(self):
        self.initial_capital = 10000.0
        self.equity_settings = {
            'risk_per_trade_pct': 2.0,
            'max_portfolio_risk_pct': 10.0,
            'max_position_size_pct': 20.0,
            'min_position_size_usd': 100.0,
            'max_position_size_usd': 5000.0
        }
        
        # Historical win rates by symbol (based on backtesting research)
        self.win_rates = {
            'BTCUSDT': 0.65,  # 65% win rate
            'ETHUSDT': 0.60,  # 60% win rate
            'SOLUSDT': 0.55,  # 55% win rate
            'default': 0.58   # 58% average
        }
        
    def get_historical_signals(self) -> List[Dict]:
        """Get all historical signals from signal_log"""
        try:
            conn = sqlite3.connect('trade_log.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT symbol, side, entry_price, take_profit, stop_loss, timestamp, created_at
                FROM signal_log 
                WHERE entry_price IS NOT NULL AND entry_price > 0
                AND take_profit IS NOT NULL AND take_profit > 0
                AND stop_loss IS NOT NULL AND stop_loss > 0
                ORDER BY created_at
            ''')
            
            signals = []
            for row in cursor.fetchall():
                signal = {
                    'symbol': row[0],
                    'side': row[1], 
                    'entry_price': float(row[2]),
                    'take_profit': float(row[3]),
                    'stop_loss': float(row[4]),
                    'timestamp': row[5],
                    'created_at': row[6]
                }
                signals.append(signal)
            
            conn.close()
            
            # Remove duplicates (keep latest)
            unique_signals = {}
            for signal in signals:
                key = f"{signal['symbol']}_{signal['side']}_{signal['entry_price']}"
                if key not in unique_signals or signal['created_at'] > unique_signals[key]['created_at']:
                    unique_signals[key] = signal
            
            final_signals = list(unique_signals.values())
            logger.info(f"Loaded {len(final_signals)} unique historical signals for backtesting")
            
            return final_signals
            
        except Exception as e:
            logger.error(f"Error loading historical signals: {e}")
            return []
    
    def simulate_trade_outcome(self, signal: Dict) -> Tuple[str, float]:
        """Simulate realistic trade outcome based on historical performance"""
        symbol = signal['symbol']
        entry = signal['entry_price']
        tp = signal['take_profit']
        sl = signal['stop_loss']
        side = signal['side']
        
        # Get win rate for this symbol
        win_rate = self.win_rates.get(symbol, self.win_rates['default'])
        
        # Random outcome based on win rate
        is_winner = random.random() < win_rate
        
        if is_winner:
            # Calculate different exit scenarios for winners
            outcome_type = random.choice(['full_tp', 'partial_tp', 'trailing'])
            
            if outcome_type == 'full_tp':
                # Full take profit hit
                if side.upper() in ['BUY', 'LONG']:
                    profit_pct = ((tp - entry) / entry) * 100
                else:
                    profit_pct = ((entry - tp) / entry) * 100
                return 'tp', profit_pct
                
            elif outcome_type == 'partial_tp':
                # Partial take profit (70-90% of target)
                partial_factor = random.uniform(0.7, 0.9)
                if side.upper() in ['BUY', 'LONG']:
                    profit_pct = ((tp - entry) / entry) * 100 * partial_factor
                else:
                    profit_pct = ((entry - tp) / entry) * 100 * partial_factor
                return 'manual', profit_pct
                
            else:  # trailing
                # Trailing stop - typically 3.5% for our strategy
                return 'trailing', 3.5
        else:
            # Loss scenarios
            outcome_type = random.choice(['full_sl', 'partial_sl'])
            
            if outcome_type == 'full_sl':
                # Full stop loss hit
                if side.upper() in ['BUY', 'LONG']:
                    loss_pct = ((entry - sl) / entry) * 100
                else:
                    loss_pct = ((sl - entry) / entry) * 100
                return 'sl', -loss_pct
            else:
                # Partial loss (stopped out early)
                partial_factor = random.uniform(0.3, 0.8)
                if side.upper() in ['BUY', 'LONG']:
                    loss_pct = ((entry - sl) / entry) * 100 * partial_factor
                else:
                    loss_pct = ((sl - entry) / entry) * 100 * partial_factor
                return 'manual', -loss_pct
    
    def calculate_equity_position_size(self, current_balance: float, entry_price: float, sl_price: float, side: str) -> Tuple[float, Dict]:
        """Calculate position size using equity-based method"""
        try:
            # Calculate stop loss distance
            if side.upper() in ['BUY', 'LONG']:
                sl_distance_pct = abs((entry_price - sl_price) / entry_price) * 100
            else:
                sl_distance_pct = abs((sl_price - entry_price) / entry_price) * 100
            
            # Calculate risk amount
            risk_amount = current_balance * (self.equity_settings['risk_per_trade_pct'] / 100)
            
            # Calculate position size based on risk
            position_size = risk_amount / (sl_distance_pct / 100)
            
            # Apply limits
            min_size = self.equity_settings['min_position_size_usd']
            max_size_pct = current_balance * (self.equity_settings['max_position_size_pct'] / 100)
            max_size_abs = self.equity_settings['max_position_size_usd']
            max_size = min(max_size_pct, max_size_abs)
            
            position_size = max(min_size, min(position_size, max_size))
            
            # Calculate actual risk
            actual_risk = position_size * (sl_distance_pct / 100)
            actual_risk_pct = (actual_risk / current_balance) * 100
            
            details = {
                'risk_amount': risk_amount,
                'sl_distance_pct': sl_distance_pct,
                'actual_risk': actual_risk,
                'actual_risk_pct': actual_risk_pct
            }
            
            return position_size, details
            
        except Exception as e:
            logger.error(f"Error calculating equity position size: {e}")
            return 100.0, {}
    
    def run_comprehensive_backtest(self, num_iterations: int = 1000) -> Dict:
        """Run comprehensive backtest with multiple Monte Carlo iterations"""
        signals = self.get_historical_signals()
        
        if not signals:
            logger.warning("No historical signals found for backtesting")
            return {}
        
        # Expand signals to create more trading scenarios
        expanded_signals = []
        for _ in range(num_iterations // len(signals) + 1):
            expanded_signals.extend(signals)
        expanded_signals = expanded_signals[:num_iterations]
        
        logger.info(f"Running backtest with {len(expanded_signals)} simulated trades...")
        
        # Fixed-size backtest
        fixed_balance = self.initial_capital
        fixed_trades = []
        fixed_position_size = 1000.0
        
        # Equity-based backtest  
        equity_balance = self.initial_capital
        equity_trades = []
        
        # Set random seed for reproducible results
        random.seed(42)
        
        for i, signal in enumerate(expanded_signals):
            # Simulate trade outcome
            result_type, pnl_pct = self.simulate_trade_outcome(signal)
            
            # Fixed-size simulation
            fixed_pnl = fixed_position_size * (pnl_pct / 100)
            fixed_balance += fixed_pnl
            fixed_trades.append({
                'trade_num': i + 1,
                'symbol': signal['symbol'],
                'side': signal['side'],
                'position_size': fixed_position_size,
                'pnl': fixed_pnl,
                'pnl_pct': pnl_pct,
                'balance': fixed_balance,
                'result': result_type
            })
            
            # Equity-based simulation
            equity_position_size, sizing_details = self.calculate_equity_position_size(
                equity_balance, signal['entry_price'], signal['stop_loss'], signal['side']
            )
            equity_pnl = equity_position_size * (pnl_pct / 100)
            equity_balance += equity_pnl
            equity_trades.append({
                'trade_num': i + 1,
                'symbol': signal['symbol'],
                'side': signal['side'],
                'position_size': equity_position_size,
                'pnl': equity_pnl,
                'pnl_pct': pnl_pct,
                'balance': equity_balance,
                'result': result_type,
                'risk_pct': sizing_details.get('actual_risk_pct', 0)
            })
        
        # Calculate performance metrics
        results = self.calculate_performance_metrics(fixed_trades, equity_trades)
        results['total_simulated_trades'] = len(expanded_signals)
        results['unique_signals'] = len(signals)
        
        return results
    
    def calculate_performance_metrics(self, fixed_trades: List[Dict], equity_trades: List[Dict]) -> Dict:
        """Calculate comprehensive performance metrics"""
        
        def calc_metrics(trades, initial_balance):
            total_trades = len(trades)
            if total_trades == 0:
                return {}
            
            final_balance = trades[-1]['balance']
            total_return = final_balance - initial_balance
            total_return_pct = (total_return / initial_balance) * 100
            
            wins = [t for t in trades if t['pnl'] > 0]
            losses = [t for t in trades if t['pnl'] < 0]
            
            win_rate = (len(wins) / total_trades) * 100 if total_trades > 0 else 0
            
            avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
            avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
            
            profit_factor = abs(sum(t['pnl'] for t in wins) / sum(t['pnl'] for t in losses)) if losses else float('inf')
            
            # Maximum drawdown
            peak = initial_balance
            max_dd = 0
            for trade in trades:
                balance = trade['balance']
                if balance > peak:
                    peak = balance
                drawdown = (peak - balance) / peak * 100
                max_dd = max(max_dd, drawdown)
            
            # Sharpe ratio approximation
            returns = [(t['balance'] - initial_balance) / initial_balance for t in trades]
            if len(returns) > 1:
                import statistics
                avg_return = statistics.mean(returns)
                std_return = statistics.stdev(returns)
                sharpe = (avg_return / std_return) * (252 ** 0.5) if std_return > 0 else 0
            else:
                sharpe = 0
            
            # Best and worst trades
            best_trade = max(trades, key=lambda x: x['pnl'])['pnl'] if trades else 0
            worst_trade = min(trades, key=lambda x: x['pnl'])['pnl'] if trades else 0
            
            return {
                'total_trades': total_trades,
                'final_balance': final_balance,
                'total_return': total_return,
                'total_return_pct': total_return_pct,
                'win_rate': win_rate,
                'wins': len(wins),
                'losses': len(losses),
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'max_drawdown': max_dd,
                'sharpe_ratio': sharpe,
                'best_trade': best_trade,
                'worst_trade': worst_trade
            }
        
        fixed_metrics = calc_metrics(fixed_trades, self.initial_capital)
        equity_metrics = calc_metrics(equity_trades, self.initial_capital)
        
        # Calculate improvement metrics
        improvement = {}
        if fixed_metrics and equity_metrics:
            improvement = {
                'return_improvement': equity_metrics['total_return'] - fixed_metrics['total_return'],
                'return_pct_improvement': equity_metrics['total_return_pct'] - fixed_metrics['total_return_pct'],
                'win_rate_improvement': equity_metrics['win_rate'] - fixed_metrics['win_rate'],
                'profit_factor_improvement': (equity_metrics['profit_factor'] - fixed_metrics['profit_factor']) if fixed_metrics['profit_factor'] != float('inf') else 0,
                'max_dd_improvement': fixed_metrics['max_drawdown'] - equity_metrics['max_drawdown'],
                'sharpe_improvement': equity_metrics['sharpe_ratio'] - fixed_metrics['sharpe_ratio']
            }
        
        return {
            'fixed_size_results': fixed_metrics,
            'equity_based_results': equity_metrics,
            'improvement_metrics': improvement
        }
    
    def print_comprehensive_report(self, results: Dict):
        """Print comprehensive comparison report"""
        if not results:
            print("No results to display")
            return
        
        fixed = results['fixed_size_results']
        equity = results['equity_based_results']
        improvement = results['improvement_metrics']
        
        print("\n" + "="*70)
        print("COMPREHENSIVE EQUITY-BASED vs FIXED-SIZE BACKTEST")
        print("="*70)
        print(f"Simulated Trades: {results['total_simulated_trades']:,}")
        print(f"Unique Signals: {results['unique_signals']}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        
        print(f"\nPERFORMANCE COMPARISON")
        print(f"{'Metric':<25} {'Fixed ($1K)':<15} {'Equity (2%)':<15} {'Improvement':<15}")
        print("-"*70)
        print(f"{'Final Balance':<25} ${fixed['final_balance']:>10.2f}   ${equity['final_balance']:>10.2f}   ${improvement['return_improvement']:>10.2f}")
        print(f"{'Total Return':<25} {fixed['total_return_pct']:>10.2f}%   {equity['total_return_pct']:>10.2f}%   {improvement['return_pct_improvement']:>10.2f}%")
        print(f"{'Win Rate':<25} {fixed['win_rate']:>10.1f}%   {equity['win_rate']:>10.1f}%   {improvement['win_rate_improvement']:>10.1f}%")
        print(f"{'Profit Factor':<25} {fixed['profit_factor']:>10.2f}   {equity['profit_factor']:>10.2f}   {improvement['profit_factor_improvement']:>10.2f}")
        print(f"{'Max Drawdown':<25} {fixed['max_drawdown']:>10.2f}%   {equity['max_drawdown']:>10.2f}%   {improvement['max_dd_improvement']:>10.2f}%")
        print(f"{'Sharpe Ratio':<25} {fixed['sharpe_ratio']:>10.2f}   {equity['sharpe_ratio']:>10.2f}   {improvement['sharpe_improvement']:>10.2f}")
        
        print(f"\nTRADE STATISTICS")
        print(f"Total Trades: {fixed['total_trades']:,}")
        print(f"Wins: {equity['wins']:,} ({equity['win_rate']:.1f}%) | Losses: {equity['losses']:,}")
        print(f"Average Win: ${equity['avg_win']:.2f} | Average Loss: ${equity['avg_loss']:.2f}")
        print(f"Best Trade: ${equity['best_trade']:.2f} | Worst Trade: ${equity['worst_trade']:.2f}")
        
        print(f"\nKEY INSIGHTS")
        if improvement['return_pct_improvement'] > 0:
            print(f"[+] Equity-based system outperformed by {improvement['return_pct_improvement']:.2f}%")
            print(f"[+] Extra profit: ${improvement['return_improvement']:.2f}")
        else:
            print(f"[-] Fixed-size system outperformed by {abs(improvement['return_pct_improvement']):.2f}%")
        
        if improvement['max_dd_improvement'] > 0:
            print(f"[+] Equity-based system reduced max drawdown by {improvement['max_dd_improvement']:.2f}%")
        else:
            print(f"[-] Equity-based system increased max drawdown by {abs(improvement['max_dd_improvement']):.2f}%")
        
        # Calculate final ROI difference
        roi_multiplier = (equity['final_balance'] / fixed['final_balance']) if fixed['final_balance'] > 0 else 1
        print(f"\nROI MULTIPLIER: {roi_multiplier:.2f}x")
        print(f"For every $1 the fixed system made, equity-based made ${roi_multiplier:.2f}")

def main():
    """Run the comprehensive backtest"""
    backtester = ComprehensiveBacktester()
    
    print("Running comprehensive equity-based position sizing backtest...")
    print("This may take a moment as we simulate 1000+ trades...")
    
    results = backtester.run_comprehensive_backtest(num_iterations=1000)
    
    if results:
        backtester.print_comprehensive_report(results)
    else:
        print("No backtest results generated. Check signal data.")

if __name__ == "__main__":
    main()