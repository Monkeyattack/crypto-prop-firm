#!/usr/bin/env python3
"""
Check recent signals and trading status
"""

import sqlite3
from datetime import datetime
from database import DatabaseManager
import pandas as pd
import os
from dotenv import load_dotenv

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
            LIMIT 10
            """
            
            cursor = conn.cursor()
            cursor.execute(query)
            trades = cursor.fetchall()
            
            if not trades:
                print("\n[INFO] No trades found in database yet")
                print("\nTo add trades:")
                print("1. Use the dashboard at http://localhost:8501")
                print("2. Wait for Telegram signals once connected")
                print("3. Run 'python add_test_trade.py' to add sample trades")
            else:
                print(f"\n[FOUND] {len(trades)} trades in database")
                print("-" * 60)
                
                for trade in trades:
                    trade_id, symbol, side, entry, tp, sl, result, pnl, timestamp = trade
                    
                    try:
                        trade_time = datetime.fromisoformat(timestamp)
                        time_ago = datetime.now() - trade_time
                        
                        if time_ago.days > 0:
                            time_str = f"{time_ago.days}d ago"
                        elif time_ago.seconds > 3600:
                            time_str = f"{time_ago.seconds // 3600}h ago"
                        else:
                            time_str = f"{time_ago.seconds // 60}m ago"
                    except:
                        time_str = "Unknown time"
                    
                    status_map = {
                        'open': '[OPEN]',
                        'tp': '[WIN]',
                        'sl': '[LOSS]',
                        'manual': '[CLOSED]'
                    }
                    status = status_map.get(result, '[UNKNOWN]')
                    
                    print(f"\nTrade #{trade_id} - {time_str}")
                    print(f"   Symbol: {symbol}")
                    print(f"   Side: {side}")
                    print(f"   Entry: ${entry:,.2f}")
                    print(f"   TP: ${tp:,.2f} ({((tp/entry-1)*100):+.2f}%)")
                    print(f"   SL: ${sl:,.2f} ({((sl/entry-1)*100):+.2f}%)")
                    print(f"   Status: {status}")
                    if pnl != 0:
                        print(f"   P&L: ${pnl:,.2f}")
                
                # Show summary
                print("\n" + "=" * 50)
                print("Summary:")
                open_count = sum(1 for t in trades if t[6] == 'open')
                closed_count = len(trades) - open_count
                total_pnl = sum(t[7] for t in trades)
                
                print(f"   Open Trades: {open_count}")
                print(f"   Closed Trades: {closed_count}")
                print(f"   Total P&L: ${total_pnl:,.2f}")
    
    except Exception as e:
        print(f"\n[ERROR] Failed to retrieve trades: {e}")

def check_telegram_status():
    """Check Telegram configuration"""
    
    print("\n\n=== Telegram Signal Monitoring Status ===")
    print("=" * 50)
    
    load_dotenv()
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    monitored_groups = os.getenv('TELEGRAM_MONITORED_GROUPS', '')
    
    print("\nConfiguration Status:")
    print(f"   API ID: {'[SET]' if api_id else '[MISSING]'}")
    print(f"   API Hash: {'[SET]' if api_hash else '[MISSING]'}")
    print(f"   Phone: {phone if phone else '[MISSING]'}")
    print(f"   Bot Token: {'[SET]' if bot_token else '[MISSING]'}")
    print(f"   Target Group: {monitored_groups if monitored_groups else '[NOT SET]'}")
    
    if api_id and api_hash and phone:
        print(f"\n[READY] Personal account method configured")
        print(f"   Run: python telegram_verify.py")
    elif bot_token:
        print(f"\n[ALTERNATIVE] Bot method available")
        print(f"   Run: python test_bot.py")
    else:
        print(f"\n[ERROR] Neither method properly configured")

def show_signal_examples():
    """Show expected signal formats"""
    
    print("\n\n=== Expected Signal Formats ===")
    print("=" * 50)
    
    print("\nThe system can detect these formats:")
    
    print("\n1. Standard Format:")
    print("   Buy BTCUSDT")
    print("   Entry: 45000")
    print("   TP: 47000")
    print("   SL: 43000")
    
    print("\n2. Long/Short Format:")
    print("   LONG ETHUSDT")
    print("   Entry Price: 2600")
    print("   Take Profit: 2750")
    print("   Stop Loss: 2450")
    
    print("\n3. Compact Format:")
    print("   BUY $ADA @ 0.45 | TP: 0.50 | SL: 0.40")

if __name__ == "__main__":
    show_recent_trades()
    check_telegram_status()
    show_signal_examples()