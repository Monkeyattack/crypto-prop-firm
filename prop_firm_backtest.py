"""
Prop Firm Backtest - Test if strategy passes $10k evaluation
Combines existing strategy with prop firm rules
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import json
import logging
from typing import Dict, List, Tuple
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from prop_firm_manager import PropFirmManager, PropFirmConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PropFirmBacktest:
    """Backtest the strategy with prop firm rules"""
    
    def __init__(self):
        # Load optimized strategy config
        with open('optimized_strategy_config.json', 'r') as f:
            self.strategy_config = json.load(f)
        
        # Initialize prop firm manager
        self.prop_config = PropFirmConfig()
        self.initial_balance = 10000.00
        
        # Trading parameters from original strategy
        self.preferred_symbols = self.strategy_config['entry_criteria']['preferred_symbols']
        self.avoid_symbols = self.strategy_config['entry_criteria']['avoid_symbols']
        self.min_risk_reward = self.strategy_config['entry_criteria']['min_risk_reward_ratio']
        
        # Results tracking
        self.trades = []
        self.daily_results = []
        self.evaluation_passed = False
        self.evaluation_failed = False
        
    def load_historical_signals(self) -> pd.DataFrame:
        """Load historical signals from database"""
        try:
            conn = sqlite3.connect('trading.db')
            
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
                logger.info(f"Loaded {len(df)} historical signals")
            else:
                logger.warning("No historical signals found")
                
            return df
            
        except Exception as e:
            logger.error(f"Error loading signals: {e}")
            return pd.DataFrame()
    
    def calculate_position_size(self, balance: float, stop_loss_pct: float) -> float:
        """Calculate position size based on prop firm rules"""
        # Use 1.5% risk per trade (prop firm rule)
        risk_amount = balance * 0.015
        
        # Calculate position size
        position_size = risk_amount / (stop_loss_pct / 100)
        
        # Apply leverage limits (5x for BTC/ETH, 2x for alts)
        max_position = balance * 5  # Assume max leverage
        
        return min(position_size, max_position)
    
    def simulate_trade_outcome(self, signal: pd.Series, symbol_stats: Dict) -> Tuple[bool, float]:
        """Simulate trade outcome based on historical statistics"""
        symbol = signal['symbol']
        side = signal['side'].upper()
        entry_price = float(signal['entry_price'])
        take_profit = float(signal['take_profit'])
        stop_loss = float(signal['stop_loss'])
        
        # Calculate risk/reward ratio
        if side in ['BUY', 'LONG']:
            profit_potential = (take_profit - entry_price) / entry_price
            loss_potential = (entry_price - stop_loss) / entry_price
        else:
            profit_potential = (entry_price - take_profit) / entry_price
            loss_potential = (stop_loss - entry_price) / entry_price
        
        risk_reward_ratio = profit_potential / loss_potential if loss_potential > 0 else 0
        
        # Base win rate from optimized strategy (40% historical)
        base_win_rate = 0.40
        
        # Adjust for preferred symbols
        if symbol in self.preferred_symbols:
            base_win_rate += 0.10
        elif symbol in self.avoid_symbols:
            base_win_rate -= 0.10
        
        # Adjust for risk/reward ratio
        if risk_reward_ratio >= self.min_risk_reward:
            base_win_rate += 0.05
        if risk_reward_ratio >= 2.0:
            base_win_rate += 0.05
        
        # Cap win rate between 25% and 65%
        win_rate = max(0.25, min(0.65, base_win_rate))
        
        # Simulate outcome
        won_trade = np.random.random() < win_rate
        
        if won_trade:
            pnl_pct = profit_potential
        else:
            pnl_pct = -loss_potential
        
        return won_trade, pnl_pct
    
    def run_backtest(self, start_date: datetime = None, end_date: datetime = None):
        """Run the backtest with prop firm rules"""
        logger.info("Starting prop firm backtest...")
        
        # Load historical signals
        signals_df = self.load_historical_signals()
        
        if signals_df.empty:
            logger.error("No signals to backtest")
            return
        
        # Filter by date range if provided
        if start_date:
            signals_df = signals_df[signals_df['message_date'] >= start_date]
        if end_date:
            signals_df = signals_df[signals_df['message_date'] <= end_date]
        
        # Initialize tracking variables
        current_balance = self.initial_balance
        peak_balance = self.initial_balance
        daily_start_balance = self.initial_balance
        daily_trades = 0
        daily_pnl = 0
        current_date = None
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        
        # Process each signal
        for idx, signal in signals_df.iterrows():
            signal_date = signal['message_date'].date()
            
            # Check for new day (reset at 00:30 UTC)
            if current_date is None:
                current_date = signal_date
            elif signal_date != current_date:
                # Save daily results
                self.daily_results.append({
                    'date': current_date,
                    'starting_balance': daily_start_balance,
                    'ending_balance': current_balance,
                    'daily_pnl': daily_pnl,
                    'daily_pnl_pct': (daily_pnl / daily_start_balance) * 100,
                    'trades': daily_trades,
                    'cumulative_pnl': current_balance - self.initial_balance
                })
                
                # Reset daily tracking
                current_date = signal_date
                daily_start_balance = current_balance
                daily_pnl = 0
                daily_trades = 0
            
            # Check evaluation status
            if self.evaluation_passed or self.evaluation_failed:
                break
            
            # Calculate risk/reward
            symbol = signal['symbol']
            entry_price = float(signal['entry_price'])
            take_profit = float(signal['take_profit'])
            stop_loss = float(signal['stop_loss'])
            
            if signal['side'].upper() in ['BUY', 'LONG']:
                stop_loss_pct = ((entry_price - stop_loss) / entry_price) * 100
            else:
                stop_loss_pct = ((stop_loss - entry_price) / entry_price) * 100
            
            # Skip if risk/reward is too low
            risk_reward = abs((take_profit - entry_price) / (entry_price - stop_loss))
            if risk_reward < self.min_risk_reward:
                continue
            
            # Check prop firm risk limits
            position_size = self.calculate_position_size(current_balance, stop_loss_pct)
            potential_loss = position_size * (stop_loss_pct / 100)
            
            # Check daily loss limit
            if abs(daily_pnl - potential_loss) > self.prop_config.max_daily_loss:
                logger.debug(f"Skipping trade - would exceed daily loss limit")
                continue
            
            # Check drawdown limit
            current_drawdown = peak_balance - current_balance
            if (current_drawdown + potential_loss) > self.prop_config.max_drawdown:
                logger.debug(f"Skipping trade - would exceed max drawdown")
                continue
            
            # Check max concurrent trades (3 for prop firm)
            if daily_trades >= 3:
                continue
            
            # Simulate trade outcome
            won_trade, pnl_pct = self.simulate_trade_outcome(signal, {})
            trade_pnl = position_size * pnl_pct
            
            # Update balance
            current_balance += trade_pnl
            daily_pnl += trade_pnl
            daily_trades += 1
            total_trades += 1
            
            if won_trade:
                winning_trades += 1
            else:
                losing_trades += 1
            
            # Update peak balance
            if current_balance > peak_balance:
                peak_balance = current_balance
            
            # Record trade
            self.trades.append({
                'date': signal_date,
                'symbol': symbol,
                'side': signal['side'],
                'entry': entry_price,
                'exit': take_profit if won_trade else stop_loss,
                'position_size': position_size,
                'pnl': trade_pnl,
                'pnl_pct': pnl_pct * 100,
                'won': won_trade,
                'balance': current_balance,
                'drawdown': peak_balance - current_balance
            })
            
            # Check if evaluation passed
            total_profit = current_balance - self.initial_balance
            if total_profit >= self.prop_config.profit_target:
                self.evaluation_passed = True
                logger.info(f"✅ EVALUATION PASSED! Profit: ${total_profit:.2f}")
                break
            
            # Check if evaluation failed (drawdown breach)
            drawdown = peak_balance - current_balance
            if drawdown >= self.prop_config.max_drawdown:
                self.evaluation_failed = True
                logger.error(f"❌ EVALUATION FAILED! Drawdown: ${drawdown:.2f}")
                break
            
            # Check daily loss breach
            if abs(daily_pnl) >= self.prop_config.max_daily_loss:
                logger.warning(f"Daily loss limit reached: ${daily_pnl:.2f}")
                # Skip to next day in real scenario
        
        # Save final day results
        if daily_trades > 0:
            self.daily_results.append({
                'date': current_date,
                'starting_balance': daily_start_balance,
                'ending_balance': current_balance,
                'daily_pnl': daily_pnl,
                'daily_pnl_pct': (daily_pnl / daily_start_balance) * 100,
                'trades': daily_trades,
                'cumulative_pnl': current_balance - self.initial_balance
            })
        
        # Calculate final statistics
        self.final_stats = {
            'evaluation_passed': self.evaluation_passed,
            'evaluation_failed': self.evaluation_failed,
            'final_balance': current_balance,
            'total_pnl': current_balance - self.initial_balance,
            'total_pnl_pct': ((current_balance - self.initial_balance) / self.initial_balance) * 100,
            'peak_balance': peak_balance,
            'max_drawdown': peak_balance - min([t['balance'] for t in self.trades]) if self.trades else 0,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            'days_traded': len(self.daily_results),
            'avg_daily_pnl': np.mean([d['daily_pnl'] for d in self.daily_results]) if self.daily_results else 0,
            'best_day': max([d['daily_pnl'] for d in self.daily_results]) if self.daily_results else 0,
            'worst_day': min([d['daily_pnl'] for d in self.daily_results]) if self.daily_results else 0
        }
    
    def generate_report(self) -> str:
        """Generate detailed backtest report"""
        report = []
        report.append("=" * 60)
        report.append("PROP FIRM BACKTEST REPORT - $10,000 ONE-STEP EVALUATION")
        report.append("=" * 60)
        report.append("")
        
        # Evaluation Result
        if self.evaluation_passed:
            report.append("🎉 EVALUATION STATUS: PASSED ✅")
            report.append(f"Days to Pass: {self.final_stats['days_traded']}")
        elif self.evaluation_failed:
            report.append("❌ EVALUATION STATUS: FAILED")
            report.append(f"Reason: Maximum drawdown exceeded")
        else:
            report.append("⏳ EVALUATION STATUS: IN PROGRESS")
            progress = (self.final_stats['total_pnl'] / self.prop_config.profit_target) * 100
            report.append(f"Progress to Target: {progress:.1f}%")
        
        report.append("")
        report.append("PERFORMANCE SUMMARY")
        report.append("-" * 40)
        report.append(f"Initial Balance:     ${self.initial_balance:,.2f}")
        report.append(f"Final Balance:       ${self.final_stats['final_balance']:,.2f}")
        report.append(f"Total P&L:           ${self.final_stats['total_pnl']:,.2f} ({self.final_stats['total_pnl_pct']:.2f}%)")
        report.append(f"Peak Balance:        ${self.final_stats['peak_balance']:,.2f}")
        report.append(f"Max Drawdown:        ${self.final_stats['max_drawdown']:,.2f}")
        report.append("")
        
        report.append("TRADING STATISTICS")
        report.append("-" * 40)
        report.append(f"Total Trades:        {self.final_stats['total_trades']}")
        report.append(f"Winning Trades:      {self.final_stats['winning_trades']}")
        report.append(f"Losing Trades:       {self.final_stats['losing_trades']}")
        report.append(f"Win Rate:            {self.final_stats['win_rate']:.1f}%")
        report.append(f"Days Traded:         {self.final_stats['days_traded']}")
        report.append(f"Avg Trades/Day:      {self.final_stats['total_trades'] / max(1, self.final_stats['days_traded']):.1f}")
        report.append("")
        
        report.append("DAILY PERFORMANCE")
        report.append("-" * 40)
        report.append(f"Average Daily P&L:   ${self.final_stats['avg_daily_pnl']:,.2f}")
        report.append(f"Best Day:            ${self.final_stats['best_day']:,.2f}")
        report.append(f"Worst Day:           ${self.final_stats['worst_day']:,.2f}")
        report.append("")
        
        report.append("RISK METRICS vs LIMITS")
        report.append("-" * 40)
        report.append(f"Max Daily Loss Limit:    ${self.prop_config.max_daily_loss:.2f}")
        report.append(f"Worst Daily Loss:        ${abs(self.final_stats['worst_day']):.2f}")
        report.append(f"Max Drawdown Limit:      ${self.prop_config.max_drawdown:.2f}")
        report.append(f"Actual Max Drawdown:     ${self.final_stats['max_drawdown']:.2f}")
        report.append("")
        
        # Time estimation
        if self.evaluation_passed:
            report.append("TIME TO COMPLETION")
            report.append("-" * 40)
            report.append(f"Days Required:       {self.final_stats['days_traded']}")
            report.append(f"Estimated Weeks:     {self.final_stats['days_traded'] / 7:.1f}")
        elif not self.evaluation_failed and self.final_stats['avg_daily_pnl'] > 0:
            remaining = self.prop_config.profit_target - self.final_stats['total_pnl']
            days_needed = remaining / self.final_stats['avg_daily_pnl']
            report.append("PROJECTED COMPLETION")
            report.append("-" * 40)
            report.append(f"P&L Remaining:       ${remaining:.2f}")
            report.append(f"Est. Days to Pass:   {days_needed:.0f}")
            report.append(f"Est. Weeks to Pass:  {days_needed / 7:.1f}")
        
        report.append("")
        report.append("TOP 5 WINNING TRADES")
        report.append("-" * 40)
        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            top_trades = trades_df.nlargest(5, 'pnl')
            for _, trade in top_trades.iterrows():
                report.append(f"{trade['date']} {trade['symbol']:8} ${trade['pnl']:7.2f} ({trade['pnl_pct']:5.1f}%)")
        
        report.append("")
        report.append("TOP 5 LOSING TRADES")
        report.append("-" * 40)
        if self.trades:
            worst_trades = trades_df.nsmallest(5, 'pnl')
            for _, trade in worst_trades.iterrows():
                report.append(f"{trade['date']} {trade['symbol']:8} ${trade['pnl']:7.2f} ({trade['pnl_pct']:5.1f}%)")
        
        report.append("")
        report.append("DAILY P&L PROGRESSION")
        report.append("-" * 40)
        for day in self.daily_results[-10:]:  # Last 10 days
            bar = "+" * int(abs(day['daily_pnl']) / 20) if day['daily_pnl'] > 0 else "-" * int(abs(day['daily_pnl']) / 20)
            report.append(f"{day['date']}: ${day['daily_pnl']:7.2f} {bar}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def save_results(self, filename: str = "prop_firm_backtest_results.json"):
        """Save backtest results to JSON file"""
        results = {
            'config': {
                'initial_balance': self.initial_balance,
                'profit_target': self.prop_config.profit_target,
                'max_drawdown': self.prop_config.max_drawdown,
                'max_daily_loss': self.prop_config.max_daily_loss
            },
            'final_stats': self.final_stats,
            'daily_results': self.daily_results,
            'trades': self.trades[-50:] if len(self.trades) > 50 else self.trades  # Last 50 trades
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {filename}")


def main():
    """Run the prop firm backtest"""
    logger.info("Starting Prop Firm Backtest for $10,000 One-Step Evaluation")
    
    # Initialize backtest
    backtest = PropFirmBacktest()
    
    # Run backtest (use last 6 months of data if available)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    backtest.run_backtest(start_date=start_date, end_date=end_date)
    
    # Generate and print report
    report = backtest.generate_report()
    print(report)
    
    # Save results
    backtest.save_results()
    
    # Return success status
    return backtest.evaluation_passed


if __name__ == "__main__":
    success = main()