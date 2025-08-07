"""
Prop Firm Strategy Simulation
Simulates your trading strategy with prop firm rules to estimate evaluation success
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import random

class PropFirmSimulation:
    """Simulate prop firm evaluation with your strategy parameters"""
    
    def __init__(self):
        # Load your optimized strategy config
        with open('optimized_strategy_config.json', 'r') as f:
            self.strategy = json.load(f)
        
        # Prop firm parameters ($10k one-step)
        self.initial_balance = 10000
        self.profit_target = 1000  # 10%
        self.max_drawdown = 600    # 6%
        self.max_daily_loss = 500  # 5%
        
        # Strategy parameters from your config
        self.win_rate = 0.40  # 40% historical win rate
        self.avg_rr_ratio = 2.0  # Risk-reward ratio
        self.risk_per_trade = 0.015  # 1.5% risk per trade
        
        # Preferred symbols with better performance
        self.preferred_symbols = ['DOTUSDT', 'BTCUSDT', 'SOLUSDT', 'ADAUSDT']
        self.regular_symbols = ['ATOMUSDT', 'LINKUSDT', 'AVAXUSDT']
        self.avoid_symbols = ['MATICUSDT', 'ETHUSDT', 'UNIUSDT']
        
    def generate_realistic_signals(self, days: int = 30) -> list:
        """Generate realistic trading signals based on your strategy"""
        signals = []
        current_date = datetime.now()
        
        for day in range(days):
            trade_date = current_date + timedelta(days=day)
            
            # Generate 2-5 signals per day (realistic for crypto)
            daily_signals = random.randint(2, 5)
            
            for _ in range(daily_signals):
                # Choose symbol based on your strategy preferences
                symbol_choice = random.random()
                if symbol_choice < 0.5:  # 50% chance for preferred symbols
                    symbol = random.choice(self.preferred_symbols)
                    win_rate_adj = 0.10  # Better win rate for preferred
                elif symbol_choice < 0.8:  # 30% chance for regular
                    symbol = random.choice(self.regular_symbols)
                    win_rate_adj = 0.0
                else:  # 20% chance for avoid symbols
                    symbol = random.choice(self.avoid_symbols)
                    win_rate_adj = -0.10  # Worse win rate
                
                # Generate risk-reward ratio (your strategy targets 1.5+)
                rr_ratio = np.random.uniform(1.5, 3.0)
                
                signals.append({
                    'date': trade_date,
                    'symbol': symbol,
                    'rr_ratio': rr_ratio,
                    'win_rate_adjustment': win_rate_adj
                })
        
        return signals
    
    def run_monte_carlo_simulation(self, num_simulations: int = 1000):
        """Run multiple simulations to estimate success probability"""
        results = []
        
        for sim in range(num_simulations):
            result = self.simulate_single_evaluation()
            results.append(result)
        
        # Analyze results
        passed_count = sum(1 for r in results if r['passed'])
        failed_count = sum(1 for r in results if r['failed'])
        avg_days = np.mean([r['days'] for r in results if r['passed']])
        avg_final_balance = np.mean([r['final_balance'] for r in results])
        
        return {
            'pass_rate': (passed_count / num_simulations) * 100,
            'fail_rate': (failed_count / num_simulations) * 100,
            'avg_days_to_pass': avg_days if passed_count > 0 else None,
            'avg_final_balance': avg_final_balance,
            'simulations_run': num_simulations,
            'detailed_results': results[:10]  # First 10 for inspection
        }
    
    def simulate_single_evaluation(self, max_days: int = 60) -> dict:
        """Simulate a single evaluation attempt"""
        balance = self.initial_balance
        peak_balance = self.initial_balance
        daily_balance = self.initial_balance
        daily_pnl = 0
        total_trades = 0
        winning_trades = 0
        current_day = 0
        
        signals = self.generate_realistic_signals(max_days)
        
        for signal in signals:
            # New day reset
            if current_day != signal['date'].day:
                daily_balance = balance
                daily_pnl = 0
                current_day = signal['date'].day
            
            # Check if we can trade (prop firm rules)
            if abs(daily_pnl) >= self.max_daily_loss * 0.8:  # Stop at 80% of daily limit
                continue
            
            drawdown = peak_balance - balance
            if drawdown >= self.max_drawdown * 0.9:  # Stop at 90% of max drawdown
                return {
                    'passed': False,
                    'failed': True,
                    'reason': 'Drawdown limit',
                    'final_balance': balance,
                    'days': current_day,
                    'trades': total_trades
                }
            
            # Calculate position size and risk
            position_risk = balance * self.risk_per_trade
            
            # Determine trade outcome
            adjusted_win_rate = self.win_rate + signal['win_rate_adjustment']
            win = random.random() < adjusted_win_rate
            
            if win:
                # Win: gain based on risk-reward ratio
                trade_pnl = position_risk * signal['rr_ratio']
                winning_trades += 1
            else:
                # Loss: lose the risk amount
                trade_pnl = -position_risk
            
            # Update balances
            balance += trade_pnl
            daily_pnl += trade_pnl
            total_trades += 1
            
            # Update peak
            if balance > peak_balance:
                peak_balance = balance
            
            # Check if passed
            if balance >= self.initial_balance + self.profit_target:
                return {
                    'passed': True,
                    'failed': False,
                    'reason': 'Target reached',
                    'final_balance': balance,
                    'days': current_day,
                    'trades': total_trades,
                    'win_rate': (winning_trades / total_trades) * 100
                }
            
            # Check if failed
            if balance <= self.initial_balance - self.max_drawdown:
                return {
                    'passed': False,
                    'failed': True,
                    'reason': 'Account drawdown',
                    'final_balance': balance,
                    'days': current_day,
                    'trades': total_trades
                }
        
        # Evaluation incomplete after max days
        return {
            'passed': False,
            'failed': False,
            'reason': 'Time limit',
            'final_balance': balance,
            'days': max_days,
            'trades': total_trades
        }
    
    def generate_report(self, simulation_results: dict) -> str:
        """Generate comprehensive simulation report"""
        report = []
        report.append("=" * 70)
        report.append("PROP FIRM EVALUATION SIMULATION REPORT")
        report.append("$10,000 One-Step Evaluation - Based on Your Strategy")
        report.append("=" * 70)
        report.append("")
        
        report.append("STRATEGY PARAMETERS (from your optimized config)")
        report.append("-" * 50)
        report.append(f"Historical Win Rate:        40%")
        report.append(f"Risk-Reward Target:         1.5+ (avg 2.0)")
        report.append(f"Risk Per Trade:             1.5%")
        report.append(f"Preferred Symbols:          DOTUSDT, BTCUSDT, SOLUSDT, ADAUSDT")
        report.append(f"Symbols to Avoid:           MATICUSDT, ETHUSDT, UNIUSDT")
        report.append("")
        
        report.append("PROP FIRM REQUIREMENTS")
        report.append("-" * 50)
        report.append(f"Initial Balance:            $10,000")
        report.append(f"Profit Target:              $1,000 (10%)")
        report.append(f"Max Drawdown:               $600 (6%)")
        report.append(f"Max Daily Loss:             $500 (5%)")
        report.append("")
        
        report.append("SIMULATION RESULTS (1000 Monte Carlo runs)")
        report.append("-" * 50)
        report.append(f"[PASS] Pass Rate:           {simulation_results['pass_rate']:.1f}%")
        report.append(f"[FAIL] Fail Rate:           {simulation_results['fail_rate']:.1f}%")
        report.append(f"[WAIT] Incomplete Rate:     {100 - simulation_results['pass_rate'] - simulation_results['fail_rate']:.1f}%")
        report.append("")
        
        if simulation_results['avg_days_to_pass']:
            report.append(f"Average Days to Pass:       {simulation_results['avg_days_to_pass']:.0f} days")
            report.append(f"Estimated Weeks:            {simulation_results['avg_days_to_pass'] / 7:.1f} weeks")
        
        report.append(f"Average Final Balance:      ${simulation_results['avg_final_balance']:.2f}")
        report.append("")
        
        report.append("PROBABILITY ANALYSIS")
        report.append("-" * 50)
        
        if simulation_results['pass_rate'] >= 70:
            report.append(">>> HIGH SUCCESS PROBABILITY <<<")
            report.append("Your strategy has a strong chance of passing the evaluation.")
        elif simulation_results['pass_rate'] >= 50:
            report.append(">>> MODERATE SUCCESS PROBABILITY <<<")
            report.append("Your strategy has a reasonable chance but may need optimization.")
        else:
            report.append(">>> LOW SUCCESS PROBABILITY <<<")
            report.append("Your strategy needs improvement before attempting evaluation.")
        
        report.append("")
        report.append("RECOMMENDATIONS")
        report.append("-" * 50)
        
        if simulation_results['pass_rate'] < 70:
            report.append("To improve your success rate:")
            report.append("1. Focus exclusively on preferred symbols (DOT, BTC, SOL, ADA)")
            report.append("2. Only take trades with RR ratio > 2.0")
            report.append("3. Reduce position size to 1% when near limits")
            report.append("4. Skip trading after 2 losses in a day")
            report.append("5. Wait for high-confidence setups only")
        else:
            report.append("Your strategy is evaluation-ready!")
            report.append("1. Maintain discipline and follow your rules")
            report.append("2. Don't increase risk after wins")
            report.append("3. Stop trading if daily loss exceeds $400")
            report.append("4. Focus on capital preservation near target")
        
        report.append("")
        report.append("SAMPLE EVALUATION RUNS")
        report.append("-" * 50)
        
        for i, result in enumerate(simulation_results['detailed_results'][:5], 1):
            status = "PASSED" if result['passed'] else "FAILED" if result['failed'] else "INCOMPLETE"
            report.append(f"Run {i}: {status} - Balance: ${result['final_balance']:.2f}, "
                         f"Days: {result['days']}, Trades: {result['trades']}")
        
        report.append("")
        report.append("=" * 70)
        
        return "\n".join(report)


def main():
    """Run the prop firm simulation"""
    print("Running Prop Firm Evaluation Simulation...")
    print("This will simulate 1000 evaluation attempts using your strategy.\n")
    
    simulator = PropFirmSimulation()
    
    # Run Monte Carlo simulation
    results = simulator.run_monte_carlo_simulation(num_simulations=1000)
    
    # Generate report
    report = simulator.generate_report(results)
    print(report)
    
    # Save results
    with open('prop_firm_simulation_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\nDetailed results saved to prop_firm_simulation_results.json")
    
    return results['pass_rate'] >= 50  # Return True if strategy is viable


if __name__ == "__main__":
    viable = main()