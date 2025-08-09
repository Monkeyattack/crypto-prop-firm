"""Check Gold/FX signals and current prices"""

import sqlite3
import MetaTrader5 as mt5

# Connect to database
conn = sqlite3.connect('trade_log.db')
cursor = conn.cursor()

# Get Gold/FX signals
cursor.execute("""
    SELECT symbol, side, entry_price, stop_loss, take_profit
    FROM signal_log 
    WHERE symbol IN ('XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY')
    AND processed = 0
""")

signals = cursor.fetchall()

print("=" * 70)
print("GOLD/FX SIGNALS vs CURRENT MARKET PRICES")
print("=" * 70)

# Initialize MT5
if mt5.initialize():
    print("\nSignal Analysis:")
    for signal in signals:
        symbol, side, entry, sl, tp = signal
        
        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            current = tick.ask if side == 'BUY' else tick.bid
            
            # Calculate original R:R
            if side == 'BUY':
                orig_risk = entry - sl
                orig_reward = tp - entry
            else:
                orig_risk = sl - entry
                orig_reward = entry - tp
            
            orig_rr = orig_reward / orig_risk if orig_risk > 0 else 0
            
            # Calculate current R:R based on market price
            if side == 'BUY':
                curr_risk = current - sl
                curr_reward = tp - current
            else:
                curr_risk = sl - current
                curr_reward = current - tp
            
            curr_rr = curr_reward / curr_risk if curr_risk > 0 else 0
            
            print(f"\n{symbol} {side}:")
            print(f"  Signal Entry: {entry:.5f}")
            print(f"  Current Price: {current:.5f}")
            print(f"  Price Difference: {abs(current - entry):.5f}")
            print(f"  Original R:R: {orig_rr:.2f}")
            print(f"  Current R:R: {curr_rr:.2f}")
            
            if curr_rr < 2.5:
                print(f"  Status: SKIPPED (R:R {curr_rr:.2f} < 2.5)")
            else:
                print(f"  Status: TRADEABLE")
        else:
            print(f"\n{symbol}: No market data available")
    
    mt5.shutdown()
else:
    print("Failed to connect to MT5")

conn.close()

print("\n" + "=" * 70)
print("EXPLANATION:")
print("The system recalculates R:R based on CURRENT market prices.")
print("If price has moved against the signal, R:R deteriorates.")
print("This is correct behavior - we don't chase bad entries.")
print("=" * 70)