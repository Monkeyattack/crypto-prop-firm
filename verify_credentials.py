"""
Verify PlexyTrade Login Credentials
Since authentication failed, let's check what's wrong with the login details
"""

import MetaTrader5 as mt5
import time

print("VERIFYING PLEXYTRADE CREDENTIALS")
print("="*60)

# Your provided credentials
ACCOUNT = 3062432
PASSWORD = "d07uL40Z%I"
SERVER = "PlexyTrade-Server01"

print(f"Account: {ACCOUNT}")
print(f"Password: {PASSWORD}")
print(f"Server: {SERVER}")
print("="*60)

# Initialize MT5
print("\nInitializing MT5...")
if not mt5.initialize():
    print(f"[ERROR] Failed to initialize: {mt5.last_error()}")
    exit(1)

print("[OK] MT5 initialized successfully")

# Check what's currently logged in
account_info = mt5.account_info()
if account_info:
    print(f"\nCurrently logged into:")
    print(f"  Account: {account_info.login}")
    print(f"  Server: {account_info.server}")
    print(f"  Company: {account_info.company}")
    print(f"  Balance: ${account_info.balance:.2f}")
    
    if account_info.login == ACCOUNT:
        print(f"\n[SUCCESS] Already logged into the correct account!")
        print(f"The credentials work. The issue was the connection, not authentication.")
        
        # Test trading capabilities
        print(f"\nTesting account capabilities...")
        print(f"  Trade allowed: {account_info.trade_allowed}")
        print(f"  Expert advisors: {account_info.trade_expert}")
        print(f"  Account type: {account_info.margin_so_mode}")
        
        # Test symbols
        print(f"\nTesting symbols...")
        for symbol in ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY']:
            if mt5.symbol_select(symbol, True):
                info = mt5.symbol_info(symbol)
                if info:
                    tick = mt5.symbol_info_tick(symbol)
                    if tick:
                        print(f"  {symbol}: Available, Bid={tick.bid:.5f}, Ask={tick.ask:.5f}")
                    else:
                        print(f"  {symbol}: Available but no price data")
                else:
                    print(f"  {symbol}: Symbol info not available")
            else:
                print(f"  {symbol}: Not available")
        
        print(f"\n" + "="*60)
        print(f"CREDENTIALS ARE CORRECT!")
        print(f"="*60)
        print(f"\nThe MT5 connection is working now.")
        print(f"You can proceed with paper trading.")
        
        # Save working config
        with open('working_mt5_config.py', 'w') as f:
            f.write(f"# Working MT5 Configuration\n")
            f.write(f"LOGIN = {ACCOUNT}\n")
            f.write(f"PASSWORD = '{PASSWORD}'\n")
            f.write(f"SERVER = '{account_info.server}'\n")
            f.write(f"COMPANY = '{account_info.company}'\n")
            f.write(f"BALANCE = {account_info.balance}\n")
        
        print(f"Configuration saved to working_mt5_config.py")
        
    else:
        print(f"\n[INFO] Different account logged in. Trying to switch...")
        
        # Try exact login
        print(f"\nAttempting login with provided credentials...")
        result = mt5.login(ACCOUNT, password=PASSWORD, server=SERVER)
        
        if result:
            print(f"[SUCCESS] Logged in successfully!")
            
            # Get updated account info
            account_info = mt5.account_info()
            if account_info:
                print(f"  Account: {account_info.login}")
                print(f"  Server: {account_info.server}")
                print(f"  Balance: ${account_info.balance:.2f}")
        else:
            error = mt5.last_error()
            print(f"[ERROR] Login failed: {error}")
            
            if error[0] == -6:
                print(f"\nAuthentication failed. Possible issues:")
                print(f"1. Password case sensitivity: '{PASSWORD}'")
                print(f"2. Server name case sensitivity: '{SERVER}'")
                print(f"3. Account number: {ACCOUNT}")
                print(f"4. Account may be expired or locked")
                print(f"5. Wrong broker - this might not be PlexyTrade MT5")
                
                # Try variations
                print(f"\nTrying server name variations...")
                server_variations = [
                    "PlexyTrade-Server01",
                    "plexytrade-server01", 
                    "PlexyTrade-Server",
                    "PlexyTradeServer01",
                    "Plexy-Server01",
                    "PlexyTrade-Demo",
                    "PlexyTrade-Live"
                ]
                
                for server_var in server_variations:
                    print(f"  Trying '{server_var}'... ", end="")
                    if mt5.login(ACCOUNT, password=PASSWORD, server=server_var):
                        print(f"SUCCESS!")
                        account_info = mt5.account_info()
                        if account_info:
                            print(f"    Server: {account_info.server}")
                            print(f"    Balance: ${account_info.balance:.2f}")
                        break
                    else:
                        print(f"Failed")
                    time.sleep(1)
            
            elif error[0] == -8:
                print(f"\nServer not found. The server name '{SERVER}' doesn't exist.")
                print(f"Check the exact server name in your MT5.")
            
            elif error[0] == -10:
                print(f"\nAccount disabled or expired.")
else:
    print(f"\n[INFO] No account currently logged in")
    
    # Try to login
    print(f"\nAttempting fresh login...")
    result = mt5.login(ACCOUNT, password=PASSWORD, server=SERVER)
    
    if result:
        print(f"[SUCCESS] Logged in!")
        account_info = mt5.account_info()
        if account_info:
            print(f"  Account: {account_info.login}")
            print(f"  Server: {account_info.server}")
            print(f"  Balance: ${account_info.balance:.2f}")
    else:
        error = mt5.last_error()
        print(f"[ERROR] Login failed: {error}")

print(f"\n" + "="*60)
print(f"DIAGNOSTIC COMPLETE")
print(f"="*60)

# Get terminal info
terminal_info = mt5.terminal_info()
if terminal_info:
    print(f"\nTerminal Information:")
    print(f"  Name: {terminal_info.name}")
    print(f"  Company: {terminal_info.company}")
    print(f"  Path: {terminal_info.path}")
    print(f"  Version: {terminal_info.version}")
    
    # This tells us which MT5 Python connected to
    if "PlexyTrade" in terminal_info.path or "Plexy" in terminal_info.company:
        print(f"\n[OK] Connected to PlexyTrade MT5")
    else:
        print(f"\n[WARNING] Connected to different MT5: {terminal_info.company}")
        print(f"This might explain the authentication failure.")

mt5.shutdown()
print(f"\nDone.")