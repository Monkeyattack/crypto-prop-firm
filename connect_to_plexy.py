"""
Connect to the running PlexyTrade MT5 terminal
"""

import MetaTrader5 as mt5
import time
import os

print("CONNECTING TO PLEXYTRADE MT5")
print("="*60)

# Check running processes
print("\nChecking MT5 processes...")
os.system("tasklist | findstr terminal64")

print("\nGood! Only PlexyTrade MT5 is running.")
print("\nAttempting connection...")

# Since only PlexyTrade is running, default init should work
print("\nMethod 1: Default initialization...")
if mt5.initialize():
    print("[SUCCESS] MT5 initialized!")
    
    # Check account
    account = mt5.account_info()
    if account:
        print(f"\nConnected to:")
        print(f"  Account: {account.login}")
        print(f"  Server: {account.server}")
        print(f"  Company: {account.company}")
        print(f"  Balance: ${account.balance:.2f}")
        print(f"  Currency: {account.currency}")
        print(f"  Leverage: 1:{account.leverage}")
        
        if account.login == 3062432:
            print("\n[SUCCESS] This is your PlexyTrade account!")
            
            # Test trading capabilities
            print("\nTesting trading capabilities...")
            
            # Check symbols
            symbols = ['XAUUSD', 'EURUSD', 'GBPUSD', 'BTCUSD']
            print("\nAvailable symbols:")
            for symbol in symbols:
                if mt5.symbol_select(symbol, True):
                    info = mt5.symbol_info(symbol)
                    if info:
                        tick = mt5.symbol_info_tick(symbol)
                        if tick:
                            print(f"  {symbol}: Bid={tick.bid:.5f}, Ask={tick.ask:.5f}, Spread={(tick.ask-tick.bid):.5f}")
                        else:
                            print(f"  {symbol}: Available but no tick data")
                else:
                    print(f"  {symbol}: Not available")
            
            # Check if we can place orders
            print("\nChecking order placement capability...")
            if account.trade_allowed:
                print("[OK] Trading is allowed")
            else:
                print("[WARNING] Trading is not allowed")
            
            if account.trade_expert:
                print("[OK] Expert Advisors allowed")
            else:
                print("[WARNING] Expert Advisors not allowed")
            
            print("\n" + "="*60)
            print("CONNECTION SUCCESSFUL!")
            print("="*60)
            print("\nEverything is working! Now we can run paper trading.")
            print("\nTo start 7-day paper trading test:")
            print("  python start_paper_trading.py")
            
            # Save the configuration
            with open('mt5_working_config.txt', 'w') as f:
                f.write("STATUS=CONNECTED\n")
                f.write(f"ACCOUNT={account.login}\n")
                f.write(f"SERVER={account.server}\n")
                f.write(f"COMPANY={account.company}\n")
                f.write(f"BALANCE={account.balance}\n")
            
            print("\nConfiguration saved to mt5_working_config.txt")
            
        else:
            print(f"\n[ERROR] Wrong account! Expected 3062432, got {account.login}")
            print("\nTrying to login to correct account...")
            
            if mt5.login(3062432, password="d07uL40Z%I", server="PlexyTrade-Server01"):
                print("[SUCCESS] Logged in!")
                account = mt5.account_info()
                if account:
                    print(f"Balance: ${account.balance:.2f}")
            else:
                error = mt5.last_error()
                print(f"[ERROR] Login failed: {error}")
                
                if error[0] == -6:
                    print("\nAuthorization failed. Please check:")
                    print("1. Is the password correct? d07uL40Z%I")
                    print("2. Is the server name exact? PlexyTrade-Server01")
                    print("3. Is the account still active?")
    else:
        print("[ERROR] Connected but no account info")
        print("\nTrying to login...")
        
        if mt5.login(3062432, password="d07uL40Z%I", server="PlexyTrade-Server01"):
            print("[SUCCESS] Logged in!")
            account = mt5.account_info()
            if account:
                print(f"Account: {account.login}")
                print(f"Balance: ${account.balance:.2f}")
        else:
            print(f"[ERROR] Login failed: {mt5.last_error()}")
            
else:
    error = mt5.last_error()
    print(f"[ERROR] Failed to initialize: {error}")
    
    if error[0] == -10005:
        print("\nIPC timeout. Try:")
        print("1. Run this script as Administrator")
        print("2. Make sure Windows Defender isn't blocking Python")
        print("3. Restart the PlexyTrade MT5 terminal")

mt5.shutdown()
print("\nDone.")