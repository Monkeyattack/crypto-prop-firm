"""Monitor Paper Trading Progress"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List

def get_paper_trading_stats():
    """Get current paper trading statistics"""
    
    conn = sqlite3.connect('paper_trades.db')
    cursor = conn.cursor()
    
    # Get all trades
    cursor.execute("""
        SELECT * FROM paper_trades
        ORDER BY open_time DESC
    """)
    trades = cursor.fetchall()
    
    # Calculate statistics
    total_trades = len(trades)
    open_trades = 0
    closed_trades = 0
    winning_trades = 0
    losing_trades = 0
    total_pnl = 0.0
    ftmo_pnl = 0.0
    breakout_pnl = 0.0
    
    for trade in trades:
        if trade[15] is None:  # close_time
            open_trades += 1
        else:
            closed_trades += 1
            pnl = trade[16] if trade[16] else 0  # pnl
            total_pnl += pnl
            
            # Track by prop firm
            ftmo_pnl += pnl * (100000 / 50000)  # Scale to FTMO balance
            breakout_pnl += pnl * (10000 / 50000)  # Scale to Breakout balance
            
            if pnl > 0:
                winning_trades += 1
            elif pnl < 0:
                losing_trades += 1
    
    # Get prop firm status
    cursor.execute("""
        SELECT * FROM prop_firm_tracking
        ORDER BY date DESC
        LIMIT 1
    """)
    prop_status = cursor.fetchone()
    
    conn.close()
    
    # Calculate metrics
    win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0
    
    # Print report
    print("=" * 70)
    print("PAPER TRADING MONITOR")
    print("=" * 70)
    print(f"Started: {datetime.now() - timedelta(days=1)}")
    print(f"Current: {datetime.now()}")
    print()
    
    print("TRADE STATISTICS:")
    print(f"  Total Trades: {total_trades}")
    print(f"  Open: {open_trades}")
    print(f"  Closed: {closed_trades}")
    print(f"  Winners: {winning_trades}")
    print(f"  Losers: {losing_trades}")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Total P&L: ${total_pnl:.2f}")
    print()
    
    print("PROP FIRM PROGRESS:")
    
    # FTMO Progress
    ftmo_balance = 100000 + ftmo_pnl
    ftmo_profit_pct = (ftmo_pnl / 100000) * 100
    ftmo_target = 10000  # 10% of $100k
    ftmo_progress = (ftmo_pnl / ftmo_target) * 100 if ftmo_pnl > 0 else 0
    
    print(f"  FTMO ($100k Challenge):")
    print(f"    Balance: ${ftmo_balance:,.2f}")
    print(f"    P&L: ${ftmo_pnl:,.2f} ({ftmo_profit_pct:.2f}%)")
    print(f"    Target: $10,000 (10%)")
    print(f"    Progress: {ftmo_progress:.1f}%")
    
    if prop_status and prop_status[6]:  # ftmo_max_daily_loss
        print(f"    Max Daily Loss Used: ${abs(prop_status[6]):.2f} / $5,000")
    if prop_status and prop_status[7]:  # ftmo_max_drawdown
        print(f"    Max Drawdown Used: ${abs(prop_status[7]):.2f} / $10,000")
    
    print()
    
    # Breakout Prop Progress
    breakout_balance = 10000 + breakout_pnl
    breakout_profit_pct = (breakout_pnl / 10000) * 100
    breakout_target = 1000  # 10% of $10k
    breakout_progress = (breakout_pnl / breakout_target) * 100 if breakout_pnl > 0 else 0
    
    print(f"  Breakout Prop ($10k One-Step):")
    print(f"    Balance: ${breakout_balance:,.2f}")
    print(f"    P&L: ${breakout_pnl:,.2f} ({breakout_profit_pct:.2f}%)")
    print(f"    Target: $1,000 (10%)")
    print(f"    Progress: {breakout_progress:.1f}%")
    
    if prop_status and prop_status[11]:  # breakout_max_daily_loss
        print(f"    Max Daily Loss Used: ${abs(prop_status[11]):.2f} / $500")
    if prop_status and prop_status[12]:  # breakout_max_drawdown
        print(f"    Max Drawdown Used: ${abs(prop_status[12]):.2f} / $600")
    
    print()
    
    # Show recent trades
    print("RECENT TRADES:")
    cursor = sqlite3.connect('paper_trades.db').cursor()
    cursor.execute("""
        SELECT symbol, side, entry_price, risk_reward, pnl, open_time
        FROM paper_trades
        ORDER BY open_time DESC
        LIMIT 5
    """)
    recent = cursor.fetchall()
    
    if recent:
        for trade in recent:
            symbol, side, entry, rr, pnl, open_time = trade
            pnl_str = f"${pnl:.2f}" if pnl else "OPEN"
            print(f"  {open_time[:16]} | {symbol:8} | {side:4} | R:R {rr:.1f} | {pnl_str:>10}")
    else:
        print("  No trades yet")
    
    print()
    print("=" * 70)
    
    # Check for achievements
    if ftmo_progress >= 100:
        print("!!! FTMO CHALLENGE PASSED !!!")
    if breakout_progress >= 100:
        print("!!! BREAKOUT PROP CHALLENGE PASSED !!!")
    
    return {
        'total_trades': total_trades,
        'open_trades': open_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'ftmo_progress': ftmo_progress,
        'breakout_progress': breakout_progress
    }

if __name__ == "__main__":
    stats = get_paper_trading_stats()
    
    # Check if still running
    import subprocess
    try:
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                              capture_output=True, text=True)
        if 'start_paper_trading' in result.stdout or 'mt5_paper_trader' in result.stdout:
            print("\nSystem Status: RUNNING")
        else:
            print("\nSystem Status: NOT RUNNING - Please restart with: python start_paper_trading.py")
    except:
        pass