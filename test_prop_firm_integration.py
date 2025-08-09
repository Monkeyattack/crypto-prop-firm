#!/usr/bin/env python3
"""
Test Prop Firm Integration
Creates sample data to demonstrate the integrated dashboard
"""

import sqlite3
import random
from datetime import datetime, timedelta
from prop_firm_signal_processor import PropFirmSignalProcessor

def create_sample_signals(db_path="trade_log.db", count=20):
    """Create sample signals in signal_log table"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT']
    sides = ['BUY', 'SELL']
    
    print(f"Creating {count} sample signals...")
    
    for i in range(count):
        # Generate random signal
        symbol = random.choice(symbols)
        side = random.choice(sides)
        
        # Generate realistic prices
        if symbol == 'BTCUSDT':
            base_price = 45000 + random.randint(-5000, 5000)
        elif symbol == 'ETHUSDT':
            base_price = 2500 + random.randint(-500, 500)
        else:
            base_price = random.uniform(0.5, 10.0)
        
        entry = base_price
        
        # Generate TP and SL with varying R:R ratios
        risk_distance = entry * random.uniform(0.02, 0.05)  # 2-5% risk
        
        # Vary R:R ratios to test filtering
        rr_ratio = random.choice([0.5, 0.8, 1.2, 1.8, 2.5, 3.0])  # Mix of good and bad ratios
        reward_distance = risk_distance * rr_ratio
        
        if side == 'BUY':
            sl = entry - risk_distance
            tp = entry + reward_distance
        else:
            sl = entry + risk_distance
            tp = entry - reward_distance
        
        # Random timestamp in last 24 hours
        timestamp = datetime.now() - timedelta(hours=random.randint(0, 24))
        
        # Insert signal
        cursor.execute("""
            INSERT INTO signal_log 
            (channel, message_id, timestamp, symbol, side, entry_price, take_profit, stop_loss, 
             signal_type, raw_message, processed, trade_executed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
        """, (
            'test_channel',
            1000 + i,
            timestamp.isoformat(),
            symbol,
            side,
            entry,
            tp,
            sl,
            'breakout',
            f"Test signal {i+1}: {symbol} {side} @ {entry:.4f} TP:{tp:.4f} SL:{sl:.4f}"
        ))
    
    conn.commit()
    conn.close()
    print(f"Created {count} sample signals")

def test_prop_firm_processing():
    """Test the prop firm signal processing"""
    
    print("\nTesting prop firm signal processing...")
    
    processor = PropFirmSignalProcessor()
    
    # Process all signals
    decisions = processor.process_new_signals()
    
    if decisions:
        accepted = sum(1 for d in decisions if d['decision'] == 'ACCEPTED')
        rejected = len(decisions) - accepted
        
        print(f"Processed {len(decisions)} signals:")
        print(f"  Accepted: {accepted}")
        print(f"  Rejected: {rejected}")
        print(f"  Acceptance Rate: {(accepted/len(decisions)*100):.1f}%")
        
        # Show some examples
        print("\nExample decisions:")
        for decision in decisions[:5]:
            status = "ACCEPTED" if decision['decision'] == 'ACCEPTED' else "REJECTED"
            print(f"  {status} {decision['symbol']} {decision['side']} - {decision['reason'][:60]}...")
    else:
        print("No decisions generated - all signals may already be processed")
    
    # Show daily stats
    stats = processor.get_daily_stats()
    print(f"\nDaily Stats:")
    print(f"  Total Signals: {stats.get('total_signals', 0)}")
    print(f"  Accepted: {stats.get('accepted', 0)}")
    print(f"  Rejected: {stats.get('rejected', 0)}")
    print(f"  Acceptance Rate: {stats.get('acceptance_rate', 0):.1f}%")

def show_recent_decisions():
    """Show recent decisions for verification"""
    
    print("\nRecent Prop Firm Decisions:")
    
    processor = PropFirmSignalProcessor()
    decisions = processor.get_recent_decisions(10)
    
    if decisions:
        print(f"{'Time':<8} {'Symbol':<10} {'Side':<5} {'Decision':<9} {'Reason'}")
        print("-" * 80)
        
        for decision in decisions:
            timestamp = datetime.fromisoformat(decision['timestamp'].replace('Z', '+00:00'))
            time_str = timestamp.strftime('%H:%M:%S')
            
            print(f"{time_str:<8} {decision['symbol']:<10} {decision['side']:<5} "
                  f"{decision['decision']:<9} {decision['reason'][:40]}...")
    else:
        print("No recent decisions found")

def main():
    """Main test function"""
    print("Testing Prop Firm Integration")
    print("=" * 50)
    
    # Create sample signals
    create_sample_signals(count=15)
    
    # Test processing
    test_prop_firm_processing()
    
    # Show results
    show_recent_decisions()
    
    print("\nTest complete! You can now:")
    print("1. Run the dashboard: streamlit run dashboard/app.py")
    print("2. Navigate to 'Prop Firm' tab to see the integration")
    print("3. Check the 'Dashboard' page for prop firm status banner")
    print("4. Look for prop firm decisions in the main dashboard")
    print("\nThe integration shows:")
    print("   - Real-time prop firm signal filtering decisions")
    print("   - Risk management status and warnings") 
    print("   - Separate statistics for both accounts")
    print("   - Telegram alert messages for accepted trades")

if __name__ == "__main__":
    main()