#!/usr/bin/env python3
"""
Test the new equity-based position sizing system
"""

from equity_position_sizer import position_sizer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_equity_sizing():
    """Test equity-based position sizing with sample signals"""
    
    # Test signal from SMRT Signals
    test_signal = {
        'symbol': 'ETHUSDT',
        'side': 'Sell',
        'entry_price': 3668.53,
        'take_profit': 3594.43,  # Modified by our 5% strategy
        'stop_loss': 3851.96     # Modified by our 5% max loss
    }
    
    print("Testing Equity-Based Position Sizing")
    print("=" * 50)
    print(f"Signal: {test_signal['symbol']} {test_signal['side']}")
    print(f"Entry: ${test_signal['entry_price']:.2f}")
    print(f"Take Profit: ${test_signal['take_profit']:.2f}")
    print(f"Stop Loss: ${test_signal['stop_loss']:.2f}")
    print()
    
    # Calculate position size
    position_size, details = position_sizer.calculate_position_size(test_signal)
    
    if position_size > 0:
        print("Position Size Calculation Successful!")
        print(f"Position Size: ${position_size:.2f}")
        print()
        print("Sizing Details:")
        for key, value in details.items():
            if isinstance(value, float):
                if 'pct' in key:
                    print(f"   {key}: {value:.2f}%")
                elif 'usd' in key or 'balance' in key or 'size' in key:
                    print(f"   {key}: ${value:.2f}")
                else:
                    print(f"   {key}: {value:.2f}")
            else:
                print(f"   {key}: {value}")
        
        print()
        print("Trade Economics:")
        entry = test_signal['entry_price']
        sl = test_signal['stop_loss']
        tp = test_signal['take_profit']
        
        # Calculate potential P&L
        sl_distance_pct = abs((sl - entry) / entry) * 100
        tp_distance_pct = abs((entry - tp) / entry) * 100
        
        max_loss = position_size * (sl_distance_pct / 100)
        max_profit = position_size * (tp_distance_pct / 100)
        
        print(f"   Max Loss: ${max_loss:.2f} ({sl_distance_pct:.2f}%)")
        print(f"   Max Profit: ${max_profit:.2f} ({tp_distance_pct:.2f}%)")
        print(f"   Risk/Reward: 1:{max_profit/max_loss:.2f}")
        
    else:
        print("Position Size Calculation Failed!")
        print(f"Error: {details.get('error', 'Unknown error')}")
        if 'error' not in details:
            print("Details:", details)

if __name__ == "__main__":
    test_equity_sizing()