#!/usr/bin/env python3
"""
Telegram Notification System for Crypto Trading
Sends detailed notifications for all trading events
"""

import os
import logging
import requests
from datetime import datetime
from typing import Dict, Optional, Any
import json

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Emoji mappings for visual notifications
        self.emojis = {
            'new_signal': '📡',
            'signal_processed': '✅',
            'signal_failed': '❌',
            'trade_opened': '🚀',
            'trade_closed_profit': '💰',
            'trade_closed_loss': '📉',
            'trade_closed_manual': '🛑',
            'tp_hit': '🎯',
            'sl_hit': '🔴',
            'trailing_activated': '📈',
            'warning': '⚠️',
            'info': 'ℹ️',
            'error': '🚨'
        }
        
    def send_message(self, text: str, parse_mode: str = 'HTML') -> bool:
        """Send a message to Telegram"""
        try:
            params = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            
            response = requests.post(f"{self.base_url}/sendMessage", params=params)
            
            if response.status_code == 200:
                logging.info("Telegram notification sent successfully")
                return True
            else:
                logging.error(f"Failed to send Telegram notification: {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"Error sending Telegram notification: {e}")
            return False
    
    def format_price(self, price: float) -> str:
        """Format price for display"""
        if price > 100:
            return f"${price:,.2f}"
        elif price > 1:
            return f"${price:.4f}"
        else:
            return f"${price:.8f}"
    
    def notify_new_signal(self, signal: Dict[str, Any]):
        """Notify when a new signal is detected"""
        emoji = self.emojis['new_signal']
        
        message = f"""
{emoji} <b>NEW SIGNAL DETECTED</b>

<b>Symbol:</b> {signal.get('symbol', 'Unknown')}
<b>Side:</b> {signal.get('side', 'Unknown')}
<b>Entry:</b> {self.format_price(signal.get('entry_price', 0))}
<b>Take Profit:</b> {self.format_price(signal.get('take_profit', 0))}
<b>Stop Loss:</b> {self.format_price(signal.get('stop_loss', 0))}
<b>Source:</b> {signal.get('channel', 'Unknown')}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Strategy Analysis:</b>
• Risk/Reward: {signal.get('risk_reward_ratio', 'N/A')}
• Position Size: ${signal.get('position_size', 1000)}
• Modified TP: {self.format_price(signal.get('modified_tp', signal.get('take_profit', 0)))} (5% target)
• Modified SL: {self.format_price(signal.get('modified_sl', signal.get('stop_loss', 0)))} (5% max loss)
• Trailing TP: Enabled at 3% profit
"""
        
        self.send_message(message)
    
    def notify_signal_processed(self, signal: Dict[str, Any], trade_executed: bool, reason: Optional[str] = None):
        """Notify when a signal is processed"""
        if trade_executed:
            emoji = self.emojis['signal_processed']
            status = "EXECUTED"
        else:
            emoji = self.emojis['signal_failed']
            status = "REJECTED"
        
        message = f"""
{emoji} <b>SIGNAL {status}</b>

<b>Symbol:</b> {signal.get('symbol', 'Unknown')}
<b>Side:</b> {signal.get('side', 'Unknown')}
"""
        
        if trade_executed:
            message += f"""
<b>Entry Price:</b> {self.format_price(signal.get('actual_entry', signal.get('entry_price', 0)))}
<b>Position Size:</b> ${signal.get('position_size', 1000)}
<b>Trade ID:</b> #{signal.get('trade_id', 'N/A')}
"""
        else:
            message += f"""
<b>Reason:</b> {reason or 'Unknown'}
<b>Details:</b>
• Max open trades: {signal.get('open_trades', 0)}/{signal.get('max_trades', 10)}
• Daily trades: {signal.get('daily_trades', 0)}/{signal.get('max_daily', 10)}
• Market conditions: {signal.get('market_status', 'Normal')}
"""
        
        self.send_message(message)
    
    def notify_trade_opened(self, trade: Dict[str, Any]):
        """Notify when a trade is opened"""
        emoji = self.emojis['trade_opened']
        
        # Calculate profit targets
        entry = trade.get('entry', 0)
        tp = trade.get('tp', 0)
        sl = trade.get('sl', 0)
        
        if trade.get('side', '').upper() in ['BUY', 'LONG']:
            tp_pct = ((tp - entry) / entry) * 100 if entry > 0 else 0
            sl_pct = ((entry - sl) / entry) * 100 if entry > 0 else 0
        else:
            tp_pct = ((entry - tp) / entry) * 100 if entry > 0 else 0
            sl_pct = ((sl - entry) / entry) * 100 if entry > 0 else 0
        
        message = f"""
{emoji} <b>TRADE OPENED</b>

<b>Symbol:</b> {trade.get('symbol', 'Unknown')}
<b>Side:</b> {trade.get('side', 'Unknown')}
<b>Entry:</b> {self.format_price(entry)}
<b>Position Size:</b> ${trade.get('position_size', 1000)}

<b>Targets:</b>
• Take Profit: {self.format_price(tp)} (+{tp_pct:.2f}%)
• Stop Loss: {self.format_price(sl)} (-{sl_pct:.2f}%)

<b>Risk Management:</b>
• Trailing TP: Activates at +3%
• Target: 5% (fallback to 3.5%)
• Max Risk: ${trade.get('position_size', 1000) * sl_pct / 100:.2f}

<b>Trade ID:</b> #{trade.get('id', 'N/A')}
"""
        
        self.send_message(message)
    
    def notify_trade_closed(self, trade: Dict[str, Any]):
        """Notify when a trade is closed"""
        pnl = trade.get('pnl', 0)
        pnl_pct = trade.get('pnl_pct', 0)
        
        if pnl > 0:
            emoji = self.emojis['trade_closed_profit']
            result = "PROFIT"
        else:
            emoji = self.emojis['trade_closed_loss']
            result = "LOSS"
        
        exit_reason = trade.get('exit_reason', 'manual')
        if exit_reason == 'tp':
            exit_emoji = self.emojis['tp_hit']
            exit_text = "Take Profit Hit"
        elif exit_reason == 'sl':
            exit_emoji = self.emojis['sl_hit']
            exit_text = "Stop Loss Hit"
        elif exit_reason == 'trailing':
            exit_emoji = self.emojis['trailing_activated']
            exit_text = "Trailing Stop Hit"
        else:
            exit_emoji = self.emojis['trade_closed_manual']
            exit_text = "Manual Close"
        
        message = f"""
{emoji} <b>TRADE CLOSED - {result}</b>

<b>Symbol:</b> {trade.get('symbol', 'Unknown')}
<b>Side:</b> {trade.get('side', 'Unknown')}

<b>Entry:</b> {self.format_price(trade.get('entry', 0))}
<b>Exit:</b> {self.format_price(trade.get('exit_price', 0))}
<b>Exit Reason:</b> {exit_emoji} {exit_text}

<b>Results:</b>
• P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)
• Duration: {trade.get('duration', 'N/A')}
• Max Profit: {trade.get('max_profit_pct', 0):+.2f}%
• Max Drawdown: {trade.get('max_drawdown_pct', 0):.2f}%

<b>Account Update:</b>
• New Balance: ${trade.get('new_balance', 10000):.2f}
• Total P&L Today: ${trade.get('daily_pnl', 0):.2f}
• Win Rate: {trade.get('win_rate', 0):.1f}%

<b>Trade ID:</b> #{trade.get('id', 'N/A')}
"""
        
        self.send_message(message)
    
    def notify_trailing_update(self, trade: Dict[str, Any]):
        """Notify when trailing stop is updated"""
        emoji = self.emojis['trailing_activated']
        
        message = f"""
{emoji} <b>TRAILING STOP UPDATED</b>

<b>Symbol:</b> {trade.get('symbol', 'Unknown')}
<b>Current Price:</b> {self.format_price(trade.get('current_price', 0))}
<b>Current Profit:</b> +{trade.get('current_profit_pct', 0):.2f}%

<b>Stop Loss Updated:</b>
• Old SL: {self.format_price(trade.get('old_sl', 0))}
• New SL: {self.format_price(trade.get('new_sl', 0))}
• Locked Profit: +{trade.get('locked_profit_pct', 0):.2f}%

<b>Trade ID:</b> #{trade.get('id', 'N/A')}
"""
        
        self.send_message(message)
    
    def notify_daily_summary(self, summary: Dict[str, Any]):
        """Send daily trading summary"""
        message = f"""
📊 <b>DAILY TRADING SUMMARY</b>
{datetime.now().strftime('%Y-%m-%d')}

<b>Trading Activity:</b>
• Signals Received: {summary.get('signals_received', 0)}
• Trades Executed: {summary.get('trades_executed', 0)}
• Trades Closed: {summary.get('trades_closed', 0)}
• Open Positions: {summary.get('open_positions', 0)}

<b>Performance:</b>
• Daily P&L: ${summary.get('daily_pnl', 0):.2f}
• Win Rate: {summary.get('win_rate', 0):.1f}%
• Best Trade: ${summary.get('best_trade', 0):.2f}
• Worst Trade: ${summary.get('worst_trade', 0):.2f}

<b>Account Status:</b>
• Starting Balance: ${summary.get('start_balance', 10000):.2f}
• Current Balance: ${summary.get('current_balance', 10000):.2f}
• Total ROI: {summary.get('total_roi', 0):.2f}%

<b>Top Performers:</b>
{summary.get('top_symbols', 'No trades today')}

<b>Risk Metrics:</b>
• Max Drawdown: {summary.get('max_drawdown', 0):.2f}%
• Sharpe Ratio: {summary.get('sharpe_ratio', 0):.2f}
• Avg Risk/Reward: {summary.get('avg_rr', 0):.2f}
"""
        
        self.send_message(message)
    
    def notify_error(self, error_type: str, details: str):
        """Notify about system errors"""
        emoji = self.emojis['error']
        
        message = f"""
{emoji} <b>SYSTEM ALERT</b>

<b>Error Type:</b> {error_type}
<b>Details:</b> {details}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please check the system logs for more information.
"""
        
        self.send_message(message)

# Create global notifier instance
notifier = TelegramNotifier()

if __name__ == "__main__":
    # Test notifications
    print("Testing Telegram notifications...")
    
    # Test signal notification
    test_signal = {
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'entry_price': 65000,
        'take_profit': 68250,
        'stop_loss': 61750,
        'channel': 'Test Channel',
        'risk_reward_ratio': '1:1',
        'position_size': 1000
    }
    
    notifier.notify_new_signal(test_signal)
    print("Test notification sent!")