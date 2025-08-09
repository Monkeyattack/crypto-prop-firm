"""
Debug Trade Execution
Find out why orders are failing
"""

import MetaTrader5 as mt5
from datetime import datetime

print("DEBUGGING TRADE EXECUTION")
print("="*60)

# Connect
if not mt5.initialize():
    print(f"Failed to initialize: {mt5.last_error()}")
    exit(1)

account = mt5.account_info()
print(f"Connected to account: {account.login}")
print(f"Balance: ${account.balance:.2f}")
print(f"Trade allowed: {account.trade_allowed}")
print(f"Expert allowed: {account.trade_expert}")

# Test EURUSD
symbol = "EURUSD"
print(f"\nTesting {symbol}...")

if not mt5.symbol_select(symbol, True):
    print(f"Cannot select {symbol}")
    exit(1)

# Get symbol info
info = mt5.symbol_info(symbol)
print(f"Symbol info:")
print(f"  Min volume: {info.volume_min}")
print(f"  Max volume: {info.volume_max}")
print(f"  Volume step: {info.volume_step}")
print(f"  Trade mode: {info.trade_mode}")
print(f"  Trade contract size: {info.trade_contract_size}")
print(f"  Point: {info.point}")
print(f"  Digits: {info.digits}")

# Get current price
tick = mt5.symbol_info_tick(symbol)
print(f"\nCurrent prices:")
print(f"  Bid: {tick.bid:.5f}")
print(f"  Ask: {tick.ask:.5f}")
print(f"  Spread: {tick.ask - tick.bid:.5f}")

# Try the simplest possible order
print(f"\nTesting simplest market order...")

request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbol,
    "volume": info.volume_min,
    "type": mt5.ORDER_TYPE_BUY,
    "price": tick.ask,
    "deviation": 50,
    "magic": 12345,
    "comment": "Debug test",
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_IOC,
}

print(f"Order request:")
for key, value in request.items():
    print(f"  {key}: {value}")

print(f"\nSending order...")
result = mt5.order_send(request)

print(f"\nOrder result:")
if result is None:
    print("  Result is None - order_send failed completely")
    print(f"  Last error: {mt5.last_error()}")
else:
    print(f"  Return code: {result.retcode}")
    print(f"  Comment: {result.comment}")
    print(f"  Request ID: {result.request_id}")
    
    if hasattr(result, 'order'):
        print(f"  Order: {result.order}")
    if hasattr(result, 'deal'):
        print(f"  Deal: {result.deal}")
    if hasattr(result, 'price'):
        print(f"  Price: {result.price}")
    if hasattr(result, 'volume'):
        print(f"  Volume: {result.volume}")
    
    # Explain return codes
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print("  [SUCCESS] Trade executed!")
    elif result.retcode == mt5.TRADE_RETCODE_INVALID_VOLUME:
        print("  [ERROR] Invalid volume")
    elif result.retcode == mt5.TRADE_RETCODE_INVALID_PRICE:
        print("  [ERROR] Invalid price")
    elif result.retcode == mt5.TRADE_RETCODE_INVALID_STOPS:
        print("  [ERROR] Invalid stops")
    elif result.retcode == mt5.TRADE_RETCODE_TRADE_DISABLED:
        print("  [ERROR] Trading disabled")
    elif result.retcode == mt5.TRADE_RETCODE_MARKET_CLOSED:
        print("  [ERROR] Market closed")
    elif result.retcode == mt5.TRADE_RETCODE_NO_MONEY:
        print("  [ERROR] Not enough money")
    elif result.retcode == mt5.TRADE_RETCODE_PRICE_CHANGED:
        print("  [ERROR] Price changed")
    elif result.retcode == mt5.TRADE_RETCODE_REJECT:
        print("  [ERROR] Request rejected")
    else:
        print(f"  [ERROR] Unknown return code: {result.retcode}")

# Check if we have any open positions
positions = mt5.positions_get()
print(f"\nOpen positions: {len(positions) if positions else 0}")

if positions:
    for pos in positions[:3]:  # Show first 3
        print(f"  {pos.symbol} {pos.type} {pos.volume} lots, P&L: {pos.profit:.2f}")

# Check recent orders
print(f"\nChecking recent orders...")
orders = mt5.history_orders_get(datetime.now().replace(hour=0, minute=0, second=0), datetime.now())
if orders:
    print(f"Orders today: {len(orders)}")
    for order in orders[-3:]:  # Last 3 orders
        print(f"  {order.symbol} {order.type} {order.volume_initial} lots, State: {order.state}")
else:
    print("No orders found today")

mt5.shutdown()
print("\nDone.")