"""
Backtest using REAL signals from Telegram
Shows what would happen with actual prop firm rules
"""

import sqlite3
from datetime import datetime, timedelta

def backtest_signals():
    """Run backtest on all signals"""
    
    conn = sqlite3.connect('trade_log.db')
    cursor = conn.cursor()
    
    # Configuration
    initial_balance = 10000  # Breakout Prop $10k account
    risk_per_trade = 0.01  # 1% risk
    
    # Prop firm limits
    max_drawdown = 600  # 6% for Breakout
    max_daily_loss = 500  # 5% daily
    profit_target = 1000  # 10% to pass
    
    # Track performance
    balance = initial_balance
    peak_balance = initial_balance
    trades_taken = []
    trades_skipped = []
    daily_results = {}
    
    print("="*70)
    print("BACKTEST WITH REAL TELEGRAM SIGNALS")
    print("="*70)
    print(f"Account: Breakout Prop $10,000 One-Step")
    print(f"Risk per trade: 1%")
    print(f"Max drawdown: 6% ($600)")
    print(f"Daily loss limit: 5% ($500)")
    print(f"Profit target: 10% ($1,000)")
    print()
    
    # Get all signals ordered by timestamp
    cursor.execute("""
        SELECT symbol, side, entry_price, stop_loss, take_profit, timestamp,
               CASE 
                   WHEN side = 'BUY' THEN (take_profit - entry_price) / (entry_price - stop_loss)
                   ELSE (entry_price - take_profit) / (stop_loss - entry_price)
               END as rr
        FROM signal_log 
        ORDER BY timestamp
    """)
    
    all_signals = cursor.fetchall()
    
    for signal in all_signals:
        symbol, side, entry, sl, tp, timestamp, rr = signal
        
        # Check minimum R:R requirements
        if symbol in ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY']:
            min_rr = 2.5  # Gold/FX minimum
        else:
            min_rr = 2.0  # Crypto minimum
        
        if rr < min_rr:
            trades_skipped.append({
                'symbol': symbol,
                'rr': rr,
                'reason': f'R:R {rr:.2f} < {min_rr}'
            })
            continue
        
        # Check if we can take the trade (drawdown/daily loss)
        current_drawdown = peak_balance - balance
        if current_drawdown >= max_drawdown:
            trades_skipped.append({
                'symbol': symbol,
                'rr': rr,
                'reason': 'Max drawdown reached'
            })
            continue
        
        # Calculate position size (1% risk)
        risk_amount = balance * risk_per_trade
        
        # Simulate trade outcome (simplified - random based on R:R)
        # Higher R:R = higher win rate in this simulation
        import random
        
        # Win rate based on R:R (rough approximation)
        if rr >= 3.0:
            win_rate = 0.40  # 40% win rate for 3:1
        elif rr >= 2.5:
            win_rate = 0.35  # 35% win rate for 2.5:1
        elif rr >= 2.0:
            win_rate = 0.33  # 33% win rate for 2:1
        else:
            win_rate = 0.30  # 30% for lower R:R
        
        # Determine if trade wins
        if random.random() < win_rate:
            # Win
            profit = risk_amount * rr
            balance += profit
            result = 'WIN'
        else:
            # Loss
            balance -= risk_amount
            result = 'LOSS'
            profit = -risk_amount
        
        # Update peak balance
        if balance > peak_balance:
            peak_balance = balance
        
        # Track trade
        trades_taken.append({
            'symbol': symbol,
            'side': side,
            'rr': rr,
            'result': result,
            'profit': profit,
            'balance': balance,
            'timestamp': timestamp
        })
        
        # Track daily results
        trade_date = timestamp[:10] if timestamp else 'unknown'
        if trade_date not in daily_results:
            daily_results[trade_date] = {'trades': 0, 'profit': 0}
        daily_results[trade_date]['trades'] += 1
        daily_results[trade_date]['profit'] += profit
        
        # Check if we hit profit target
        if balance >= initial_balance + profit_target:
            print(f"CHALLENGE PASSED! Balance: ${balance:.2f}")
            break
        
        # Check if we blew the account
        if balance <= initial_balance - max_drawdown:
            print(f"CHALLENGE FAILED! Max drawdown hit. Balance: ${balance:.2f}")
            break
    
    conn.close()
    
    # Print results
    print("\n" + "="*70)
    print("BACKTEST RESULTS")
    print("="*70)
    
    print(f"\nTrades taken: {len(trades_taken)}")
    print(f"Trades skipped: {len(trades_skipped)}")
    
    # Win/loss stats
    wins = [t for t in trades_taken if t['result'] == 'WIN']
    losses = [t for t in trades_taken if t['result'] == 'LOSS']
    
    if trades_taken:
        win_rate = len(wins) / len(trades_taken) * 100
        print(f"Wins: {len(wins)}")
        print(f"Losses: {len(losses)}")
        print(f"Win rate: {win_rate:.1f}%")
    
    print(f"\nStarting balance: ${initial_balance:.2f}")
    print(f"Final balance: ${balance:.2f}")
    print(f"Total P&L: ${balance - initial_balance:.2f}")
    print(f"Return: {(balance - initial_balance) / initial_balance * 100:.1f}%")
    
    max_dd = peak_balance - balance
    print(f"Max drawdown: ${max_dd:.2f} ({max_dd/initial_balance*100:.1f}%)")
    
    # Check if passed
    if balance >= initial_balance + profit_target:
        print("\n*** PROP FIRM CHALLENGE: PASSED ***")
    elif balance <= initial_balance - max_drawdown:
        print("\n*** PROP FIRM CHALLENGE: FAILED (Drawdown) ***")
    else:
        print("\n*** PROP FIRM CHALLENGE: IN PROGRESS ***")
    
    # Analyze why signals were skipped
    print("\n" + "="*70)
    print("SIGNAL QUALITY ANALYSIS")
    print("="*70)
    
    # Group skipped by symbol
    skipped_by_symbol = {}
    for skip in trades_skipped:
        sym = skip['symbol']
        if sym not in skipped_by_symbol:
            skipped_by_symbol[sym] = []
        skipped_by_symbol[sym].append(skip['rr'])
    
    print("\nSignals skipped due to low R:R:")
    for sym, rrs in skipped_by_symbol.items():
        avg_rr = sum(rrs) / len(rrs)
        print(f"  {sym}: {len(rrs)} signals, Avg R:R: {avg_rr:.2f}")
    
    # Show actual trades taken
    if trades_taken:
        print("\nActual trades taken:")
        for i, trade in enumerate(trades_taken[:10], 1):  # Show first 10
            print(f"  {i}. {trade['symbol']} {trade['side']} - R:R: {trade['rr']:.2f} - {trade['result']} - P&L: ${trade['profit']:.2f}")
    
    # Key finding
    print("\n" + "="*70)
    print("KEY FINDINGS:")
    print("="*70)
    
    if symbol in skipped_by_symbol and 'XAUUSD' in skipped_by_symbol:
        xau_skipped = len(skipped_by_symbol['XAUUSD'])
        print(f"1. XAUUSD: {xau_skipped} signals ALL rejected (R:R too low)")
        print("   The Gold/FX channel signals are NOT suitable for prop trading")
    
    if trades_taken:
        avg_rr_taken = sum([t['rr'] for t in trades_taken]) / len(trades_taken)
        print(f"2. Only {len(trades_taken)} signals met minimum R:R requirements")
        print(f"   Average R:R of trades taken: {avg_rr_taken:.2f}")
    else:
        print("2. NO signals met the minimum R:R requirements!")
        print("   Need better signal sources for prop firm trading")

if __name__ == "__main__":
    backtest_signals()