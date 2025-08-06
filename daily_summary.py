#!/usr/bin/env python3
"""
Daily Trading Summary - Sends summary to Telegram/Email
"""

import sqlite3
import os
from datetime import datetime, date, timedelta
import requests
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DailySummary:
    def __init__(self):
        load_dotenv()
        self.db_path = 'trading.db'
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '7169619484:AAF2Kea4mskf8kWeq4Ugj-Fop7qZ8cGudT8')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '6585156851')
        
    def get_daily_stats(self):
        """Get today's trading statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        today = date.today()
        
        # Get trades
        cursor.execute('''
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN result = 'open' THEN 1 ELSE 0 END) as open,
                   SUM(CASE WHEN result != 'open' THEN 1 ELSE 0 END) as closed
            FROM trades
            WHERE DATE(timestamp) = DATE('now', 'localtime')
        ''')
        trade_stats = cursor.fetchone()
        stats['total_trades'] = trade_stats[0]
        stats['open_positions'] = trade_stats[1]
        stats['closed_trades'] = trade_stats[2]
        
        # Get P&L
        cursor.execute('''
            SELECT SUM(pnl), AVG(pnl), MIN(pnl), MAX(pnl)
            FROM trades
            WHERE DATE(timestamp) = DATE('now', 'localtime')
            AND result != 'open' AND pnl IS NOT NULL
        ''')
        pnl_stats = cursor.fetchone()
        stats['total_pnl'] = pnl_stats[0] or 0
        stats['avg_pnl'] = pnl_stats[1] or 0
        stats['min_pnl'] = pnl_stats[2] or 0
        stats['max_pnl'] = pnl_stats[3] or 0
        
        # Get symbol breakdown
        cursor.execute('''
            SELECT symbol, COUNT(*) as count,
                   SUM(CASE WHEN result != 'open' THEN pnl ELSE 0 END) as pnl
            FROM trades
            WHERE DATE(timestamp) = DATE('now', 'localtime')
            GROUP BY symbol
            ORDER BY count DESC
        ''')
        stats['symbols'] = cursor.fetchall()
        
        # Get signals processed
        cursor.execute('''
            SELECT COUNT(*) FROM signal_log
            WHERE DATE(created_at) = DATE('now', 'localtime')
        ''')
        stats['signals_processed'] = cursor.fetchone()[0]
        
        # Get current open positions detail
        cursor.execute('''
            SELECT symbol, side, entry, tp, sl, timestamp
            FROM trades
            WHERE result = 'open'
            ORDER BY timestamp DESC
            LIMIT 10
        ''')
        stats['open_positions_detail'] = cursor.fetchall()
        
        conn.close()
        return stats
    
    def format_telegram_message(self, stats):
        """Format summary for Telegram"""
        today = date.today().strftime('%B %d, %Y')
        
        message = f"""📊 <b>Daily Trading Summary</b>
📅 {today}

<b>📈 Overview</b>
• Total Trades: {stats['total_trades']}
• Open Positions: {stats['open_positions']}
• Closed Trades: {stats['closed_trades']}
• Signals Processed: {stats['signals_processed']}

<b>💰 Performance</b>"""
        
        if stats['closed_trades'] > 0:
            message += f"""
• Total P&L: {stats['total_pnl']:.2f}%
• Average P&L: {stats['avg_pnl']:.2f}%
• Best Trade: {stats['max_pnl']:.2f}%
• Worst Trade: {stats['min_pnl']:.2f}%"""
        else:
            message += "\n• No closed trades today"
        
        # Symbol breakdown
        if stats['symbols']:
            message += "\n\n<b>🎯 By Symbol</b>"
            for symbol, count, pnl in stats['symbols'][:5]:  # Top 5
                message += f"\n• {symbol}: {count} trades"
                if pnl != 0:
                    message += f" ({pnl:.2f}% P&L)"
        
        # Open positions
        if stats['open_positions'] > 0:
            message += f"\n\n<b>🟢 Open Positions ({stats['open_positions']})</b>"
            for pos in stats['open_positions_detail'][:5]:  # Show top 5
                symbol, side, entry, tp, sl, _ = pos
                target_pct = abs((tp - entry) / entry * 100)
                message += f"\n• {symbol} {side} @ ${entry:.2f} (TP: {target_pct:.2f}%)"
        
        # Add performance indicator
        if stats['total_pnl'] > 0:
            message += "\n\n✅ Profitable Day! Keep it up! 🚀"
        elif stats['total_pnl'] < 0:
            message += "\n\n📉 Down day - Review and adjust strategy"
        else:
            message += "\n\n⏳ Positions still open - Check tomorrow!"
        
        return message
    
    def send_telegram_message(self, message):
        """Send message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data)
            if response.status_code == 200:
                logger.info("Daily summary sent successfully")
                return True
            else:
                logger.error(f"Failed to send message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def run_daily_summary(self):
        """Generate and send daily summary"""
        logger.info("Generating daily trading summary...")
        
        stats = self.get_daily_stats()
        
        if stats['total_trades'] == 0:
            message = f"""📊 <b>Daily Trading Summary</b>
📅 {date.today().strftime('%B %d, %Y')}

No trades executed today.
Signals processed: {stats['signals_processed']}

Check your settings and ensure automated trading is enabled."""
        else:
            message = self.format_telegram_message(stats)
        
        # Send to Telegram
        if self.send_telegram_message(message):
            logger.info("Daily summary sent to Telegram")
        
        # Could also send email here if configured
        
        return message

if __name__ == "__main__":
    summary = DailySummary()
    summary.run_daily_summary()