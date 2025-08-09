"""
MT5 Credentials Verification
Helps verify the correct login details
"""

import MetaTrader5 as mt5
import time

print("MT5 CREDENTIALS VERIFICATION")
print("="*60)

# Initialize MT5 first
print("\nInitializing MT5...")
if not mt5.initialize():
    print(f"[ERROR] Failed to initialize: {mt5.last_error()}")
    print("\nMake sure MT5 is running and try again.")
    exit(1)

print("[OK] MT5 initialized")

# Get current terminal info
terminal_info = mt5.terminal_info()
if terminal_info:
    print(f"Terminal: {terminal_info.name}")
    print(f"Company: {terminal_info.company}")

# Check if already logged in
account = mt5.account_info()
if account:
    print(f"\nCurrently logged in:")
    print(f"  Account: {account.login}")
    print(f"  Server: {account.server}")
    print(f"  Balance: ${account.balance:.2f}")
    print(f"  Currency: {account.currency}")
    print(f"  Company: {account.company}")
    
    if account.login == 3062432:
        print("\n[SUCCESS] Already logged into PlexyTrade account!")
        print("The account is working. The issue might be:")
        print("1. Password has special characters that need escaping")
        print("2. Server name might be different")
        print(f"\nUse these exact credentials:")
        print(f"  Account: {account.login}")
        print(f"  Server: {account.server}")
        print(f"  Password: [Use the password you logged in with in MT5]")
    else:
        print(f"\n[INFO] Logged into different account: {account.login}")
else:
    print("\n[INFO] No account currently logged in")

# Try different server name variations
print("\n" + "="*60)
print("TESTING LOGIN VARIATIONS")
print("="*60)

servers_to_try = [
    "PlexyTrade-Server01",
    "PlexyTrade-Server",
    "PlexyTrade",
    "Plexytrade-Server01",
    "PlexyTradeServer01",
    "PlexyTrade-Demo",
    "PlexyTrade-Live"
]

account_num = 3062432
password = "d07uL40Z%I"

print(f"\nTrying account: {account_num}")
print(f"Password: {password}")
print("\nTrying different server names...\n")

for server in servers_to_try:
    print(f"Server: {server}... ", end="")
    
    # Try to login
    if mt5.login(account_num, password=password, server=server):
        print("[SUCCESS]")
        
        # Get account info
        account = mt5.account_info()
        if account:
            print(f"  Logged in! Balance: ${account.balance:.2f}")
            print(f"  Server: {account.server}")
            print(f"  Company: {account.company}")
            print(f"\n[FOUND] Use server name: '{server}'")
            break
    else:
        error = mt5.last_error()
        if error[0] == -6:  # Authorization failed
            print(f"[AUTH FAILED]")
        elif error[0] == -8:  # Server not found
            print(f"[SERVER NOT FOUND]")
        else:
            print(f"[ERROR: {error[0]}]")
    
    time.sleep(1)  # Small delay between attempts

else:
    print("\n[FAILED] Could not login with any server variation")
    print("\nPOSSIBLE ISSUES:")
    print("1. Password might be wrong (check for typos)")
    print("2. Account might be for different broker")
    print("3. Demo account might have expired")
    print("\nSOLUTION:")
    print("1. In MT5, go to File -> Login to Trade Account")
    print("2. Note the EXACT Server name shown")
    print("3. Verify the account number is 3062432")
    print("4. Try logging in manually first")

# Show all available servers
print("\n" + "="*60)
print("AVAILABLE SERVERS IN MT5")
print("="*60)

# This gets servers known to the terminal
servers = mt5.symbols_get()
if servers:
    # Get unique server from account info if available
    print("\nTo see all available servers:")
    print("1. In MT5, click File -> Login to Trade Account")
    print("2. Click on Server dropdown")
    print("3. Use the EXACT server name shown for PlexyTrade")

# Cleanup
mt5.shutdown()

print("\n" + "="*60)
print("NEXT STEPS")
print("="*60)
print("""
If login still fails:

1. VERIFY IN MT5:
   - Open MT5
   - Go to File -> Login to Trade Account
   - Confirm account is 3062432
   - Note the EXACT server name
   - Try logging in manually

2. CHECK DEMO STATUS:
   - Demo accounts can expire
   - Create new demo if needed

3. PASSWORD ISSUES:
   - Your password has special characters: d07uL40Z%I
   - The % might need escaping
   - Try setting a simpler password in MT5

4. IF ALL ELSE FAILS:
   - Create a new demo account
   - Use a broker like ICMarkets or Pepperstone
   - They have reliable MT5 demo servers
""")