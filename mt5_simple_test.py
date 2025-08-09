"""
Simple MT5 Connection Test
"""

import MetaTrader5 as mt5
import sys

print("MT5 Simple Connection Test")
print("="*40)

# Method 1: Direct initialization
print("\nAttempt 1: Direct initialization...")
if mt5.initialize():
    print("[OK] MT5 initialized")
    
    # Get terminal info
    terminal_info = mt5.terminal_info()
    if terminal_info:
        print(f"Terminal: {terminal_info.name}")
        print(f"Path: {terminal_info.path}")
        print(f"Data path: {terminal_info.data_path}")
    
    # Get account info
    account = mt5.account_info()
    if account:
        print(f"\nAccount connected:")
        print(f"  Login: {account.login}")
        print(f"  Server: {account.server}")
        print(f"  Balance: ${account.balance:.2f}")
        print(f"  Company: {account.company}")
        
        # Check if this is the right account
        if account.login == 3062432:
            print("\n[SUCCESS] This is your PlexyTrade account!")
            
            # Test symbol access
            print("\nTesting symbol access...")
            for symbol in ['XAUUSD', 'EURUSD', 'GBPUSD', 'BTCUSD']:
                if mt5.symbol_select(symbol, True):
                    tick = mt5.symbol_info_tick(symbol)
                    if tick:
                        print(f"  {symbol}: Bid={tick.bid:.5f}, Ask={tick.ask:.5f}")
                    else:
                        print(f"  {symbol}: No tick data")
                else:
                    print(f"  {symbol}: Not available")
        else:
            print(f"\n[WARNING] Wrong account. Expected 3062432, got {account.login}")
            print("\nAttempting to login to correct account...")
            
            # Try to login
            if mt5.login(3062432, password="d07uL40Z%I", server="PlexyTrade-Server01"):
                print("[OK] Logged in to PlexyTrade")
                account = mt5.account_info()
                if account:
                    print(f"  Balance: ${account.balance:.2f}")
            else:
                error = mt5.last_error()
                print(f"[ERROR] Login failed: {error}")
    else:
        print("[ERROR] No account info available")
else:
    error = mt5.last_error()
    print(f"[ERROR] MT5 initialization failed: {error}")
    
    if error[0] == -10005:
        print("""
        IPC Timeout Error - Solutions:
        1. Make sure MT5 is running
        2. Login to your account in MT5 manually
        3. Try closing other MT5 instances
        4. Run this script as Administrator
        """)

# Cleanup
mt5.shutdown()
print("\nTest complete.")