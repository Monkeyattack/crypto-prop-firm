#!/usr/bin/env python3
from equity_position_sizer import position_sizer

test_signal = {
    'symbol': 'ETHUSDT',
    'side': 'Sell', 
    'entry_price': 3668.53,
    'take_profit': 3594.43,
    'stop_loss': 3851.96
}

position_size, details = position_sizer.calculate_position_size(test_signal)
print(f'VPS Position Size Test: ${position_size:.2f}')
print(f'Account Balance: ${details.get("account_balance", 0):.2f}')
print(f'Risk Per Trade: {details.get("actual_risk_pct", 0):.2f}%')
print(f'Position Capacity: {details.get("open_positions", 0)}/{details.get("max_positions", 0)}')
print('Equity-based position sizing deployed successfully!')