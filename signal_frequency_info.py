#!/usr/bin/env python3
"""
Information about signal update frequency
"""

def explain_signal_frequency():
    """Explain how often signals are updated"""
    
    print("=== SIGNAL UPDATE FREQUENCY ===")
    print()
    
    print("SAMPLE TRADES (Current):")
    print("- Static test data (not real-time)")
    print("- Added once for demonstration")
    print("- Manual updates only")
    print()
    
    print("LIVE TELEGRAM SIGNALS (When Connected):")
    print("- Real-time as messages arrive")
    print("- Instant processing (< 1 second)")
    print("- 24/7 monitoring")
    print("- Depends on group activity")
    print()
    
    print("TYPICAL SIGNAL FREQUENCY:")
    print("Active Groups:")
    print("- 5-20 signals per day")
    print("- Peak during market hours")
    print("- Higher on volatile days")
    print()
    
    print("SMRT Signals - Crypto Channel:")
    print("- Unknown frequency (you'd need to observe)")
    print("- Could be 1-10 signals per day")
    print("- Quality over quantity approach")
    print()
    
    print("SYSTEM RESPONSE TIME:")
    print("- Signal detection: < 1 second")
    print("- Database update: < 1 second") 
    print("- Dashboard refresh: 1-5 seconds")
    print("- Total delay: 1-6 seconds max")
    print()
    
    print("MONITORING STATUS:")
    from database import DatabaseManager
    
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM trades")
            count = cursor.fetchone()[0]
            print(f"- Current trades in database: {count}")
            
            cursor.execute("SELECT timestamp FROM trades ORDER BY timestamp DESC LIMIT 1")
            latest = cursor.fetchone()
            if latest:
                print(f"- Latest trade: {latest[0]}")
            else:
                print("- No trades yet")
    except:
        print("- Database status: Unknown")
    
    print()
    print("TO GET LIVE SIGNALS:")
    print("1. Add @MonkeyAttack_ProfitHit_Bot to your group")
    print("2. Make it admin with message reading")
    print("3. Signals will appear in real-time")
    print("4. Check dashboard for updates")

if __name__ == "__main__":
    explain_signal_frequency()