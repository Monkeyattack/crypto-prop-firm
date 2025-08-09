"""
MT5 Multiple Terminal Connection Handler
Connects to the correct MT5 instance when multiple terminals are running
"""

import MetaTrader5 as mt5
import os
import time

def connect_to_specific_terminal(terminal_path: str = None):
    """Connect to specific MT5 terminal"""
    
    print("="*60)
    print("MT5 MULTIPLE TERMINAL CONNECTION")
    print("="*60)
    
    # Method 1: Specify terminal path
    if terminal_path:
        print(f"Attempting to connect to: {terminal_path}")
        if mt5.initialize(terminal_path):
            print("[OK] Connected via specified path")
            return True
        else:
            print(f"[ERROR] Failed: {mt5.last_error()}")
    
    # Method 2: Try different terminal locations
    terminal_paths = [
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        r"C:\Program Files\PlexyTrade MT5\terminal64.exe",
        r"C:\Program Files\MetaTrader 5 - Broker 1\terminal64.exe",
        r"C:\Program Files\MetaTrader 5 - Broker 2\terminal64.exe",
        r"C:\Program Files (x86)\MetaTrader 5\terminal.exe",
        os.path.expanduser(r"~\AppData\Roaming\MetaQuotes\Terminal\terminal64.exe")
    ]
    
    for path in terminal_paths:
        if os.path.exists(path):
            print(f"\nTrying: {path}")
            
            # Shutdown any existing connection
            mt5.shutdown()
            time.sleep(1)
            
            # Try to initialize with this path
            if mt5.initialize(path):
                print(f"[OK] Connected to: {path}")
                
                # Check which account is connected
                account_info = mt5.account_info()
                if account_info:
                    print(f"Account: {account_info.login}")
                    print(f"Server: {account_info.server}")
                    print(f"Company: {account_info.company}")
                    print(f"Balance: ${account_info.balance:.2f}")
                    
                    # Ask if this is the right one
                    return True
                else:
                    print("[WARNING] Connected but no account info")
            else:
                print(f"[ERROR] Failed: {mt5.last_error()}")
    
    return False

def connect_with_portable_mode():
    """Use portable mode to connect to specific terminal"""
    
    print("\nUsing PORTABLE MODE connection...")
    
    # Method 3: Use portable mode with config file
    # This allows specifying exact terminal
    
    # First, shutdown any existing connection
    mt5.shutdown()
    time.sleep(1)
    
    # Initialize without path (connects to first available)
    if mt5.initialize():
        account = mt5.account_info()
        if account:
            print(f"\n[OK] Connected to first available terminal")
            print(f"Account: {account.login}")
            print(f"Server: {account.server}")
            
            # Check if this is PlexyTrade
            if "Plexy" in account.server or account.login == 3062432:
                print("[OK] This is the PlexyTrade account!")
                return True
            else:
                print("[INFO] This is not PlexyTrade, trying to switch...")
                
                # Try to login to PlexyTrade
                mt5.shutdown()
                time.sleep(2)
                
                # Reinitialize and login
                if mt5.initialize():
                    if mt5.login(3062432, "d07uL40Z%I", "PlexyTrade-Server01"):
                        print("[OK] Logged into PlexyTrade account")
                        return True
    
    return False

def test_plexytrade_connection():
    """Test connection specifically to PlexyTrade"""
    
    print("\n" + "="*60)
    print("TESTING PLEXYTRADE CONNECTION")
    print("="*60)
    
    # Try different connection methods
    methods = [
        ("Default connection", lambda: mt5.initialize()),
        ("Portable mode", connect_with_portable_mode),
        ("Direct path", lambda: connect_to_specific_terminal())
    ]
    
    for method_name, method_func in methods:
        print(f"\nMethod: {method_name}")
        
        # Shutdown any existing
        mt5.shutdown()
        time.sleep(1)
        
        try:
            if method_func():
                # Try to login to PlexyTrade
                result = mt5.login(
                    login=3062432,
                    password="d07uL40Z%I",
                    server="PlexyTrade-Server01"
                )
                
                if result:
                    account = mt5.account_info()
                    if account:
                        print(f"\n[SUCCESS] Connected to PlexyTrade!")
                        print(f"Account: {account.login}")
                        print(f"Balance: ${account.balance:.2f}")
                        print(f"Server: {account.server}")
                        print(f"Currency: {account.currency}")
                        
                        # Test getting symbol info
                        symbols = ['XAUUSD', 'EURUSD', 'BTCUSD']
                        print("\nAvailable symbols:")
                        for symbol in symbols:
                            if mt5.symbol_select(symbol, True):
                                info = mt5.symbol_info(symbol)
                                if info:
                                    print(f"  {symbol}: Bid={info.bid:.5f}, Ask={info.ask:.5f}")
                        
                        return True
                else:
                    error = mt5.last_error()
                    print(f"[ERROR] Login failed: {error}")
        except Exception as e:
            print(f"[ERROR] Exception: {e}")
    
    return False

def run_paper_trader_with_connection():
    """Run paper trader after establishing connection"""
    
    if test_plexytrade_connection():
        print("\n" + "="*60)
        print("CONNECTION SUCCESSFUL!")
        print("="*60)
        print("\nNow we can run the paper trader.")
        print("The system will:")
        print("1. Monitor signals from your database")
        print("2. Execute them on PlexyTrade demo")
        print("3. Track performance for 7 days")
        print("4. Simulate FTMO and Breakout Prop rules")
        print("5. Send daily reports")
        
        # Import and run paper trader
        from mt5_paper_trader import MT5PaperTrader
        
        trader = MT5PaperTrader(
            account=3062432,
            password="d07uL40Z%I",
            server="PlexyTrade-Server01"
        )
        
        if trader.connected:
            print("\n[OK] Paper trader initialized")
            print("Starting 7-day verification...")
            
            import asyncio
            asyncio.run(trader.run_paper_trading())
        else:
            print("[ERROR] Paper trader failed to connect")
    else:
        print("\n" + "="*60)
        print("CONNECTION FAILED")
        print("="*60)
        print("""
        SOLUTIONS:
        
        1. ENSURE MT5 IS RUNNING:
           - Open MT5 if not already open
           - Login to account 3062432
           - Keep it running in background
        
        2. CHECK WINDOWS DEFENDER:
           - Add Python to Windows Defender exceptions
           - Add MT5 to exceptions
        
        3. RUN AS ADMINISTRATOR:
           - Right-click Command Prompt
           - Run as Administrator
           - Try script again
        
        4. USE ONLY ONE MT5:
           - Close all MT5 terminals
           - Open only PlexyTrade MT5
           - Login to account 3062432
           - Try script again
        """)

if __name__ == "__main__":
    print("""
    This script handles multiple MT5 terminals.
    It will find and connect to your PlexyTrade account.
    """)
    
    # Run connection test
    run_paper_trader_with_connection()
