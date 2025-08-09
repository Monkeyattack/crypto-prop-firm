"""
MT5 Connection Troubleshooting and Setup Guide
"""

import subprocess
import os
import time
import MetaTrader5 as mt5

def diagnose_mt5():
    """Diagnose MT5 connection issues"""
    
    print("="*60)
    print("MT5 CONNECTION DIAGNOSTIC")
    print("="*60)
    
    # Check if MT5 is installed
    mt5_paths = [
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        r"C:\Program Files (x86)\MetaTrader 5\terminal.exe",
        os.path.expanduser(r"~\AppData\Roaming\MetaQuotes\Terminal\terminal64.exe"),
        r"C:\Program Files\PlexyTrade MT5\terminal64.exe",
        r"C:\Program Files\MetaTrader 5 - PlexyTrade\terminal64.exe"
    ]
    
    mt5_found = False
    mt5_location = None
    
    for path in mt5_paths:
        if os.path.exists(path):
            mt5_found = True
            mt5_location = path
            print(f"[OK] MT5 found at: {path}")
            break
    
    if not mt5_found:
        print("[ERROR] MT5 not found in standard locations")
        print("\nPlease install MT5 from your broker:")
        print("1. Go to PlexyTrade website")
        print("2. Download their MT5 platform")
        print("3. Install and run it once manually")
        return False
    
    # Try to start MT5
    print("\nAttempting to start MT5...")
    try:
        # Initialize MT5
        if not mt5.initialize():
            print("[ERROR] Failed to initialize MT5")
            print("\nTrying to launch MT5 manually...")
            
            # Try to launch MT5
            if mt5_location:
                subprocess.Popen([mt5_location])
                print("Waiting for MT5 to start (30 seconds)...")
                time.sleep(30)
                
                # Try again
                if mt5.initialize():
                    print("[OK] MT5 initialized after manual launch")
                    return True
                else:
                    print("[ERROR] Still cannot connect")
                    return False
        else:
            print("[OK] MT5 initialized successfully")
            return True
            
    except Exception as e:
        print(f"[ERROR] Exception during MT5 startup: {e}")
        return False

def setup_mt5_connection():
    """Guide user through MT5 setup"""
    
    print("""
    ============================================================
    MT5 SETUP INSTRUCTIONS FOR PLEXYTRADE
    ============================================================
    
    The IPC timeout error means MT5 isn't running or accessible.
    
    STEP-BY-STEP FIX:
    
    1. DOWNLOAD MT5 FROM PLEXYTRADE:
       - Go to PlexyTrade website
       - Download their MT5 platform (not generic MT5)
       - Install it completely
    
    2. LAUNCH MT5 MANUALLY FIRST:
       - Open MetaTrader 5 from desktop/start menu
       - Click File -> Login to Trade Account
       - Enter:
         Login: 3062432
         Password: d07uL40Z%I
         Server: PlexyTrade-Server01
       - Click OK and verify you're connected
    
    3. KEEP MT5 RUNNING:
       - Leave MT5 open in the background
       - Do NOT close it
    
    4. RUN THIS SCRIPT AGAIN:
       - With MT5 already running, the connection should work
    
    ALTERNATIVE: If PlexyTrade doesn't work, try:
    - ICMarkets Demo (very reliable)
    - Pepperstone Demo
    - XM Demo
    
    ============================================================
    """)

def test_connection_with_retry(account: int, password: str, server: str):
    """Test MT5 connection with retry logic"""
    
    print(f"\nTesting connection to {server}...")
    
    # First ensure MT5 is running
    if not diagnose_mt5():
        print("\n[ACTION REQUIRED] Please start MT5 manually and login")
        print("Press Enter when MT5 is running and logged in...")
        input()
    
    # Now try to connect
    attempts = 3
    for attempt in range(attempts):
        print(f"\nConnection attempt {attempt + 1} of {attempts}...")
        
        if mt5.initialize():
            print("[OK] MT5 initialized")
            
            # Try to login
            authorized = mt5.login(
                login=account,
                password=password,
                server=server
            )
            
            if authorized:
                account_info = mt5.account_info()
                print(f"[OK] Connected to account {account}")
                print(f"[OK] Balance: ${account_info.balance:.2f}")
                print(f"[OK] Server: {account_info.server}")
                print(f"[OK] Company: {account_info.company}")
                return True
            else:
                error = mt5.last_error()
                print(f"[ERROR] Login failed: {error}")
                
                if error[0] == -10004:  # Invalid password
                    print("Password may be incorrect")
                elif error[0] == -10006:  # No connection
                    print("Cannot connect to server")
        else:
            print(f"[ERROR] MT5 initialization failed: {mt5.last_error()}")
        
        if attempt < attempts - 1:
            print("Waiting 10 seconds before retry...")
            time.sleep(10)
    
    return False

if __name__ == "__main__":
    # Show setup instructions
    setup_mt5_connection()
    
    # Test with user's credentials
    print("\n" + "="*60)
    print("TESTING YOUR CREDENTIALS")
    print("="*60)
    
    success = test_connection_with_retry(
        account=3062432,
        password="d07uL40Z%I",
        server="PlexyTrade-Server01"
    )
    
    if success:
        print("\n" + "="*60)
        print("SUCCESS! MT5 CONNECTION WORKING")
        print("="*60)
        print("\nYou can now run: python mt5_paper_trader.py")
        print("The paper trading system will track your trades for 7 days")
        
        # Shutdown MT5 connection
        mt5.shutdown()
    else:
        print("\n" + "="*60)
        print("CONNECTION FAILED")
        print("="*60)
        print("""
        TROUBLESHOOTING CHECKLIST:
        
        [ ] Is MT5 installed from PlexyTrade?
        [ ] Is MT5 currently running?
        [ ] Are you logged into the account in MT5?
        [ ] Is the server name exactly 'PlexyTrade-Server01'?
        [ ] Is Windows Firewall blocking MT5?
        
        If PlexyTrade doesn't work, consider getting a demo from:
        - ICMarkets (most reliable)
        - Pepperstone
        - XM
        """)
