"""
Fix MT5 Connection Issues
Specific solution for PlexyTrade GOLD RAW account
"""

import MetaTrader5 as mt5
import time
import sys
import os

print("FIXING MT5 CONNECTION FOR PLEXYTRADE")
print("="*60)

# Your exact credentials
LOGIN = 3062432
PASSWORD = "d07uL40Z%I"
SERVER = "PlexyTrade-Server01"
ACCOUNT_TYPE = "GOLD RAW"

print(f"Account: {LOGIN}")
print(f"Server: {SERVER}")
print(f"Type: {ACCOUNT_TYPE}")
print("="*60)

# Step 1: Try with path specification
print("\nStep 1: Looking for MT5 installations...")

mt5_paths = [
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
    r"C:\Program Files\PlexyTrade MetaTrader 5\terminal64.exe",
    r"C:\Program Files\MetaTrader 5 - PlexyTrade\terminal64.exe",
    r"C:\Users\cmeredith\AppData\Roaming\MetaQuotes\Terminal\terminal64.exe"
]

found_path = None
for path in mt5_paths:
    if os.path.exists(path):
        print(f"Found MT5 at: {path}")
        found_path = path
        break

if not found_path:
    print("[WARNING] MT5 not found in standard locations")
    print("Trying default initialization...")

# Step 2: Initialize with timeout and retry
print("\nStep 2: Initializing MT5...")

for attempt in range(3):
    print(f"\nAttempt {attempt + 1} of 3...")
    
    # Close any existing connection
    mt5.shutdown()
    time.sleep(2)
    
    # Try to initialize
    if found_path:
        result = mt5.initialize(path=found_path, login=LOGIN, password=PASSWORD, server=SERVER, timeout=10000, portable=False)
    else:
        result = mt5.initialize(login=LOGIN, password=PASSWORD, server=SERVER, timeout=10000, portable=False)
    
    if result:
        print("[SUCCESS] MT5 initialized!")
        break
    else:
        error = mt5.last_error()
        print(f"[ERROR] Initialization failed: {error}")
        
        if error[0] == -10005:  # IPC timeout
            print("\nIPC Timeout - Trying workaround...")
            
            # Try without credentials first
            mt5.shutdown()
            time.sleep(2)
            
            if mt5.initialize():
                print("[OK] Basic initialization successful")
                
                # Now try to login
                print(f"\nLogging into account {LOGIN}...")
                if mt5.login(login=LOGIN, password=PASSWORD, server=SERVER):
                    print("[SUCCESS] Logged in!")
                    result = True
                    break
                else:
                    login_error = mt5.last_error()
                    print(f"[ERROR] Login failed: {login_error}")
                    
                    if login_error[0] == -6:  # Authorization failed
                        print("\nAuthorization failed. Possible causes:")
                        print("1. Password might need escaping")
                        print("2. Server name might be case-sensitive")
                        print("3. Account might be locked or expired")
            else:
                print("[ERROR] Basic initialization also failed")
        
        time.sleep(3)

if not result:
    print("\n" + "="*60)
    print("MANUAL FIX REQUIRED")
    print("="*60)
    print("""
    The IPC timeout is blocking Python from connecting to MT5.
    
    SOLUTION:
    
    1. CLOSE ALL MT5 TERMINALS:
       - Close every MT5 window
       - Open Task Manager (Ctrl+Shift+Esc)
       - End any terminal64.exe processes
    
    2. RESTART MT5:
       - Open only ONE MT5 terminal
       - Login manually with:
         Account: 3062432
         Password: d07uL40Z%I
         Server: PlexyTrade-Server01
    
    3. VERIFY LOGIN:
       - Check that you see your balance
       - Keep MT5 running in background
    
    4. RUN THIS SCRIPT AS ADMINISTRATOR:
       - Right-click Command Prompt
       - Run as Administrator
       - Navigate to: C:\\Users\\cmeredith\\source\\repos\\crypto-prop-firm
       - Run: python fix_mt5_connection.py
    
    If this still doesn't work, we need to use the Windows-specific workaround.
    """)
    sys.exit(1)

# Step 3: Verify connection
print("\nStep 3: Verifying connection...")

account_info = mt5.account_info()
if account_info:
    print("\n[SUCCESS] Connected to MT5!")
    print("="*60)
    print(f"Account: {account_info.login}")
    print(f"Server: {account_info.server}")
    print(f"Company: {account_info.company}")
    print(f"Balance: ${account_info.balance:.2f}")
    print(f"Equity: ${account_info.equity:.2f}")
    print(f"Currency: {account_info.currency}")
    print(f"Leverage: 1:{account_info.leverage}")
    print("="*60)
    
    # Test symbols
    print("\nTesting symbol access...")
    symbols_to_test = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD']
    
    for symbol in symbols_to_test:
        if mt5.symbol_select(symbol, True):
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                print(f"  {symbol}: Bid={tick.bid:.5f}, Ask={tick.ask:.5f}, Spread={tick.ask-tick.bid:.5f}")
            else:
                print(f"  {symbol}: No tick data")
        else:
            print(f"  {symbol}: Not available")
    
    print("\n" + "="*60)
    print("CONNECTION SUCCESSFUL!")
    print("="*60)
    print("\nNow we can run the paper trading system.")
    print("To start paper trading, run:")
    print("  python run_paper_trader.py")
    
    # Save working configuration
    with open('mt5_config.txt', 'w') as f:
        f.write(f"LOGIN={LOGIN}\n")
        f.write(f"SERVER={SERVER}\n")
        f.write(f"ACCOUNT_TYPE={ACCOUNT_TYPE}\n")
        f.write(f"STATUS=WORKING\n")
    
    print("\nConfiguration saved to mt5_config.txt")
    
else:
    print("[ERROR] Could not get account info")
    print("Connection established but account details unavailable")

mt5.shutdown()
print("\nDone.")