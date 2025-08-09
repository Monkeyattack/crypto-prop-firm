"""
Pull ALL historical signals from Telegram channels for backtesting
"""

import asyncio
import os
import sqlite3
import re
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession

async def pull_all_signals():
    """Pull all available signals from Telegram channels"""
    
    # Load credentials
    api_id = 27540855
    api_hash = '0ad0e0e612829f4642c373ff0334df1e'
    
    # Load session
    session_string = None
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('TELEGRAM_SESSION_STRING='):
                    session_string = line.split('=', 1)[1].strip()
                    break
    
    if not session_string:
        print("No session found")
        return
    
    print("Connecting to Telegram...")
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    
    signals_found = []
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print("Not authorized!")
            return
        
        print("Connected! Searching for signals...")
        
        # Get dialogs
        dialogs = await client.get_dialogs()
        
        # Find channels
        channels_to_check = []
        for dialog in dialogs:
            if "Gold" in dialog.name or "FX" in dialog.name or "SMRT" in dialog.name:
                channels_to_check.append(dialog)
                print(f"Will check: {dialog.name}")
        
        # Process each channel
        for channel in channels_to_check:
            print(f"\n{'='*70}")
            print(f"Checking: {channel.name}")
            print('='*70)
            
            # Get more messages (last 100)
            messages = await client.get_messages(channel, limit=100)
            
            for msg in messages:
                if not msg.text:
                    continue
                
                text = msg.text
                upper_text = text.upper()
                
                # Parse different signal formats
                signal = None
                
                # Format 1: "Buy XAUUSD\nEntry: X\nTP: Y\nSL: Z"
                if ('BUY' in upper_text or 'SELL' in upper_text) and ('ENTRY' in upper_text or '@' in text):
                    
                    # Extract symbol
                    symbol = None
                    if 'XAUUSD' in upper_text:
                        symbol = 'XAUUSD'
                    elif 'GOLD' in upper_text:
                        symbol = 'XAUUSD'
                    elif 'EURUSD' in upper_text:
                        symbol = 'EURUSD'
                    elif 'GBPUSD' in upper_text:
                        symbol = 'GBPUSD'
                    elif 'USDJPY' in upper_text:
                        symbol = 'USDJPY'
                    elif 'BTCUSDT' in upper_text or 'BTCUSD' in upper_text:
                        symbol = 'BTCUSD'
                    elif 'ETHUSDT' in upper_text or 'ETHUSD' in upper_text:
                        symbol = 'ETHUSD'
                    elif 'SOLUSDT' in upper_text or 'SOLUSD' in upper_text:
                        symbol = 'SOLUSD'
                    
                    if symbol:
                        # Extract side
                        side = 'BUY' if 'BUY' in upper_text or 'LONG' in upper_text else 'SELL'
                        
                        # Extract prices using regex
                        entry_match = re.search(r'(?:ENTRY|Entry|@)\s*:?\s*([\d.]+)', text, re.IGNORECASE)
                        tp_match = re.search(r'(?:TP|T\.P|TARGET|Take Profit)\s*:?\s*([\d.]+)', text, re.IGNORECASE)
                        sl_match = re.search(r'(?:SL|S\.L|STOP|Stop Loss)\s*:?\s*([\d.]+)', text, re.IGNORECASE)
                        
                        if entry_match and tp_match and sl_match:
                            try:
                                entry = float(entry_match.group(1))
                                tp = float(tp_match.group(1))
                                sl = float(sl_match.group(1))
                                
                                # Calculate R:R
                                if side == 'BUY':
                                    risk = entry - sl
                                    reward = tp - entry
                                else:
                                    risk = sl - entry
                                    reward = entry - tp
                                
                                if risk > 0:
                                    rr = reward / risk
                                    
                                    signal = {
                                        'channel': channel.name,
                                        'message_id': msg.id,
                                        'timestamp': msg.date,
                                        'symbol': symbol,
                                        'side': side,
                                        'entry_price': entry,
                                        'stop_loss': sl,
                                        'take_profit': tp,
                                        'risk_reward': rr,
                                        'raw_message': text[:500]  # First 500 chars
                                    }
                                    
                                    signals_found.append(signal)
                                    print(f"Found: {symbol} {side} @ {entry:.2f}, R:R: {rr:.2f}")
                                    
                            except ValueError:
                                pass  # Could not parse numbers
                
                # Format 2: Check for multiple TPs
                elif 'TP' in upper_text and 'SL' in upper_text:
                    # Try to parse structured signals with multiple targets
                    tp_matches = re.findall(r'TP\d?\s*:?\s*([\d.]+)', text, re.IGNORECASE)
                    if tp_matches and len(tp_matches) > 0:
                        # Use first TP for conservative R:R calculation
                        pass  # Already handled above
        
        await client.disconnect()
        
    except Exception as e:
        print(f"Error: {e}")
        return signals_found
    
    return signals_found

def save_signals_to_db(signals):
    """Save signals to database"""
    
    if not signals:
        print("No signals to save")
        return
    
    conn = sqlite3.connect('trade_log.db')
    cursor = conn.cursor()
    
    saved = 0
    skipped = 0
    
    for signal in signals:
        # Check if already exists
        cursor.execute("""
            SELECT COUNT(*) FROM signal_log 
            WHERE message_id = ? AND channel = ?
        """, (signal['message_id'], signal['channel']))
        
        if cursor.fetchone()[0] == 0:
            # Insert new signal
            cursor.execute("""
                INSERT INTO signal_log 
                (channel, message_id, timestamp, symbol, side, entry_price, 
                 stop_loss, take_profit, signal_type, raw_message, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                signal['channel'],
                signal['message_id'],
                signal['timestamp'],
                signal['symbol'],
                signal['side'],
                signal['entry_price'],
                signal['stop_loss'],
                signal['take_profit'],
                'SPOT',
                signal['raw_message']
            ))
            saved += 1
        else:
            skipped += 1
    
    conn.commit()
    conn.close()
    
    print(f"\nSaved {saved} new signals, skipped {skipped} duplicates")

def analyze_signals():
    """Analyze all signals in database"""
    
    conn = sqlite3.connect('trade_log.db')
    cursor = conn.cursor()
    
    # Get signal statistics
    cursor.execute("""
        SELECT symbol, COUNT(*) as count,
               AVG(CASE 
                   WHEN side = 'BUY' THEN (take_profit - entry_price) / (entry_price - stop_loss)
                   ELSE (entry_price - take_profit) / (stop_loss - entry_price)
               END) as avg_rr,
               MIN(CASE 
                   WHEN side = 'BUY' THEN (take_profit - entry_price) / (entry_price - stop_loss)
                   ELSE (entry_price - take_profit) / (stop_loss - entry_price)
               END) as min_rr,
               MAX(CASE 
                   WHEN side = 'BUY' THEN (take_profit - entry_price) / (entry_price - stop_loss)
                   ELSE (entry_price - take_profit) / (stop_loss - entry_price)
               END) as max_rr
        FROM signal_log 
        WHERE processed = 0
        GROUP BY symbol
        ORDER BY avg_rr DESC
    """)
    
    print("\n" + "="*70)
    print("SIGNAL ANALYSIS")
    print("="*70)
    print(f"{'Symbol':<10} {'Count':>6} {'Avg R:R':>10} {'Min R:R':>10} {'Max R:R':>10}")
    print("-"*50)
    
    total_signals = 0
    for row in cursor.fetchall():
        symbol, count, avg_rr, min_rr, max_rr = row
        if avg_rr:
            print(f"{symbol:<10} {count:>6} {avg_rr:>10.2f} {min_rr:>10.2f} {max_rr:>10.2f}")
            total_signals += count
    
    # Get high quality signals (R:R > 2.5 for Gold/FX, > 2.0 for Crypto)
    cursor.execute("""
        SELECT symbol, side, entry_price, stop_loss, take_profit,
               CASE 
                   WHEN side = 'BUY' THEN (take_profit - entry_price) / (entry_price - stop_loss)
                   ELSE (entry_price - take_profit) / (stop_loss - entry_price)
               END as rr
        FROM signal_log 
        WHERE processed = 0
        AND (
            (symbol IN ('XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY') 
             AND CASE 
                   WHEN side = 'BUY' THEN (take_profit - entry_price) / (entry_price - stop_loss)
                   ELSE (entry_price - take_profit) / (stop_loss - entry_price)
               END >= 2.5)
            OR 
            (symbol NOT IN ('XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY')
             AND CASE 
                   WHEN side = 'BUY' THEN (take_profit - entry_price) / (entry_price - stop_loss)
                   ELSE (entry_price - take_profit) / (stop_loss - entry_price)
               END >= 2.0)
        )
        ORDER BY rr DESC
        LIMIT 10
    """)
    
    high_quality = cursor.fetchall()
    
    print(f"\nTotal signals: {total_signals}")
    print(f"High quality signals: {len(high_quality)}")
    
    if high_quality:
        print("\nTop tradeable signals:")
        for signal in high_quality[:5]:
            symbol, side, entry, sl, tp, rr = signal
            print(f"  {symbol} {side} @ {entry:.2f}, SL: {sl:.2f}, TP: {tp:.2f}, R:R: {rr:.2f}")
    
    conn.close()

async def main():
    """Main function"""
    print("="*70)
    print("PULLING ALL TELEGRAM SIGNALS")
    print("="*70)
    
    # Pull signals
    signals = await pull_all_signals()
    
    print(f"\n{'='*70}")
    print(f"Found {len(signals)} total signals")
    
    if signals:
        # Show summary by symbol
        symbol_counts = {}
        for sig in signals:
            sym = sig['symbol']
            if sym not in symbol_counts:
                symbol_counts[sym] = {'count': 0, 'total_rr': 0}
            symbol_counts[sym]['count'] += 1
            symbol_counts[sym]['total_rr'] += sig['risk_reward']
        
        print("\nSignals by symbol:")
        for sym, data in symbol_counts.items():
            avg_rr = data['total_rr'] / data['count']
            print(f"  {sym}: {data['count']} signals, Avg R:R: {avg_rr:.2f}")
        
        # Save to database
        save_signals_to_db(signals)
    
    # Analyze all signals
    analyze_signals()

if __name__ == "__main__":
    asyncio.run(main())