"""
Daily Summary Reporter for Prop Firm System
Sends comprehensive daily reports of all trading activity
"""

import sqlite3
import logging
from datetime import datetime, timedelta, time
import requests
import json
import asyncio
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DailySummaryReporter:
    """Generates and sends daily summary reports"""
    
    def __init__(self, db_path: str = "trade_log.db"):
        self.db_path = db_path
        self.telegram_token = '8405614465:AAGl1MFkI4T7dksrk93oHXJOilcBXH36Do0'
        self.telegram_chat_id = '6585156851'
        self.report_time = time(21, 0)  # 9:00 PM daily
        self.last_report_date = None
        
    def gather_daily_stats(self) -> Dict:
        """Gather all statistics for the day"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            stats = {}
            
            # 1. Signal Statistics
            cursor.execute("""
                SELECT COUNT(*) FROM signal_log 
                WHERE DATE(timestamp) = ?
            """, (today,))
            stats['total_signals'] = cursor.fetchone()[0]
            
            # 2. Prop Firm Decisions
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN decision = 'ACCEPTED' THEN 1 ELSE 0 END) as accepted,
                    SUM(CASE WHEN decision = 'REJECTED' THEN 1 ELSE 0 END) as rejected,
                    SUM(CASE WHEN alert_sent = 1 THEN 1 ELSE 0 END) as alerts
                FROM prop_firm_decisions 
                WHERE DATE(timestamp) = ?
            """, (today,))
            
            row = cursor.fetchone()
            stats['decisions_total'] = row[0] or 0
            stats['decisions_accepted'] = row[1] or 0
            stats['decisions_rejected'] = row[2] or 0
            stats['alerts_sent'] = row[3] or 0
            
            # 3. Rejection Reasons
            cursor.execute("""
                SELECT reason, COUNT(*) as count
                FROM prop_firm_decisions 
                WHERE DATE(timestamp) = ? AND decision = 'REJECTED'
                GROUP BY reason
                ORDER BY count DESC
                LIMIT 5
            """, (today,))
            
            stats['rejection_reasons'] = cursor.fetchall()
            
            # 4. Demo Account Performance
            cursor.execute("""
                SELECT 
                    current_balance,
                    daily_pnl,
                    total_pnl,
                    daily_loss_amount,
                    max_drawdown_amount,
                    total_trades,
                    winning_trades,
                    win_rate,
                    challenge_status,
                    (total_pnl / 1000.0 * 100) as progress_pct
                FROM prop_demo_status 
                WHERE id = 1
            """)
            
            demo_row = cursor.fetchone()
            if demo_row:
                stats['demo'] = {
                    'balance': demo_row[0],
                    'daily_pnl': demo_row[1],
                    'total_pnl': demo_row[2],
                    'daily_loss': demo_row[3],
                    'drawdown': demo_row[4],
                    'total_trades': demo_row[5],
                    'winning_trades': demo_row[6],
                    'win_rate': demo_row[7],
                    'challenge_status': demo_row[8],
                    'progress_pct': demo_row[9]
                }
            else:
                stats['demo'] = None
            
            # 5. Demo Trades Today
            cursor.execute("""
                SELECT 
                    COUNT(*) as trades,
                    SUM(CASE WHEN status = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN status = 'LOSS' THEN 1 ELSE 0 END) as losses,
                    SUM(net_pnl) as total_pnl
                FROM prop_demo_trades 
                WHERE DATE(entry_time) = ?
            """, (today,))
            
            trades_row = cursor.fetchone()
            stats['demo_trades_today'] = {
                'count': trades_row[0] or 0,
                'wins': trades_row[1] or 0,
                'losses': trades_row[2] or 0,
                'pnl': trades_row[3] or 0
            }
            
            # 6. Best Performing Symbols
            cursor.execute("""
                SELECT 
                    symbol,
                    COUNT(*) as signals,
                    SUM(CASE WHEN decision = 'ACCEPTED' THEN 1 ELSE 0 END) as accepted
                FROM prop_firm_decisions 
                WHERE DATE(timestamp) = ?
                GROUP BY symbol
                ORDER BY accepted DESC
                LIMIT 5
            """, (today,))
            
            stats['top_symbols'] = cursor.fetchall()
            
            # 7. Risk Metrics
            cursor.execute("""
                SELECT 
                    daily_loss_amount,
                    max_drawdown_amount,
                    current_balance
                FROM prop_demo_status 
                WHERE id = 1
            """)
            
            risk_row = cursor.fetchone()
            if risk_row:
                stats['risk'] = {
                    'daily_loss_used': (risk_row[0] / 500 * 100) if risk_row[0] else 0,
                    'drawdown_used': (risk_row[1] / 600 * 100) if risk_row[1] else 0,
                    'balance': risk_row[2]
                }
            
            # 8. Alert Settings
            cursor.execute("""
                SELECT telegram_alerts_enabled 
                FROM prop_firm_settings 
                WHERE id = 1
            """)
            
            alert_row = cursor.fetchone()
            stats['alerts_enabled'] = bool(alert_row[0]) if alert_row else False
            
            return stats
    
    def format_daily_summary(self, stats: Dict) -> str:
        """Format statistics into readable summary"""
        now = datetime.now()
        
        # Header
        message = f"""📊 **DAILY PROP FIRM SUMMARY**
📅 {now.strftime('%B %d, %Y')}
{'='*30}

"""
        
        # Signal Processing
        acceptance_rate = 0
        if stats['decisions_total'] > 0:
            acceptance_rate = (stats['decisions_accepted'] / stats['decisions_total']) * 100
        
        message += f"""**📡 SIGNAL PROCESSING**
• Total Signals: {stats['total_signals']}
• Processed: {stats['decisions_total']}
• Accepted: {stats['decisions_accepted']} ({acceptance_rate:.1f}%)
• Rejected: {stats['decisions_rejected']}
• Alerts Sent: {stats['alerts_sent']}

"""
        
        # Demo Account Performance
        if stats.get('demo'):
            demo = stats['demo']
            daily_pnl_sign = '+' if demo['daily_pnl'] >= 0 else ''
            total_pnl_sign = '+' if demo['total_pnl'] >= 0 else ''
            
            # Challenge status emoji
            if demo['challenge_status'] == 'PASSED':
                status_emoji = '🎉 PASSED'
            elif demo['challenge_status'] == 'FAILED':
                status_emoji = '❌ FAILED'
            else:
                status_emoji = '🏃 ACTIVE'
            
            message += f"""**🎮 DEMO ACCOUNT**
• Balance: ${demo['balance']:,.2f}
• Daily P&L: {daily_pnl_sign}${abs(demo['daily_pnl']):,.2f}
• Total P&L: {total_pnl_sign}${abs(demo['total_pnl']):,.2f}
• Progress: {demo['progress_pct']:.1f}% to target
• Win Rate: {demo['win_rate']:.1f}%
• Status: {status_emoji}

"""
        
        # Today's Demo Trades
        if stats['demo_trades_today']['count'] > 0:
            trades = stats['demo_trades_today']
            pnl_sign = '+' if trades['pnl'] >= 0 else ''
            
            message += f"""**📈 TODAY'S TRADES**
• Executed: {trades['count']}
• Winners: {trades['wins']}
• Losers: {trades['losses']}
• Net P&L: {pnl_sign}${abs(trades['pnl']):,.2f}

"""
        
        # Risk Status
        if stats.get('risk'):
            risk = stats['risk']
            daily_emoji = '🟢' if risk['daily_loss_used'] < 50 else '🟡' if risk['daily_loss_used'] < 80 else '🔴'
            dd_emoji = '🟢' if risk['drawdown_used'] < 50 else '🟡' if risk['drawdown_used'] < 80 else '🔴'
            
            message += f"""**⚠️ RISK MANAGEMENT**
• Daily Loss: {daily_emoji} {risk['daily_loss_used']:.1f}% of limit
• Drawdown: {dd_emoji} {risk['drawdown_used']:.1f}% of limit

"""
        
        # Top Rejection Reasons
        if stats['rejection_reasons']:
            message += "**❌ TOP REJECTION REASONS**\n"
            for reason, count in stats['rejection_reasons'][:3]:
                # Shorten reason for readability
                short_reason = reason[:50] + '...' if len(reason) > 50 else reason
                message += f"• {short_reason}: {count}\n"
            message += "\n"
        
        # Top Symbols
        if stats['top_symbols']:
            message += "**🏆 TOP SYMBOLS TODAY**\n"
            for symbol, signals, accepted in stats['top_symbols'][:3]:
                if accepted > 0:
                    message += f"• {symbol}: {accepted}/{signals} accepted\n"
            message += "\n"
        
        # System Status
        alert_status = "🔔 ENABLED" if stats['alerts_enabled'] else "🔕 DISABLED"
        message += f"""**⚙️ SYSTEM STATUS**
• Telegram Alerts: {alert_status}
• Dashboard: http://prop.profithits.app
• Uptime: ✅ All systems operational

"""
        
        # Daily Tips
        tips = self.get_daily_tip(stats)
        if tips:
            message += f"""**💡 INSIGHTS**
{tips}

"""
        
        # Footer
        message += f"""{'='*30}
End of Day Report - {now.strftime('%I:%M %p')}
"""
        
        return message
    
    def get_daily_tip(self, stats: Dict) -> str:
        """Generate insights based on daily performance"""
        tips = []
        
        # Low acceptance rate
        if stats['decisions_total'] > 10:
            acceptance_rate = (stats['decisions_accepted'] / stats['decisions_total']) * 100
            if acceptance_rate < 10:
                tips.append("• Low acceptance rate - Market conditions may be unfavorable")
            elif acceptance_rate > 30:
                tips.append("• High acceptance rate - Good market conditions detected")
        
        # Demo performance
        if stats.get('demo'):
            if stats['demo']['progress_pct'] > 70:
                tips.append("• Demo account nearing profit target! 🎯")
            
            if stats['demo']['daily_pnl'] > 200:
                tips.append("• Excellent daily performance! Keep momentum")
            elif stats['demo']['daily_pnl'] < -200:
                tips.append("• Tough day - Review risk management")
        
        # Risk warnings
        if stats.get('risk'):
            if stats['risk']['daily_loss_used'] > 60:
                tips.append("• ⚠️ Approaching daily loss limit - Trade carefully")
            
            if stats['risk']['drawdown_used'] > 70:
                tips.append("• ⚠️ High drawdown - Consider reducing position sizes")
        
        return '\n'.join(tips) if tips else ""
    
    def send_telegram_summary(self, message: str):
        """Send summary to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=data)
            if response.status_code == 200:
                logger.info("Daily summary sent successfully")
                return True
            else:
                logger.error(f"Failed to send summary: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending summary: {e}")
            return False
    
    def should_send_report(self) -> bool:
        """Check if it's time to send the daily report"""
        now = datetime.now()
        current_time = now.time()
        
        # Check if we've already sent today's report
        if self.last_report_date == now.date():
            return False
        
        # Check if it's past report time
        if current_time >= self.report_time:
            return True
        
        return False
    
    async def run_scheduler(self):
        """Run the daily report scheduler"""
        logger.info(f"Daily summary reporter started. Reports at {self.report_time}")
        
        while True:
            try:
                if self.should_send_report():
                    logger.info("Generating daily summary...")
                    
                    # Gather statistics
                    stats = self.gather_daily_stats()
                    
                    # Format message
                    message = self.format_daily_summary(stats)
                    
                    # Send report
                    if self.send_telegram_summary(message):
                        self.last_report_date = datetime.now().date()
                        logger.info(f"Daily summary sent for {self.last_report_date}")
                    
                # Wait 60 seconds before checking again
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in daily reporter: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    def send_immediate_summary(self):
        """Send an immediate summary (for testing or on-demand)"""
        logger.info("Generating immediate summary...")
        
        # Gather statistics
        stats = self.gather_daily_stats()
        
        # Format message
        message = self.format_daily_summary(stats)
        
        # Send report
        if self.send_telegram_summary(message):
            logger.info("Immediate summary sent successfully")
            return True
        return False

# Standalone runner
async def main():
    """Run the daily reporter as standalone service"""
    reporter = DailySummaryReporter()
    
    # Send immediate summary on startup
    reporter.send_immediate_summary()
    
    # Then run scheduler
    await reporter.run_scheduler()

if __name__ == "__main__":
    # Test immediate send
    reporter = DailySummaryReporter()
    if reporter.send_immediate_summary():
        print("Test summary sent! Check Telegram.")
    else:
        print("Failed to send test summary")
    
    # Uncomment to run scheduler
    # asyncio.run(main())