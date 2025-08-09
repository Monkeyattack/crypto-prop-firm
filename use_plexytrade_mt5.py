"""
Force Python to use PlexyTrade MT5 instead of default MT5
"""

import MetaTrader5 as mt5
import os
import subprocess
import time
import winreg

print("FIXING MT5 TERMINAL ASSOCIATION")
print("="*60)

# Step 1: Find PlexyTrade MT5 installation
print("\nStep 1: Finding PlexyTrade MT5 installation...")

plexytrade_paths = [
    r"C:\Program Files\PlexyTrade MT5\terminal64.exe",
    r"C:\Program Files\PlexyTrade MetaTrader 5\terminal64.exe",
    r"C:\Program Files\MetaTrader 5 - PlexyTrade\terminal64.exe",
    r"C:\Program Files (x86)\PlexyTrade MT5\terminal64.exe",
    r"D:\PlexyTrade MT5\terminal64.exe",
    r"C:\PlexyTrade\terminal64.exe",
]

plexytrade_terminal = None

# Check common paths
for path in plexytrade_paths:
    if os.path.exists(path):
        print(f"[FOUND] PlexyTrade MT5 at: {path}")
        plexytrade_terminal = path
        break

# If not found, search Program Files
if not plexytrade_terminal:
    print("\nSearching Program Files for PlexyTrade...")
    program_files = [r"C:\Program Files", r"C:\Program Files (x86)"]
    
    for pf in program_files:
        if os.path.exists(pf):
            for folder in os.listdir(pf):
                if 'plexy' in folder.lower() and 'mt5' in folder.lower() or 'metatrader' in folder.lower():
                    potential_path = os.path.join(pf, folder, "terminal64.exe")
                    if os.path.exists(potential_path):
                        print(f"[FOUND] PlexyTrade MT5 at: {potential_path}")
                        plexytrade_terminal = potential_path
                        break

if not plexytrade_terminal:
    print("\n[ERROR] PlexyTrade MT5 not found automatically.")
    print("\nPlease provide the path manually:")
    print("1. Find PlexyTrade MT5 shortcut on desktop or start menu")
    print("2. Right-click -> Properties")
    print("3. Copy the Target path")
    print("\nFor now, trying to work with existing MT5...")
else:
    print(f"\nUsing PlexyTrade terminal: {plexytrade_terminal}")

# Step 2: Close default MT5 and start PlexyTrade MT5
print("\n" + "="*60)
print("Step 2: Managing MT5 Processes")
print("="*60)

print("\nChecking for running MT5 instances...")
os.system("tasklist | findstr terminal64")

print("\nIMPORTANT: If you see multiple terminal64.exe:")
print("1. Close the MetaQuotes MT5 (the default one)")
print("2. Keep only PlexyTrade MT5 running")
print("3. Login to account 3062432 in PlexyTrade MT5")

# Step 3: Connect using specific path
print("\n" + "="*60)
print("Step 3: Connecting to PlexyTrade MT5")
print("="*60)

if plexytrade_terminal:
    print(f"\nInitializing with PlexyTrade terminal path...")
    
    # Method 1: Direct path initialization
    if mt5.initialize(path=plexytrade_terminal):
        print("[SUCCESS] Connected to PlexyTrade MT5!")
    else:
        error = mt5.last_error()
        print(f"[ERROR] Failed to connect: {error}")
        
        if error[0] == -10003:  # Terminal not found
            print("\nThe terminal path is incorrect or MT5 is not running.")
            print("Starting PlexyTrade MT5...")
            
            try:
                subprocess.Popen([plexytrade_terminal])
                print("Waiting 15 seconds for MT5 to start...")
                time.sleep(15)
                
                # Try again
                if mt5.initialize(path=plexytrade_terminal):
                    print("[SUCCESS] Connected after starting MT5!")
                else:
                    print(f"[ERROR] Still failed: {mt5.last_error()}")
            except Exception as e:
                print(f"[ERROR] Could not start MT5: {e}")
else:
    # Try default initialization
    print("\nTrying default initialization...")
    if mt5.initialize():
        print("[OK] Connected to MT5 (may not be PlexyTrade)")
    else:
        print(f"[ERROR] Failed: {mt5.last_error()}")

# Step 4: Login to PlexyTrade account
if mt5.initialize() or (plexytrade_terminal and mt5.initialize(path=plexytrade_terminal)):
    print("\n" + "="*60)
    print("Step 4: Logging into PlexyTrade Account")
    print("="*60)
    
    # Check current account
    account = mt5.account_info()
    if account:
        print(f"\nCurrently logged in:")
        print(f"  Account: {account.login}")
        print(f"  Server: {account.server}")
        print(f"  Company: {account.company}")
        
        if account.login == 3062432:
            print("\n[SUCCESS] Already logged into PlexyTrade!")
            print(f"Balance: ${account.balance:.2f}")
            print(f"Equity: ${account.equity:.2f}")
            
            # Save working config
            with open('plexytrade_mt5_path.txt', 'w') as f:
                if plexytrade_terminal:
                    f.write(plexytrade_terminal)
                else:
                    f.write("DEFAULT")
            
            print("\nConfiguration saved!")
            print("Now you can run: python run_paper_trader.py")
        else:
            print(f"\n[INFO] Wrong account. Attempting to login to 3062432...")
            
            if mt5.login(3062432, password="d07uL40Z%I", server="PlexyTrade-Server01"):
                print("[SUCCESS] Logged into PlexyTrade!")
                account = mt5.account_info()
                if account:
                    print(f"Balance: ${account.balance:.2f}")
            else:
                print(f"[ERROR] Login failed: {mt5.last_error()}")
    else:
        print("\n[INFO] Not logged in. Attempting to login...")
        
        if mt5.login(3062432, password="d07uL40Z%I", server="PlexyTrade-Server01"):
            print("[SUCCESS] Logged into PlexyTrade!")
        else:
            print(f"[ERROR] Login failed: {mt5.last_error()}")

mt5.shutdown()

print("\n" + "="*60)
print("SOLUTION SUMMARY")
print("="*60)
print("""
The issue is that Python MT5 is opening the default MetaQuotes MT5
instead of your PlexyTrade MT5.

TO FIX:

1. CLOSE the MetaQuotes MT5 (the one that auto-opened)
2. KEEP your PlexyTrade MT5 running
3. Make sure you're logged into account 3062432 in PlexyTrade
4. Run this script again

If this doesn't work, we'll need to:
- Uninstall the default MetaQuotes MT5, OR
- Use a different approach with direct API calls
""")