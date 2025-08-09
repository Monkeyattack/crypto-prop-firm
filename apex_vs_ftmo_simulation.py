"""
Apex vs FTMO Prop Firm Simulation
Compares real returns after costs for US vs Non-US traders
"""

import random
import statistics
from typing import Dict, List, Tuple

class PropFirmSimulator:
    """Simulate prop firm returns with real costs"""
    
    def __init__(self):
        # Signal characteristics (Gold/FX)
        self.avg_rr = 2.8
        self.win_rate = 0.58  # 58% win rate typical for Gold
        self.signals_per_month = 20  # Conservative estimate
        
        # Apex Trader Funding (US)
        self.apex = {
            'name': 'Apex Trader Funding',
            'eval_cost': 167,  # Monthly for $50k
            'account_size': 50000,
            'profit_target': 3000,  # 6%
            'max_drawdown': 2500,  # 5%
            'profit_split': 0.90,  # 90% to trader
            'monthly_fee': 0,  # No fee after funded
            'reset_cost': 80,  # If failed
            'min_trading_days': 7,
            'scaling_available': True,
            'max_contracts': 4,  # For $50k account
            'gold_tick_value': 10,  # $10 per tick
            'currency': 'USD'
        }
        
        # FTMO (Non-US)
        self.ftmo = {
            'name': 'FTMO',
            'eval_cost': 540,  # One-time for $100k
            'account_size': 100000,
            'profit_target': 10000,  # 10% for step 1
            'verification_target': 5000,  # 5% for step 2
            'max_daily_loss': 5000,  # 5%
            'max_drawdown': 10000,  # 10%
            'profit_split': 0.80,  # 80% initially, scales to 90%
            'monthly_fee': 0,
            'reset_cost': 0,  # Free retry
            'min_trading_days': 10,
            'scaling_available': True,
            'currency': 'USD'
        }
    
    def simulate_evaluation(self, firm: Dict, months: int = 12) -> Dict:
        """Simulate evaluation and funded trading over X months"""
        
        results = {
            'firm': firm['name'],
            'total_cost': 0,
            'months_to_pass': 0,
            'months_funded': 0,
            'gross_profits': 0,
            'net_profits': 0,
            'failed_evaluations': 0,
            'account_blown': False,
            'monthly_results': []
        }
        
        passed_evaluation = False
        current_month = 1
        eval_balance = firm['account_size']
        funded_balance = firm['account_size']
        
        while current_month <= months:
            month_data = {
                'month': current_month,
                'status': 'evaluation' if not passed_evaluation else 'funded',
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'gross_pnl': 0,
                'net_pnl': 0,
                'balance': eval_balance if not passed_evaluation else funded_balance
            }
            
            # Pay evaluation cost if starting or resetting
            if not passed_evaluation and current_month == 1:
                results['total_cost'] += firm['eval_cost']
                month_data['cost'] = firm['eval_cost']
            
            # Simulate month of trading
            for _ in range(self.signals_per_month):
                # Risk 1% per trade
                risk_amount = month_data['balance'] * 0.01
                
                # Simulate trade outcome
                if random.random() < self.win_rate:
                    # Winner
                    profit = risk_amount * self.avg_rr
                    month_data['wins'] += 1
                else:
                    # Loser
                    profit = -risk_amount
                    month_data['losses'] += 1
                
                month_data['trades'] += 1
                month_data['gross_pnl'] += profit
                month_data['balance'] += profit
                
                # Check drawdown limits
                if not passed_evaluation:
                    if eval_balance - month_data['balance'] > firm.get('max_drawdown', firm['account_size']):
                        # Failed evaluation
                        results['failed_evaluations'] += 1
                        
                        # Reset with Apex
                        if firm['name'] == 'Apex Trader Funding':
                            results['total_cost'] += firm['reset_cost']
                            eval_balance = firm['account_size']
                            month_data['balance'] = eval_balance
                            month_data['failed'] = True
                        break
            
            # Check if passed evaluation
            if not passed_evaluation:
                profit_made = month_data['balance'] - firm['account_size']
                
                # FTMO has two steps
                if firm['name'] == 'FTMO':
                    if profit_made >= firm['profit_target']:
                        # Passed step 1, now verification
                        if profit_made >= firm['verification_target']:
                            passed_evaluation = True
                            results['months_to_pass'] = current_month
                else:
                    # Apex - single step
                    if profit_made >= firm['profit_target']:
                        passed_evaluation = True
                        results['months_to_pass'] = current_month
                        funded_balance = firm['account_size']
            
            # Calculate net profit if funded
            if passed_evaluation:
                results['months_funded'] += 1
                trader_share = month_data['gross_pnl'] * firm['profit_split']
                month_data['net_pnl'] = trader_share - firm.get('monthly_fee', 0)
                results['gross_profits'] += month_data['gross_pnl']
                results['net_profits'] += month_data['net_pnl']
            
            results['monthly_results'].append(month_data)
            current_month += 1
        
        return results
    
    def run_comparison(self, simulations: int = 100) -> Dict:
        """Run multiple simulations and compare"""
        
        apex_results = []
        ftmo_results = []
        
        for _ in range(simulations):
            apex_results.append(self.simulate_evaluation(self.apex))
            ftmo_results.append(self.simulate_evaluation(self.ftmo))
        
        # Calculate statistics
        def get_stats(results_list):
            return {
                'avg_months_to_pass': statistics.mean([r['months_to_pass'] for r in results_list if r['months_to_pass'] > 0]),
                'pass_rate': len([r for r in results_list if r['months_to_pass'] > 0]) / len(results_list) * 100,
                'avg_total_cost': statistics.mean([r['total_cost'] for r in results_list]),
                'avg_net_profit': statistics.mean([r['net_profits'] for r in results_list]),
                'avg_roi': statistics.mean([(r['net_profits'] - r['total_cost']) / r['total_cost'] * 100 if r['total_cost'] > 0 else 0 for r in results_list]),
                'best_case': max([r['net_profits'] - r['total_cost'] for r in results_list]),
                'worst_case': min([r['net_profits'] - r['total_cost'] for r in results_list]),
                'avg_funded_months': statistics.mean([r['months_funded'] for r in results_list])
            }
        
        apex_stats = get_stats(apex_results)
        ftmo_stats = get_stats(ftmo_results)
        
        return {
            'apex': apex_stats,
            'ftmo': ftmo_stats,
            'apex_results': apex_results,
            'ftmo_results': ftmo_results
        }
    
    def calculate_breakeven_analysis(self) -> Dict:
        """Calculate how long to break even on costs"""
        
        # Apex monthly costs
        apex_monthly_cost = self.apex['eval_cost']  # $167/month during eval
        
        # FTMO one-time cost
        ftmo_onetime_cost = self.ftmo['eval_cost']  # $540 one-time
        
        # Expected monthly profit (after passing)
        trades_per_month = self.signals_per_month
        win_trades = trades_per_month * self.win_rate
        loss_trades = trades_per_month * (1 - self.win_rate)
        
        # Apex expected (1% risk on $50k)
        apex_avg_trade = 500  # $500 risk per trade
        apex_monthly_gross = (win_trades * apex_avg_trade * self.avg_rr) - (loss_trades * apex_avg_trade)
        apex_monthly_net = apex_monthly_gross * self.apex['profit_split']
        
        # FTMO expected (1% risk on $100k)
        ftmo_avg_trade = 1000  # $1000 risk per trade
        ftmo_monthly_gross = (win_trades * ftmo_avg_trade * self.avg_rr) - (loss_trades * ftmo_avg_trade)
        ftmo_monthly_net = ftmo_monthly_gross * self.ftmo['profit_split']
        
        return {
            'apex': {
                'monthly_cost': apex_monthly_cost,
                'expected_monthly_profit': apex_monthly_net,
                'months_to_breakeven': apex_monthly_cost / apex_monthly_net if apex_monthly_net > 0 else float('inf'),
                'profit_after_costs_monthly': apex_monthly_net - apex_monthly_cost
            },
            'ftmo': {
                'upfront_cost': ftmo_onetime_cost,
                'expected_monthly_profit': ftmo_monthly_net,
                'months_to_breakeven': ftmo_onetime_cost / ftmo_monthly_net if ftmo_monthly_net > 0 else float('inf'),
                'profit_after_costs_monthly': ftmo_monthly_net  # No monthly cost after evaluation
            }
        }
    
    def generate_report(self):
        """Generate comprehensive comparison report"""
        
        print("="*80)
        print("APEX vs FTMO PROP FIRM SIMULATION")
        print("Based on Gold/FX Signals (R:R 2.8, Win Rate 58%)")
        print("="*80)
        
        # Run simulations
        comparison = self.run_comparison(simulations=1000)
        breakeven = self.calculate_breakeven_analysis()
        
        print("\nEVALUATION PHASE (1000 Simulations)")
        print("-"*80)
        print(f"{'Metric':<30} {'APEX (US)':<25} {'FTMO (Non-US)':<25}")
        print("-"*80)
        
        print(f"{'Account Size:':<30} ${self.apex['account_size']:,} {'':<14} ${self.ftmo['account_size']:,}")
        print(f"{'Evaluation Cost:':<30} ${self.apex['eval_cost']}/month {'':<11} ${self.ftmo['eval_cost']} one-time")
        print(f"{'Profit Target:':<30} ${self.apex['profit_target']:,} (6%) {'':<11} ${self.ftmo['profit_target']:,} (10%)")
        print(f"{'Pass Rate:':<30} {comparison['apex']['pass_rate']:.1f}% {'':<17} {comparison['ftmo']['pass_rate']:.1f}%")
        print(f"{'Avg Months to Pass:':<30} {comparison['apex']['avg_months_to_pass']:.1f} {'':<19} {comparison['ftmo']['avg_months_to_pass']:.1f}")
        print(f"{'Avg Total Cost to Pass:':<30} ${comparison['apex']['avg_total_cost']:.0f} {'':<17} ${comparison['ftmo']['avg_total_cost']:.0f}")
        
        print("\nFUNDED ACCOUNT PERFORMANCE (12 Month Period)")
        print("-"*80)
        print(f"{'Profit Split:':<30} {self.apex['profit_split']*100:.0f}% {'':<20} {self.ftmo['profit_split']*100:.0f}%")
        print(f"{'Avg Funded Months:':<30} {comparison['apex']['avg_funded_months']:.1f} {'':<19} {comparison['ftmo']['avg_funded_months']:.1f}")
        print(f"{'Avg Net Profit:':<30} ${comparison['apex']['avg_net_profit']:,.0f} {'':<16} ${comparison['ftmo']['avg_net_profit']:,.0f}")
        print(f"{'ROI on Investment:':<30} {comparison['apex']['avg_roi']:.0f}% {'':<20} {comparison['ftmo']['avg_roi']:.0f}%")
        print(f"{'Best Case (12mo):':<30} ${comparison['apex']['best_case']:,.0f} {'':<16} ${comparison['ftmo']['best_case']:,.0f}")
        print(f"{'Worst Case (12mo):':<30} ${comparison['apex']['worst_case']:,.0f} {'':<16} ${comparison['ftmo']['worst_case']:,.0f}")
        
        print("\nBREAKEVEN ANALYSIS")
        print("-"*80)
        print(f"{'Expected Monthly Profit:':<30} ${breakeven['apex']['expected_monthly_profit']:,.0f} {'':<16} ${breakeven['ftmo']['expected_monthly_profit']:,.0f}")
        print(f"{'Monthly Costs:':<30} ${breakeven['apex']['monthly_cost']:.0f} {'':<17} $0 (after eval)")
        print(f"{'Months to Breakeven:':<30} {breakeven['apex']['months_to_breakeven']:.1f} {'':<19} {breakeven['ftmo']['months_to_breakeven']:.1f}")
        print(f"{'Net Monthly (after costs):':<30} ${breakeven['apex']['profit_after_costs_monthly']:,.0f} {'':<16} ${breakeven['ftmo']['profit_after_costs_monthly']:,.0f}")
        
        print("\nRECOMMENDATIONS")
        print("-"*80)
        
        # Calculate which is better
        apex_12mo_expected = (comparison['apex']['avg_net_profit'] - comparison['apex']['avg_total_cost'])
        ftmo_12mo_expected = (comparison['ftmo']['avg_net_profit'] - comparison['ftmo']['avg_total_cost'])
        
        if apex_12mo_expected > ftmo_12mo_expected:
            print(">>> APEX is BETTER for US traders")
            difference = apex_12mo_expected - ftmo_12mo_expected
            print(f"   Expected advantage: ${difference:,.0f} over 12 months")
        else:
            print(">>> FTMO would be BETTER (if US traders were allowed)")
            difference = ftmo_12mo_expected - apex_12mo_expected
            print(f"   FTMO advantage: ${difference:,.0f} over 12 months")
            print("   WARNING: But FTMO doesn't accept US traders!")
        
        print("\nKEY INSIGHTS:")
        print("* Apex has lower evaluation cost but smaller account")
        print("* FTMO's larger account size = larger absolute profits")
        print("* Apex's 90% split vs FTMO's 80% partially offsets smaller account")
        print("* Both are profitable with Gold/FX 2.8 R:R signals")
        print(f"* Your signals would generate ~${breakeven['apex']['expected_monthly_profit']:,.0f}/mo on Apex")
        
        print("\nCRITICAL NOTE:")
        print("With crypto signals (0.68 R:R), BOTH would lose money!")
        print("The switch to Gold/FX is essential for profitability")
        
        print("\n" + "="*80)
        
        return comparison

if __name__ == "__main__":
    simulator = PropFirmSimulator()
    simulator.generate_report()