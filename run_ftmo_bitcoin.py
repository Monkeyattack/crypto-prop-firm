#!/usr/bin/env python3
"""
FTMO Bitcoin Trading Launcher
Starts the optimized Bitcoin trading system for FTMO challenges
"""

import sys
import os
import logging
from datetime import datetime

# Add parent directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("="*80)
    print("FTMO BITCOIN TRADING SYSTEM LAUNCHER")
    print("="*80)
    print(f"Start time: {datetime.now()}")
    print()
    print("Strategy Overview:")
    print("- Symbol: BTCUSD")
    print("- Target: 5% per trade with dynamic trailing stops")
    print("- Risk: 1% per trade")
    print("- Expected monthly return: 6.8% (from backtesting)")
    print("- Phase 1 goal: $10,000 profit in 30 days")
    print("- Phase 2 goal: $5,000 profit in 60 days")
    print()
    print("Based on analysis:")
    print("- Bitcoin available on FTMO: YES")
    print("- Leverage: 1:2")
    print("- Expected Phase 1 completion: ~15 days")
    print("- Max drawdown from backtest: 0.4%")
    print("- Win rate from backtest: 75.8%")
    print("="*80)
    print()
    
    try:
        from ftmo_bitcoin_trader import FTMOBitcoinTrader
        import asyncio
        
        print("Initializing FTMO Bitcoin Trader...")
        
        trader = FTMOBitcoinTrader(
            account=3062432,
            password="d07uL40Z%I",
            server="PlexyTrade-Server01"
        )
        
        if trader.connected:
            print("[OK] Connected to MT5 successfully")
            print("[OK] Starting FTMO Bitcoin trading loop...")
            print()
            print("Monitor the ftmo_bitcoin.log file for detailed trading activity")
            print("Press Ctrl+C to stop trading")
            print("-"*80)
            
            # Run the trading loop
            asyncio.run(trader.run_ftmo_trading())
        else:
            print("[ERROR] Failed to connect to MT5")
            print("Please check:")
            print("1. MT5 terminal is running")
            print("2. Only PlexyTrade terminal is active")
            print("3. Account credentials are correct")
            
    except KeyboardInterrupt:
        print("\n\nTrading stopped by user")
        print("Saving final statistics...")
        if 'trader' in locals():
            trader.save_daily_stats()
        print("Done.")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())