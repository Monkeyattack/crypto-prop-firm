"""
Mock Telegram API for testing
"""

from unittest.mock import Mock
from typing import Dict, List, Any
from datetime import datetime
import json


class MockTelegramBot:
    """Mock Telegram Bot API for testing"""
    
    def __init__(self, token: str = "test_token"):
        self.token = token
        self.sent_messages = []
        self.should_fail = False
        self.fail_count = 0
        self.total_calls = 0
    
    def send_message(self, chat_id: str, text: str, parse_mode: str = 'HTML') -> Dict[str, Any]:
        """Mock send_message API call"""
        self.total_calls += 1
        
        if self.should_fail:
            self.fail_count += 1
            return {
                'ok': False,
                'error_code': 400,
                'description': 'Bad Request: chat not found'
            }
        
        message_id = len(self.sent_messages) + 1
        message = {
            'message_id': message_id,
            'chat': {'id': int(chat_id), 'type': 'private'},
            'date': int(datetime.now().timestamp()),
            'text': text,
            'parse_mode': parse_mode
        }
        
        self.sent_messages.append(message)
        
        return {
            'ok': True,
            'result': message
        }
    
    def get_sent_messages(self) -> List[Dict]:
        """Get all sent messages"""
        return self.sent_messages.copy()
    
    def get_last_message(self) -> Dict:
        """Get the last sent message"""
        return self.sent_messages[-1] if self.sent_messages else None
    
    def clear_messages(self):
        """Clear sent messages history"""
        self.sent_messages.clear()
        self.fail_count = 0
        self.total_calls = 0
    
    def set_should_fail(self, fail: bool):
        """Set whether API calls should fail"""
        self.should_fail = fail
    
    def get_stats(self) -> Dict[str, int]:
        """Get bot statistics"""
        return {
            'total_calls': self.total_calls,
            'successful_calls': self.total_calls - self.fail_count,
            'failed_calls': self.fail_count,
            'messages_sent': len(self.sent_messages)
        }
    
    def find_messages_containing(self, text: str) -> List[Dict]:
        """Find messages containing specific text"""
        return [msg for msg in self.sent_messages if text.lower() in msg['text'].lower()]
    
    def find_messages_by_type(self, message_type: str) -> List[Dict]:
        """Find messages by type (based on emojis/keywords)"""
        type_keywords = {
            'signal': ['NEW SIGNAL DETECTED', '📡'],
            'trade_open': ['TRADE OPENED', '🚀'],
            'trade_close': ['TRADE CLOSED', '💰', '📉'],
            'error': ['SYSTEM ALERT', '🚨'],
            'summary': ['DAILY TRADING SUMMARY', '📊']
        }
        
        keywords = type_keywords.get(message_type, [])
        return [
            msg for msg in self.sent_messages 
            if any(keyword in msg['text'] for keyword in keywords)
        ]


class MockTelegramNotifier:
    """Mock TelegramNotifier class for testing"""
    
    def __init__(self):
        self.bot = MockTelegramBot()
        self.notifications_sent = 0
        self.last_notification_type = None
    
    def send_message(self, text: str, parse_mode: str = 'HTML') -> bool:
        """Mock send_message method"""
        result = self.bot.send_message('12345', text, parse_mode)
        return result.get('ok', False)
    
    def notify_new_signal(self, signal: Dict[str, Any]):
        """Mock notify_new_signal"""
        self.notifications_sent += 1
        self.last_notification_type = 'new_signal'
        
        message = f"""
📡 NEW SIGNAL DETECTED

Symbol: {signal.get('symbol', 'Unknown')}
Side: {signal.get('side', 'Unknown')}
Entry: ${signal.get('entry_price', 0)}
Take Profit: ${signal.get('take_profit', 0)}
Stop Loss: ${signal.get('stop_loss', 0)}
"""
        return self.send_message(message)
    
    def notify_signal_processed(self, signal: Dict[str, Any], trade_executed: bool, reason: str = None):
        """Mock notify_signal_processed"""
        self.notifications_sent += 1
        self.last_notification_type = 'signal_processed'
        
        status = "EXECUTED" if trade_executed else "REJECTED"
        message = f"""
✅ SIGNAL {status}

Symbol: {signal.get('symbol', 'Unknown')}
Side: {signal.get('side', 'Unknown')}
"""
        
        if not trade_executed and reason:
            message += f"\nReason: {reason}"
        
        return self.send_message(message)
    
    def notify_trade_opened(self, trade: Dict[str, Any]):
        """Mock notify_trade_opened"""
        self.notifications_sent += 1
        self.last_notification_type = 'trade_opened'
        
        message = f"""
🚀 TRADE OPENED

Symbol: {trade.get('symbol', 'Unknown')}
Side: {trade.get('side', 'Unknown')}
Entry: ${trade.get('entry', 0)}
Position Size: ${trade.get('position_size', 1000)}
Trade ID: #{trade.get('id', 'N/A')}
"""
        return self.send_message(message)
    
    def notify_trade_closed(self, trade: Dict[str, Any]):
        """Mock notify_trade_closed"""
        self.notifications_sent += 1
        self.last_notification_type = 'trade_closed'
        
        pnl = trade.get('pnl', 0)
        result = "PROFIT" if pnl > 0 else "LOSS"
        emoji = "💰" if pnl > 0 else "📉"
        
        message = f"""
{emoji} TRADE CLOSED - {result}

Symbol: {trade.get('symbol', 'Unknown')}
Entry: ${trade.get('entry', 0)}
Exit: ${trade.get('exit_price', 0)}
P&L: ${pnl:.2f}
Trade ID: #{trade.get('id', 'N/A')}
"""
        return self.send_message(message)
    
    def notify_error(self, error_type: str, details: str):
        """Mock notify_error"""
        self.notifications_sent += 1
        self.last_notification_type = 'error'
        
        message = f"""
🚨 SYSTEM ALERT

Error Type: {error_type}
Details: {details}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(message)
    
    def get_sent_messages(self) -> List[Dict]:
        """Get all sent messages"""
        return self.bot.get_sent_messages()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        bot_stats = self.bot.get_stats()
        return {
            **bot_stats,
            'notifications_sent': self.notifications_sent,
            'last_notification_type': self.last_notification_type
        }
    
    def clear_history(self):
        """Clear notification history"""
        self.bot.clear_messages()
        self.notifications_sent = 0
        self.last_notification_type = None
    
    def set_should_fail(self, fail: bool):
        """Set whether notifications should fail"""
        self.bot.set_should_fail(fail)


# Global mock instances
mock_telegram_bot = MockTelegramBot()
mock_telegram_notifier = MockTelegramNotifier()