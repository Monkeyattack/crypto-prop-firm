"""
Integration tests for Telegram notification system
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
import time
from datetime import datetime

from telegram_notifier import TelegramNotifier
from tests.mocks.mock_telegram import MockTelegramNotifier


@pytest.mark.integration
class TestTelegramIntegration:
    """Test Telegram notification integration"""
    
    @pytest.fixture
    def mock_notifier(self):
        """Create mock Telegram notifier"""
        return MockTelegramNotifier()
    
    @pytest.fixture
    def real_notifier(self):
        """Create real TelegramNotifier with test credentials"""
        with patch.dict('os.environ', {
            'TELEGRAM_BOT_TOKEN': 'test_token_123',
            'TELEGRAM_CHAT_ID': '12345'
        }):
            return TelegramNotifier()
    
    def test_telegram_notifier_initialization(self, real_notifier):
        """Test TelegramNotifier initialization with environment variables"""
        assert real_notifier.bot_token == 'test_token_123'
        assert real_notifier.chat_id == '12345'
        assert real_notifier.base_url == 'https://api.telegram.org/bottest_token_123'
        assert len(real_notifier.emojis) > 0
    
    def test_format_price_various_ranges(self, real_notifier):
        """Test price formatting for different price ranges"""
        # High value cryptocurrencies
        assert real_notifier.format_price(45000.0) == "$45,000.00"
        assert real_notifier.format_price(1234.56) == "$1,234.56"
        
        # Medium value cryptocurrencies
        assert real_notifier.format_price(2.5678) == "$2.5678"
        assert real_notifier.format_price(0.1234) == "$0.1234"
        
        # Low value cryptocurrencies (many decimal places)
        assert real_notifier.format_price(0.00001234) == "$0.00001234"
        assert real_notifier.format_price(0.000000012) == "$0.00000001"
    
    @patch('requests.post')
    def test_send_message_success(self, mock_post, real_notifier):
        """Test successful message sending"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'ok': True, 'result': {'message_id': 123}}
        mock_post.return_value = mock_response
        
        result = real_notifier.send_message("Test message")
        
        assert result is True
        mock_post.assert_called_once()
        
        # Verify request parameters
        call_args = mock_post.call_args
        assert 'sendMessage' in call_args[0][0]
        assert call_args[1]['params']['chat_id'] == '12345'
        assert call_args[1]['params']['text'] == 'Test message'
        assert call_args[1]['params']['parse_mode'] == 'HTML'
    
    @patch('requests.post')
    def test_send_message_failure(self, mock_post, real_notifier):
        """Test message sending failure"""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request: chat not found'
        mock_post.return_value = mock_response
        
        result = real_notifier.send_message("Test message")
        
        assert result is False
    
    @patch('requests.post')
    def test_send_message_network_error(self, mock_post, real_notifier):
        """Test message sending with network error"""
        # Mock network exception
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")
        
        result = real_notifier.send_message("Test message")
        
        assert result is False
    
    def test_notify_new_signal_complete_data(self, mock_notifier):
        """Test new signal notification with complete data"""
        signal = {
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'entry_price': 45000.0,
            'take_profit': 47250.0,
            'stop_loss': 42750.0,
            'channel': 'Test Channel',
            'risk_reward_ratio': '2:1',
            'position_size': 1000,
            'modified_tp': 47250.0,
            'modified_sl': 42750.0
        }
        
        result = mock_notifier.notify_new_signal(signal)
        assert result is True
        
        messages = mock_notifier.get_sent_messages()
        assert len(messages) == 1
        
        message_text = messages[0]['text']
        assert 'NEW SIGNAL DETECTED' in message_text
        assert 'BTCUSDT' in message_text
        assert 'BUY' in message_text
        assert '$45000' in message_text
        assert 'Test Channel' in message_text
    
    def test_notify_signal_processed_executed(self, mock_notifier):
        """Test signal processed notification for executed trade"""
        signal = {
            'symbol': 'ETHUSDT',
            'side': 'SELL',
            'actual_entry': 2800.0,
            'position_size': 1500,
            'trade_id': 'TR001'
        }
        
        result = mock_notifier.notify_signal_processed(signal, trade_executed=True)
        assert result is True
        
        messages = mock_notifier.get_sent_messages()
        assert len(messages) == 1
        
        message_text = messages[0]['text']
        assert 'SIGNAL EXECUTED' in message_text
        assert 'ETHUSDT' in message_text
        assert '$2800' in message_text
        assert 'TR001' in message_text
    
    def test_notify_signal_processed_rejected(self, mock_notifier):
        """Test signal processed notification for rejected trade"""
        signal = {
            'symbol': 'ADAUSDT',
            'side': 'BUY',
            'open_trades': 8,
            'max_trades': 10,
            'daily_trades': 15,
            'max_daily': 20,
            'market_status': 'Volatile'
        }
        
        reason = "Risk management: Too many open positions"
        
        result = mock_notifier.notify_signal_processed(signal, trade_executed=False, reason=reason)
        assert result is True
        
        messages = mock_notifier.get_sent_messages()
        assert len(messages) == 1
        
        message_text = messages[0]['text']
        assert 'SIGNAL REJECTED' in message_text
        assert 'ADAUSDT' in message_text
        assert reason in message_text
        assert '8/10' in message_text  # open_trades/max_trades
        assert '15/20' in message_text  # daily_trades/max_daily
    
    def test_notify_trade_opened(self, mock_notifier):
        """Test trade opened notification"""
        trade = {
            'symbol': 'SOLUSD',
            'side': 'BUY',
            'entry': 167.50,
            'tp': 175.88,
            'sl': 159.13,
            'position_size': 800,
            'id': 'TR002'
        }
        
        result = mock_notifier.notify_trade_opened(trade)
        assert result is True
        
        messages = mock_notifier.get_sent_messages()
        assert len(messages) == 1
        
        message_text = messages[0]['text']
        assert 'TRADE OPENED' in message_text
        assert 'SOLUSD' in message_text
        assert 'BUY' in message_text
        assert '$167.50' in message_text
        assert '$800' in message_text
        assert 'TR002' in message_text
        
        # Check percentage calculations
        assert '+5.00%' in message_text  # TP percentage
        assert '-5.00%' in message_text  # SL percentage
    
    def test_notify_trade_closed_profit(self, mock_notifier):
        """Test trade closed notification with profit"""
        trade = {
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'entry': 45000.0,
            'exit_price': 46800.0,
            'pnl': 180.0,
            'pnl_pct': 4.0,
            'exit_reason': 'tp',
            'duration': '2.5 hours',
            'max_profit_pct': 4.2,
            'max_drawdown_pct': -0.8,
            'new_balance': 10180.0,
            'daily_pnl': 180.0,
            'win_rate': 75.0,
            'id': 'TR003'
        }
        
        result = mock_notifier.notify_trade_closed(trade)
        assert result is True
        
        messages = mock_notifier.get_sent_messages()
        assert len(messages) == 1
        
        message_text = messages[0]['text']
        assert 'TRADE CLOSED - PROFIT' in message_text
        assert 'BTCUSDT' in message_text
        assert '$45000' in message_text
        assert '$46800' in message_text
        assert 'Take Profit Hit' in message_text
        assert '$180.00' in message_text
        assert '+4.00%' in message_text
        assert '$10180.00' in message_text
        assert '75.0%' in message_text
    
    def test_notify_trade_closed_loss(self, mock_notifier):
        """Test trade closed notification with loss"""
        trade = {
            'symbol': 'ETHUSDT',
            'side': 'SELL',
            'entry': 2800.0,
            'exit_price': 2850.0,
            'pnl': -75.0,
            'pnl_pct': -1.8,
            'exit_reason': 'sl',
            'duration': '45 minutes',
            'max_profit_pct': 0.5,
            'max_drawdown_pct': -1.8,
            'new_balance': 9925.0,
            'daily_pnl': -75.0,
            'win_rate': 65.0,
            'id': 'TR004'
        }
        
        result = mock_notifier.notify_trade_closed(trade)
        assert result is True
        
        messages = mock_notifier.get_sent_messages()
        assert len(messages) == 1
        
        message_text = messages[0]['text']
        assert 'TRADE CLOSED - LOSS' in message_text
        assert 'Stop Loss Hit' in message_text
        assert '$-75.00' in message_text
        assert '-1.80%' in message_text
    
    def test_notify_trailing_update(self, mock_notifier):
        """Test trailing stop update notification"""
        trade = {
            'symbol': 'ADAUSDT',
            'current_price': 0.87,
            'current_profit_pct': 3.5,
            'old_sl': 0.80,
            'new_sl': 0.82,
            'locked_profit_pct': 2.0,
            'id': 'TR005'
        }
        
        result = mock_notifier.notify_trailing_update(trade)
        assert result is True
        
        messages = mock_notifier.get_sent_messages()
        assert len(messages) == 1
        
        message_text = messages[0]['text']
        assert 'TRAILING STOP UPDATED' in message_text
        assert 'ADAUSDT' in message_text
        assert '$0.87' in message_text
        assert '+3.50%' in message_text
        assert '$0.80' in message_text  # old SL
        assert '$0.82' in message_text  # new SL
        assert '+2.00%' in message_text  # locked profit
    
    def test_notify_daily_summary(self, mock_notifier):
        """Test daily summary notification"""
        summary = {
            'signals_received': 25,
            'trades_executed': 18,
            'trades_closed': 15,
            'open_positions': 3,
            'daily_pnl': 245.50,
            'win_rate': 73.3,
            'best_trade': 125.0,
            'worst_trade': -45.0,
            'start_balance': 10000.0,
            'current_balance': 10245.50,
            'total_roi': 2.46,
            'top_symbols': '🥇 BTCUSDT (+$85.50)\n🥈 ETHUSDT (+$67.25)\n🥉 ADAUSDT (+$45.75)',
            'max_drawdown': -2.1,
            'sharpe_ratio': 1.45,
            'avg_rr': 2.3
        }
        
        result = mock_notifier.notify_daily_summary(summary)
        assert result is True
        
        messages = mock_notifier.get_sent_messages()
        assert len(messages) == 1
        
        message_text = messages[0]['text']
        assert 'DAILY TRADING SUMMARY' in message_text
        assert '25' in message_text  # signals received
        assert '18' in message_text  # trades executed
        assert '$245.50' in message_text  # daily P&L
        assert '73.3%' in message_text  # win rate
        assert '2.46%' in message_text  # total ROI
        assert 'BTCUSDT (+$85.50)' in message_text
    
    def test_notify_error(self, mock_notifier):
        """Test error notification"""
        error_type = "Database Connection"
        details = "Unable to connect to trading database after 3 retries"
        
        result = mock_notifier.notify_error(error_type, details)
        assert result is True
        
        messages = mock_notifier.get_sent_messages()
        assert len(messages) == 1
        
        message_text = messages[0]['text']
        assert 'SYSTEM ALERT' in message_text
        assert 'Database Connection' in message_text
        assert 'Unable to connect' in message_text
        assert str(datetime.now().year) in message_text
    
    def test_notification_rate_limiting(self, mock_notifier):
        """Test notification system handles rate limiting"""
        # Simulate rapid notifications
        notifications_sent = 0
        
        for i in range(50):  # Send many notifications quickly
            signal = {
                'symbol': f'TEST{i}_USDT',
                'side': 'BUY',
                'entry_price': 1000.0 + i,
                'take_profit': 1100.0 + i,
                'stop_loss': 900.0 + i,
                'channel': 'Test'
            }
            
            if mock_notifier.notify_new_signal(signal):
                notifications_sent += 1
        
        # All should succeed with mock
        assert notifications_sent == 50
        
        messages = mock_notifier.get_sent_messages()
        assert len(messages) == 50
        
        # Verify messages are unique
        symbols = [msg['text'].split('Symbol: ')[1].split('\n')[0] for msg in messages]
        assert len(set(symbols)) == 50  # All unique symbols
    
    def test_notification_failure_handling(self, mock_notifier):
        """Test notification system handles failures gracefully"""
        # Set mock to fail
        mock_notifier.set_should_fail(True)
        
        signal = {
            'symbol': 'FAILUSDT',
            'side': 'BUY',
            'entry_price': 1000.0,
            'take_profit': 1100.0,
            'stop_loss': 900.0
        }
        
        result = mock_notifier.notify_new_signal(signal)
        assert result is False
        
        # Should still track the attempt
        stats = mock_notifier.get_stats()
        assert stats['failed_calls'] > 0
        assert stats['total_calls'] > 0
    
    def test_notification_content_sanitization(self, mock_notifier):
        """Test notification content is properly sanitized"""
        # Test with potentially problematic content
        signal = {
            'symbol': 'TEST<script>alert("xss")</script>USDT',
            'side': 'BUY & SELL',
            'entry_price': 1000.0,
            'take_profit': 1100.0,
            'stop_loss': 900.0,
            'channel': 'Channel with "quotes" & <tags>'
        }
        
        result = mock_notifier.notify_new_signal(signal)
        assert result is True
        
        messages = mock_notifier.get_sent_messages()
        assert len(messages) == 1
        
        message_text = messages[0]['text']
        # Content should be preserved but safely formatted
        assert 'TEST' in message_text
        assert 'USDT' in message_text
        assert 'quotes' in message_text
    
    def test_notification_message_length_limits(self, mock_notifier):
        """Test notifications handle message length limits"""
        # Create very long content
        long_reason = "This is a very long error message that exceeds normal limits. " * 100
        
        result = mock_notifier.notify_error("Long Error", long_reason)
        assert result is True
        
        messages = mock_notifier.get_sent_messages()
        assert len(messages) == 1
        
        # Message should be sent even if long (Telegram API handles truncation)
        message_text = messages[0]['text']
        assert 'Long Error' in message_text
        assert 'very long error message' in message_text
    
    def test_notification_statistics_tracking(self, mock_notifier):
        """Test notification statistics are tracked correctly"""
        # Send various notification types
        signal = {'symbol': 'BTCUSDT', 'side': 'BUY', 'entry_price': 45000, 'take_profit': 47250, 'stop_loss': 42750}
        trade = {'symbol': 'BTCUSDT', 'side': 'BUY', 'entry': 45000, 'tp': 47250, 'sl': 42750, 'id': 'TR001'}
        
        mock_notifier.notify_new_signal(signal)
        mock_notifier.notify_signal_processed(signal, True)
        mock_notifier.notify_trade_opened(trade)
        mock_notifier.notify_trade_closed({**trade, 'pnl': 100, 'exit_price': 46000})
        mock_notifier.notify_error("Test", "Test error")
        
        stats = mock_notifier.get_stats()
        
        assert stats['notifications_sent'] == 5
        assert stats['successful_calls'] == 5
        assert stats['failed_calls'] == 0
        assert stats['messages_sent'] == 5
        
        # Test message type tracking
        messages = mock_notifier.get_sent_messages()
        signal_messages = [msg for msg in messages if 'NEW SIGNAL' in msg['text']]
        assert len(signal_messages) == 1
        
        trade_messages = [msg for msg in messages if 'TRADE OPENED' in msg['text']]
        assert len(trade_messages) == 1
        
        error_messages = [msg for msg in messages if 'SYSTEM ALERT' in msg['text']]
        assert len(error_messages) == 1