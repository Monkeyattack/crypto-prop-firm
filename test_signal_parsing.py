#!/usr/bin/env python3
"""
Test signal parsing with sample messages
"""

from signal_processor import SignalProcessor

def test_signal_parsing():
    """Test signal parsing with various message formats"""
    
    processor = SignalProcessor()
    
    # Test various message formats that might come from SMRT Signals
    test_messages = [
        # Format 1: Simple format
        "BTCUSDT Buy\nEntry: 65000\nTP: 68250\nSL: 61750",
        
        # Format 2: More detailed format
        "🚀 ETHUSDT SELL SIGNAL\n\nEntry: 3500.00\nTake Profit: 3400.00\nStop Loss: 3600.00",
        
        # Format 3: With emojis and formatting
        "📈 SOLUSD - BUY\nEntry Price: $160.50\nTake Profit: $168.00\nStop Loss: $155.00",
        
        # Format 4: Different layout
        "Signal: BTCUSDT\nDirection: Long\nEntry: 65000\nTarget: 68250\nStoploss: 61750",
        
        # Format 5: Compact format
        "ETHUSDT SELL @ 3500 | TP: 3400 | SL: 3600",
        
        # Format 6: What we actually see in logs
        "ETHUSDT Sell\nEntry: 3392.83\nTP: 3324.294834\nSL: 3506.5216556402",
        
        # Format 7: With more realistic SMRT format
        "BTCUSDT Buy\nEntry: 113327.98\nTP: 115934.52354\nSL: 109928.1406"
    ]
    
    print("Testing signal parsing...")
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Test {i} ---")
        print(f"Message: {repr(message)}")
        
        try:
            result = processor.parse_signal(message)
            if result:
                print(f"Parsed successfully:")
                print(f"   Symbol: {result.get('symbol')}")
                print(f"   Side: {result.get('side')}")
                print(f"   Entry: {result.get('entry_price')}")
                print(f"   TP: {result.get('take_profit')}")
                print(f"   SL: {result.get('stop_loss')}")
            else:
                print("Failed to parse")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_signal_parsing()