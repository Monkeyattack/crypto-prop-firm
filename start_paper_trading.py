"""
Start Paper Trading with PlexyTrade Account
Direct launch without input prompts
"""

import asyncio
from mt5_paper_trader import MT5PaperTrader

print("="*70)
print("STARTING 7-DAY PAPER TRADING VERIFICATION")
print("="*70)
print()
print("Account: 3062432")
print("Server: PlexyTrade-Server01")
print("Balance: $50,000")
print("Duration: 7 days")
print()
print("This will:")
print("- Read signals from your database")
print("- Execute real trades on PlexyTrade demo")
print("- Track FTMO ($100k) and Breakout ($10k) rules")
print("- Send daily reports at 9 PM")
print("- Prove if strategy passes prop firm challenges")
print()
print("="*70)

# Initialize with your credentials
trader = MT5PaperTrader(
    account=3062432,
    password="d07uL40Z%I",
    server="PlexyTrade-Server01"
)

if trader.connected:
    print("[OK] Connected to PlexyTrade MT5")
    print("[OK] Paper trading verification started")
    print("[OK] Will run for 7 days automatically")
    print()
    print("Check back in 7 days for results, or watch for daily reports.")
    print("Press Ctrl+C to stop.")
    print()
    print("Starting main trading loop...")
    print("="*70)
    
    # Run the paper trading system
    asyncio.run(trader.run_paper_trading())
else:
    print("[ERROR] Failed to connect to MT5")
    print("Make sure PlexyTrade MT5 is running and logged in.")
