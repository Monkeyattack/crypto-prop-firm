"""
MT5 Terminal Selection Fix
Handles multiple terminals by specifying exact path
"""

import MetaTrader5 as mt5
import os
import subprocess
import time

print("MT5 TERMINAL SELECTION FIX")
print("="*60)

print("""
Since you have 2 MT5 terminals running, we need to:
1. Close ALL MT5 terminals
2. Start only the PlexyTrade one
3. Then connect

STEPS TO FIX:

1. CLOSE BOTH MT5 TERMINALS:
   - Close all MetaTrader 5 windows
   - Check Task Manager to ensure no terminal64.exe running

2. START ONLY PLEXYTRADE MT5:
   - Open only the PlexyTrade MT5
   - Login with:
     Account: 3062432
     Password: d07uL40Z%I  
     Server: PlexyTrade-Server01
   - Verify you see your balance

3. RUN THIS COMMAND IN NEW CMD WINDOW:
   python mt5_simple_test.py

ALTERNATIVE FIX:

If you need both terminals running, we can use the path method.
Find your PlexyTrade MT5 installation path:
- Usually: C:\\Program Files\\PlexyTrade MT5\\terminal64.exe
- Or: C:\\Program Files\\MetaTrader 5 - PlexyTrade\\terminal64.exe

Then we'll connect using that specific path.
""")

# Try to find PlexyTrade terminal
possible_paths = [
    r"C:\Program Files\PlexyTrade MT5\terminal64.exe",
    r"C:\Program Files\MetaTrader 5 - PlexyTrade\terminal64.exe",
    r"C:\Program Files (x86)\PlexyTrade MT5\terminal.exe",
    r"C:\PlexyTrade\terminal64.exe",
]

print("\nSearching for PlexyTrade MT5 installation...")
for path in possible_paths:
    if os.path.exists(path):
        print(f"Found: {path}")
        print("\nTo use this specific terminal:")
        print(f'mt5.initialize("{path}")')
        break
else:
    print("PlexyTrade MT5 not found in standard locations.")
    print("\nTo find it:")
    print("1. Right-click PlexyTrade MT5 shortcut")
    print("2. Select Properties")
    print("3. Copy the Target path")
    print("4. Use that path in mt5.initialize()")

print("\n" + "="*60)
print("RECOMMENDED SOLUTION:")
print("="*60)
print("""
1. Close the non-PlexyTrade MT5 terminal
2. Keep only PlexyTrade MT5 running
3. Run: python mt5_simple_test.py

This should work immediately.
""")