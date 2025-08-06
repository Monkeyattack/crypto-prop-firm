#!/usr/bin/env python3
"""
Show recent signals and trades from the database
"""

import sqlite3
from datetime import datetime, timedelta
from database import DatabaseManager
import pandas as pd

def show_recent_trades():
    """Display recent trades from the database"""
    
    print("=== Recent Trading Signals & Trades ===")
    print("=" * 50)
    
    db = DatabaseManager()
    
    try:
        with db.get_connection() as conn:
            # Get all trades ordered by timestamp
            query = """
            SELECT id, symbol, side, entry, tp, sl, result, pnl, timestamp
            FROM trades
            ORDER BY timestamp DESC
            LIMIT 20
            """
            
            df = pd.read_sql_query(query, conn)
            
            if df.empty:
                print("\n[INFO] No trades found in database yet")
                print("\nTo add trades:")
                print("1. Use the dashboard at http://localhost:8501")
                print("2. Wait for Telegram signals once connected")
                print("3. Run 'python add_test_trade.py' to add sample trades")
            else:
                print(f"\n[FOUND] {len(df)} trades in database")
                print("-" * 80)
                
                for idx, trade in df.iterrows():
                    timestamp = datetime.fromisoformat(trade['timestamp'])
                    time_ago = datetime.now() - timestamp
                    
                    if time_ago.days > 0:
                        time_str = f"{time_ago.days}d ago"
                    elif time_ago.seconds > 3600:
                        time_str = f"{time_ago.seconds // 3600}h ago"
                    else:
                        time_str = f"{time_ago.seconds // 60}m ago"
                    
                    status_emoji = {
                        'open': '🟡',
                        'tp': '✅',
                        'sl': '❌',
                        'manual': '🔄'
                    }.get(trade['result'], '❓')
                    
                    print(f"\n{status_emoji} Trade #{trade['id']} - {time_str}")
                    print(f"   Symbol: {trade['symbol']}")
                    print(f"   Side: {trade['side']}")
                    print(f"   Entry: ${trade['entry']:,.2f}")
                    print(f"   TP: ${trade['tp']:,.2f} ({((trade['tp']/trade['entry']-1)*100):+.2f}%)")
                    print(f"   SL: ${trade['sl']:,.2f} ({((trade['sl']/trade['entry']-1)*100):+.2f}%)")
                    print(f"   Status: {trade['result'].upper()}")
                    if trade['pnl'] != 0:
                        print(f"   P&L: ${trade['pnl']:,.2f}")
                
                # Show summary statistics
                print("\n" + "=" * 50)
                print("Summary Statistics:")
                open_trades = len(df[df['result'] == 'open'])
                closed_trades = len(df[df['result'] != 'open'])
                total_pnl = df['pnl'].sum()
                
                print(f"   Open Trades: {open_trades}")
                print(f"   Closed Trades: {closed_trades}")
                print(f"   Total P&L: ${total_pnl:,.2f}")
                
                if closed_trades > 0:
                    win_trades = len(df[df['pnl'] > 0])
                    win_rate = (win_trades / closed_trades) * 100
                    print(f"   Win Rate: {win_rate:.1f}%")
    
    except Exception as e:
        print(f"\n[ERROR] Failed to retrieve trades: {e}")

def check_telegram_status():
    """Check if Telegram monitoring is active"""
    
    print("\n\n=== Telegram Signal Monitoring Status ===")
    print("=" * 50)
    
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check configuration
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    monitored_groups = os.getenv('TELEGRAM_MONITORED_GROUPS', '')
    
    print("\nConfiguration:")
    print(f"   API ID: {'✅ Set' if api_id else '❌ Missing'}")
    print(f"   API Hash: {'✅ Set' if api_hash else '❌ Missing'}")
    print(f"   Phone: {phone if phone else '❌ Missing'}")
    print(f"   Bot Token: {'✅ Set' if bot_token else '❌ Missing'}")
    print(f"   Monitored Groups: {monitored_groups if monitored_groups else '❌ Not configured'}")
    
    print("\n[INFO] To start monitoring signals:")
    print("1. Fix Telegram API credentials if needed")
    print("2. Run: python telegram_user_client.py")
    print("3. Or use bot: python telegram_bot.py")

def show_signal_examples():
    """Show example signal formats"""
    
    print("\n\n=== Expected Signal Formats ===")
    print("=" * 50)
    
    examples = [
        """
Format 1 - Standard:
Buy BTCUSDT
Entry: 45000
TP: 47000
SL: 43000
        """,
        """
Format 2 - With Labels:
LONG ETHUSDT
Entry Price: 2600
Take Profit: 2750
Stop Loss: 2450
        """,
        """
Format 3 - Compact:
BUY $ADA @ 0.45 | TP: 0.50 | SL: 0.40
        """
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\nExample {i}:")
        print(example.strip())

if __name__ == "__main__":
    show_recent_trades()
    check_telegram_status()
    show_signal_examples()