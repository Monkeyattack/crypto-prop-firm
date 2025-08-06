#!/usr/bin/env python3
"""
Equity-Based Position Sizing Backtest Comparison
Compare performance of new equity-based system vs old fixed-size system
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EquityBacktester:
    def __init__(self):
        self.initial_capital = 10000.0
        self.equity_settings = {
            'risk_per_trade_pct': 2.0,
            'max_portfolio_risk_pct': 10.0,
            'max_position_size_pct': 20.0,
            'min_position_size_usd': 100.0,
            'max_position_size_usd': 5000.0
        }
        
    def get_historical_signals(self) -> List[Dict]:
        """Get historical signals from the database"""
        try:
            conn = sqlite3.connect('trade_log.db')
            cursor = conn.cursor()
            
            # Get all closed trades with their details
            cursor.execute('''
                SELECT symbol, side, entry, tp, sl, result, pnl, timestamp, position_size
                FROM trades
                WHERE result IN ('tp', 'sl', 'trailing', 'manual')
                ORDER BY timestamp
            ''')
            
            trades = []
            for row in cursor.fetchall():
                trade = {
                    'symbol': row[0],
                    'side': row[1],
                    'entry': row[2],
                    'tp': row[3],
                    'sl': row[4],
                    'result': row[5],
                    'pnl': row[6] if row[6] else 0,
                    'timestamp': row[7],
                    'old_position_size': row[8] if row[8] else 1000.0
                }
                trades.append(trade)
            
            conn.close()
            logger.info(f"Loaded {len(trades)} historical trades for backtesting")
            return trades
            
        except Exception as e:
            logger.error(f"Error loading historical signals: {e}")
            return []
    
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
    
    def simulate_trade_outcome(self, trade: Dict, position_size: float) -> float:
        """Simulate trade outcome with given position size"""
        entry = trade['entry']
        result = trade['result']
        side = trade['side']
        
        if result == 'tp':
            # Take profit hit - calculate profit
            tp = trade['tp']
            if side.upper() in ['BUY', 'LONG']:
                profit_pct = ((tp - entry) / entry) * 100
            else:
                profit_pct = ((entry - tp) / entry) * 100
            
            return position_size * (profit_pct / 100)
            
        elif result in ['sl', 'manual']:
            # Stop loss or manual close - calculate loss
            sl = trade['sl']
            if side.upper() in ['BUY', 'LONG']:
                loss_pct = ((entry - sl) / entry) * 100
            else:
                loss_pct = ((sl - entry) / entry) * 100
            
            return -position_size * (loss_pct / 100)
            
        elif result == 'trailing':
            # Trailing stop - use actual P&L from historical data
            if trade['pnl']:
                # Scale the P&L proportionally to position size difference
                old_size = trade['old_position_size']
                scaling_factor = position_size / old_size if old_size > 0 else 1
                return trade['pnl'] * scaling_factor
            else:
                # Assume 3.5% profit (fallback trailing target)
                return position_size * 0.035
        
        return 0.0
    
    def run_backtest_comparison(self) -> Dict:
        """Run backtest comparing fixed vs equity-based position sizing"""
        trades = self.get_historical_signals()
        
        if not trades:
            logger.warning("No historical trades found for backtesting")
            return {}
        
        # Fixed-size backtest results
        fixed_balance = self.initial_capital
        fixed_trades = []
        fixed_position_size = 1000.0  # Old fixed size
        
        # Equity-based backtest results
        equity_balance = self.initial_capital
        equity_trades = []
        
        logger.info("Running backtest comparison...")
        
        for i, trade in enumerate(trades):
            # Fixed-size simulation
            fixed_pnl = self.simulate_trade_outcome(trade, fixed_position_size)
            fixed_balance += fixed_pnl
            fixed_trades.append({
                'trade_num': i + 1,
                'symbol': trade['symbol'],
                'position_size': fixed_position_size,
                'pnl': fixed_pnl,
                'balance': fixed_balance,
                'result': trade['result']
            })
            
            # Equity-based simulation
            equity_position_size, sizing_details = self.calculate_equity_position_size(
                equity_balance, trade['entry'], trade['sl'], trade['side']
            )
            equity_pnl = self.simulate_trade_outcome(trade, equity_position_size)
            equity_balance += equity_pnl
            equity_trades.append({
                'trade_num': i + 1,
                'symbol': trade['symbol'],
                'position_size': equity_position_size,
                'pnl': equity_pnl,
                'balance': equity_balance,
                'result': trade['result'],
                'risk_pct': sizing_details.get('actual_risk_pct', 0)
            })
        
        # Calculate performance metrics
        results = self.calculate_performance_metrics(fixed_trades, equity_trades)
        
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
            
            # Sharpe ratio approximation (assuming daily trades)
            returns = [t['pnl'] / initial_balance for t in trades]
            if len(returns) > 1:
                import statistics
                avg_return = statistics.mean(returns)
                std_return = statistics.stdev(returns)
                sharpe = (avg_return / std_return) * (252 ** 0.5) if std_return > 0 else 0
            else:
                sharpe = 0
            
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
                'sharpe_ratio': sharpe
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
                'profit_factor_improvement': equity_metrics['profit_factor'] - fixed_metrics['profit_factor'],
                'max_dd_improvement': fixed_metrics['max_drawdown'] - equity_metrics['max_drawdown'],  # Lower is better
                'sharpe_improvement': equity_metrics['sharpe_ratio'] - fixed_metrics['sharpe_ratio']
            }
        
        return {
            'fixed_size_results': fixed_metrics,
            'equity_based_results': equity_metrics,
            'improvement_metrics': improvement,
            'fixed_trades': fixed_trades[-5:],  # Last 5 trades for reference
            'equity_trades': equity_trades[-5:]  # Last 5 trades for reference
        }
    
    def print_comparison_report(self, results: Dict):
        """Print comprehensive comparison report"""
        if not results:
            print("No results to display")
            return
        
        fixed = results['fixed_size_results']
        equity = results['equity_based_results']
        improvement = results['improvement_metrics']
        
        print("\n" + "="*60)
        print("EQUITY-BASED vs FIXED-SIZE BACKTEST COMPARISON")
        print("="*60)
        
        print(f"\nPERFORMANCE SUMMARY")
        print(f"{'Metric':<25} {'Fixed-Size':<15} {'Equity-Based':<15} {'Improvement':<15}")
        print("-"*70)
        print(f"{'Total Return':<25} ${fixed['total_return']:>8.2f}     ${equity['total_return']:>8.2f}     ${improvement['return_improvement']:>8.2f}")
        print(f"{'Return %':<25} {fixed['total_return_pct']:>8.2f}%     {equity['total_return_pct']:>8.2f}%     {improvement['return_pct_improvement']:>8.2f}%")
        print(f"{'Final Balance':<25} ${fixed['final_balance']:>8.2f}     ${equity['final_balance']:>8.2f}     ${equity['final_balance'] - fixed['final_balance']:>8.2f}")
        print(f"{'Win Rate':<25} {fixed['win_rate']:>8.1f}%     {equity['win_rate']:>8.1f}%     {improvement['win_rate_improvement']:>8.1f}%")
        print(f"{'Profit Factor':<25} {fixed['profit_factor']:>8.2f}      {equity['profit_factor']:>8.2f}      {improvement['profit_factor_improvement']:>8.2f}")
        print(f"{'Max Drawdown':<25} {fixed['max_drawdown']:>8.2f}%     {equity['max_drawdown']:>8.2f}%     {improvement['max_dd_improvement']:>8.2f}%")
        print(f"{'Sharpe Ratio':<25} {fixed['sharpe_ratio']:>8.2f}      {equity['sharpe_ratio']:>8.2f}      {improvement['sharpe_improvement']:>8.2f}")
        
        print(f"\nTRADE STATISTICS")
        print(f"Total Trades: {fixed['total_trades']}")
        print(f"Wins: {equity['wins']} | Losses: {equity['losses']}")
        print(f"Average Win: ${equity['avg_win']:.2f} | Average Loss: ${equity['avg_loss']:.2f}")
        
        print(f"\nKEY INSIGHTS")
        if improvement['return_pct_improvement'] > 0:
            print(f"[+] Equity-based system generated {improvement['return_pct_improvement']:.2f}% higher returns")
        else:
            print(f"[-] Fixed-size system performed {abs(improvement['return_pct_improvement']):.2f}% better")
        
        if improvement['max_dd_improvement'] > 0:
            print(f"[+] Equity-based system reduced max drawdown by {improvement['max_dd_improvement']:.2f}%")
        else:
            print(f"[-] Equity-based system increased max drawdown by {abs(improvement['max_dd_improvement']):.2f}%")
        
        if improvement['sharpe_improvement'] > 0:
            print(f"[+] Equity-based system improved risk-adjusted returns (Sharpe: +{improvement['sharpe_improvement']:.2f})")
        else:
            print(f"[-] Fixed-size system had better risk-adjusted returns (Sharpe: {abs(improvement['sharpe_improvement']):.2f})")
        
        # Show position sizing examples
        print(f"\nPOSITION SIZE EXAMPLES (Last 5 Trades)")
        print(f"{'Trade':<8} {'Symbol':<10} {'Fixed Size':<12} {'Equity Size':<12} {'Result':<10}")
        print("-"*55)
        
        for i in range(min(5, len(results['equity_trades']))):
            fixed_trade = results['fixed_trades'][i]
            equity_trade = results['equity_trades'][i]
            print(f"#{equity_trade['trade_num']:<7} {equity_trade['symbol']:<10} ${fixed_trade['position_size']:>8.0f}    ${equity_trade['position_size']:>8.0f}    {equity_trade['result']:<10}")

def main():
    """Run the backtest comparison"""
    backtester = EquityBacktester()
    
    print("Running equity-based position sizing backtest comparison...")
    results = backtester.run_backtest_comparison()
    
    if results:
        backtester.print_comparison_report(results)
    else:
        print("No backtest results generated. Check historical data.")

if __name__ == "__main__":
    main()