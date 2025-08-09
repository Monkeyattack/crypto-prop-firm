"""
Unit tests for SignalProcessor
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from signal_processor import SignalProcessor
from database import Trade


@pytest.mark.unit
class TestSignalProcessor:
    """Test SignalProcessor functionality"""
    
    def test_init(self):
        """Test SignalProcessor initialization"""
        with patch('signal_processor.DatabaseManager') as mock_db:
            processor = SignalProcessor()
            assert processor is not None
            assert len(processor.signal_patterns) == 4
            mock_db.assert_called_once()
    
    def test_parse_signal_format_1_smrt_signals(self, signal_processor):
        """Test parsing SMRT Signals format"""
        message = """BTCUSDT Buy
Entry: 45,000
TP: 47,250
SL: 42,750"""
        
        result = signal_processor.parse_signal(message)
        
        assert result is not None
        assert result['symbol'] == 'BTCUSDT'
        assert result['side'] == 'Buy'
        assert result['entry_price'] == 45000.0
        assert result['take_profit'] == 47250.0
        assert result['stop_loss'] == 42750.0
    
    def test_parse_signal_format_2_standard(self, signal_processor):
        """Test parsing standard Buy/Sell format"""
        message = """Buy ETHUSDT
Entry: 2,800
TP: 2,940
SL: 2,660"""
        
        result = signal_processor.parse_signal(message)
        
        assert result is not None
        assert result['symbol'] == 'ETHUSDT'
        assert result['side'] == 'Buy'
        assert result['entry_price'] == 2800.0
        assert result['take_profit'] == 2940.0
        assert result['stop_loss'] == 2660.0
    
    def test_parse_signal_format_3_compact(self, signal_processor):
        """Test parsing compact format with pipes"""
        message = "Sell ADAUSDT @ 0.85 | TP: 0.81 | SL: 0.89"
        
        result = signal_processor.parse_signal(message)
        
        assert result is not None
        assert result['symbol'] == 'ADAUSDT'
        assert result['side'] == 'Sell'
        assert result['entry_price'] == 0.85
        assert result['take_profit'] == 0.81
        assert result['stop_loss'] == 0.89
    
    def test_parse_signal_format_4_alternative(self, signal_processor):
        """Test parsing alternative format"""
        message = """Long SOLUSD
Entry Price: 167.17
Take Profit: 175.53
Stop Loss: 158.81"""
        
        result = signal_processor.parse_signal(message)
        
        assert result is not None
        assert result['symbol'] == 'SOLUSD'
        assert result['side'] == 'Buy'  # Long normalized to Buy
        assert result['entry_price'] == 167.17
        assert result['take_profit'] == 175.53
        assert result['stop_loss'] == 158.81
    
    def test_parse_signal_with_dollar_sign(self, signal_processor):
        """Test parsing signal with $ in symbol"""
        message = """Buy $BTCUSDT
Entry: 45000
TP: 47250
SL: 42750"""
        
        result = signal_processor.parse_signal(message)
        
        assert result is not None
        assert result['symbol'] == 'BTCUSDT'  # $ should be removed
    
    def test_parse_signal_case_insensitive(self, signal_processor):
        """Test case insensitive parsing"""
        message = """buy ethusdt
entry: 2800
tp: 2940
sl: 2660"""
        
        result = signal_processor.parse_signal(message)
        
        assert result is not None
        assert result['side'] == 'Buy'  # Should be normalized
        assert result['symbol'] == 'ETHUSDT'  # Should be uppercase
    
    def test_parse_signal_invalid_format(self, signal_processor):
        """Test parsing invalid signal format"""
        message = "This is not a valid signal"
        
        result = signal_processor.parse_signal(message)
        
        assert result is None
    
    def test_parse_signal_empty_message(self, signal_processor):
        """Test parsing empty message"""
        result = signal_processor.parse_signal("")
        assert result is None
        
        result = signal_processor.parse_signal("   ")
        assert result is None
    
    def test_parse_price_valid(self, signal_processor):
        """Test price parsing with valid inputs"""
        assert signal_processor._parse_price("45000") == 45000.0
        assert signal_processor._parse_price("45,000") == 45000.0
        assert signal_processor._parse_price("45,000.50") == 45000.5
        assert signal_processor._parse_price("0.85") == 0.85
    
    def test_parse_price_invalid(self, signal_processor):
        """Test price parsing with invalid inputs"""
        with pytest.raises(ValueError):
            signal_processor._parse_price("abc")
        
        with pytest.raises(ValueError):
            signal_processor._parse_price("")
    
    def test_calculate_risk_reward_ratio_buy(self, signal_processor):
        """Test risk-reward ratio calculation for buy orders"""
        # Buy: Entry 100, TP 110, SL 95 = Risk 5, Reward 10, RR = 2.0
        rr = signal_processor._calculate_risk_reward_ratio(100, 110, 95, 'buy')
        assert rr == 2.0
        
        # Buy: Entry 100, TP 105, SL 98 = Risk 2, Reward 5, RR = 2.5
        rr = signal_processor._calculate_risk_reward_ratio(100, 105, 98, 'buy')
        assert rr == 2.5
    
    def test_calculate_risk_reward_ratio_sell(self, signal_processor):
        """Test risk-reward ratio calculation for sell orders"""
        # Sell: Entry 100, TP 95, SL 105 = Risk 5, Reward 5, RR = 1.0
        rr = signal_processor._calculate_risk_reward_ratio(100, 95, 105, 'sell')
        assert rr == 1.0
        
        # Sell: Entry 100, TP 90, SL 102 = Risk 2, Reward 10, RR = 5.0
        rr = signal_processor._calculate_risk_reward_ratio(100, 90, 102, 'sell')
        assert rr == 5.0
    
    def test_calculate_risk_reward_ratio_invalid(self, signal_processor):
        """Test risk-reward ratio calculation with invalid inputs"""
        # Zero risk should return 0
        rr = signal_processor._calculate_risk_reward_ratio(100, 110, 100, 'buy')
        assert rr == 0
        
        # Negative risk should return 0  
        rr = signal_processor._calculate_risk_reward_ratio(100, 110, 105, 'buy')
        assert rr == 0
    
    @patch('signal_processor.Config')
    def test_validate_signal_valid(self, mock_config, signal_processor):
        """Test signal validation with valid signal"""
        mock_config.MIN_RISK_REWARD_RATIO = 1.5
        mock_config.ALLOWED_SYMBOLS = None
        
        signal_data = {
            'symbol': 'BTCUSDT',
            'side': 'Buy',
            'entry': 45000.0,
            'tp': 47250.0,
            'sl': 42750.0
        }
        
        # Mock database to return empty trades (no duplicates)
        signal_processor.db.get_trades_df = Mock(return_value=Mock(empty=True))
        
        is_valid, errors = signal_processor.validate_signal(signal_data)
        
        assert is_valid is True
        assert len(errors) == 0
    
    @patch('signal_processor.Config')
    def test_validate_signal_low_rr_ratio(self, mock_config, signal_processor):
        """Test signal validation with low risk-reward ratio"""
        mock_config.MIN_RISK_REWARD_RATIO = 2.0
        mock_config.ALLOWED_SYMBOLS = None
        
        signal_data = {
            'symbol': 'BTCUSDT',
            'side': 'Buy',
            'entry': 45000.0,
            'tp': 46000.0,  # Low TP for poor RR ratio
            'sl': 42750.0
        }
        
        signal_processor.db.get_trades_df = Mock(return_value=Mock(empty=True))
        
        is_valid, errors = signal_processor.validate_signal(signal_data)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any('Risk-reward ratio' in error for error in errors)
    
    @patch('signal_processor.Config')
    def test_validate_signal_restricted_symbol(self, mock_config, signal_processor):
        """Test signal validation with restricted symbol"""
        mock_config.MIN_RISK_REWARD_RATIO = 1.0
        mock_config.ALLOWED_SYMBOLS = ['BTCUSDT', 'ETHUSDT']
        
        signal_data = {
            'symbol': 'DOGECOIN',  # Not in allowed list
            'side': 'Buy',
            'entry': 0.1,
            'tp': 0.11,
            'sl': 0.09
        }
        
        signal_processor.db.get_trades_df = Mock(return_value=Mock(empty=True))
        
        is_valid, errors = signal_processor.validate_signal(signal_data)
        
        assert is_valid is False
        assert any('not in allowed list' in error for error in errors)
    
    def test_is_duplicate_signal_no_duplicates(self, signal_processor):
        """Test duplicate detection with no duplicates"""
        signal_data = {
            'symbol': 'BTCUSDT',
            'entry': 45000.0
        }
        
        # Mock empty trades dataframe
        signal_processor.db.get_trades_df = Mock(return_value=Mock(empty=True))
        
        is_duplicate = signal_processor._is_duplicate_signal(signal_data)
        assert is_duplicate is False
    
    def test_is_duplicate_signal_with_duplicate(self, signal_processor):
        """Test duplicate detection with actual duplicate"""
        signal_data = {
            'symbol': 'BTCUSDT',
            'entry': 45000.0
        }
        
        # Mock trades dataframe with similar trade
        import pandas as pd
        mock_df = pd.DataFrame([{
            'symbol': 'BTCUSDT',
            'entry': 45100.0,  # Within 1% of 45000
            'result': 'open'
        }])
        
        signal_processor.db.get_trades_df = Mock(return_value=mock_df)
        
        is_duplicate = signal_processor._is_duplicate_signal(signal_data)
        assert is_duplicate is True
    
    def test_is_duplicate_signal_different_symbol(self, signal_processor):
        """Test duplicate detection with different symbol"""
        signal_data = {
            'symbol': 'BTCUSDT',
            'entry': 45000.0
        }
        
        import pandas as pd
        mock_df = pd.DataFrame([{
            'symbol': 'ETHUSDT',  # Different symbol
            'entry': 45000.0,
            'result': 'open'
        }])
        
        signal_processor.db.get_trades_df = Mock(return_value=mock_df)
        
        is_duplicate = signal_processor._is_duplicate_signal(signal_data)
        assert is_duplicate is False
    
    @patch('signal_processor.Config')
    def test_check_risk_management_allowed(self, mock_config, signal_processor):
        """Test risk management check when trading is allowed"""
        mock_config.MAX_OPEN_TRADES = 5
        mock_config.INITIAL_CAPITAL = 10000
        
        # Mock fewer than max open trades
        import pandas as pd
        mock_df = pd.DataFrame([{
            'result': 'open'
        }] * 3)  # 3 open trades < 5 max
        
        signal_processor.db.get_trades_df = Mock(return_value=mock_df)
        signal_processor.db.get_current_capital = Mock(return_value=8000.0)  # Above 50% minimum
        
        result = signal_processor._check_risk_management()
        
        assert result['allowed'] is True
        assert result['reason'] == 'OK'
    
    @patch('signal_processor.Config')
    def test_check_risk_management_max_trades(self, mock_config, signal_processor):
        """Test risk management check when max trades reached"""
        mock_config.MAX_OPEN_TRADES = 3
        mock_config.INITIAL_CAPITAL = 10000
        
        # Mock max open trades reached
        import pandas as pd
        mock_df = pd.DataFrame([{
            'result': 'open'
        }] * 3)  # 3 open trades = 3 max
        
        signal_processor.db.get_trades_df = Mock(return_value=mock_df)
        signal_processor.db.get_current_capital = Mock(return_value=8000.0)
        
        result = signal_processor._check_risk_management()
        
        assert result['allowed'] is False
        assert 'Maximum open trades' in result['reason']
    
    @patch('signal_processor.Config')
    def test_check_risk_management_low_capital(self, mock_config, signal_processor):
        """Test risk management check when capital is too low"""
        mock_config.MAX_OPEN_TRADES = 5
        mock_config.INITIAL_CAPITAL = 10000
        
        import pandas as pd
        mock_df = pd.DataFrame()  # No open trades
        
        signal_processor.db.get_trades_df = Mock(return_value=mock_df)
        signal_processor.db.get_current_capital = Mock(return_value=4000.0)  # Below 50% minimum
        
        result = signal_processor._check_risk_management()
        
        assert result['allowed'] is False
        assert 'Capital too low' in result['reason']
    
    def test_process_signal_success(self, signal_processor):
        """Test successful signal processing"""
        message = """BTCUSDT Buy
Entry: 45,000
TP: 47,250
SL: 42,750"""
        
        # Mock all dependencies
        signal_processor.validate_signal = Mock(return_value=(True, []))
        signal_processor._check_risk_management = Mock(return_value={'allowed': True, 'reason': 'OK'})
        signal_processor.db.add_trade = Mock(return_value=True)
        
        result = signal_processor.process_signal(message)
        
        assert result['success'] is True
        assert 'BTCUSDT Buy' in result['message']
        assert result['trade_id'] is None  # Not returned by add_trade mock
        assert len(result['errors']) == 0
    
    def test_process_signal_parse_failure(self, signal_processor):
        """Test signal processing with parse failure"""
        message = "Invalid signal message"
        
        result = signal_processor.process_signal(message)
        
        assert result['success'] is False
        assert result['message'] == 'Failed to parse signal'
        assert 'Invalid signal format' in result['errors']
    
    def test_process_signal_validation_failure(self, signal_processor):
        """Test signal processing with validation failure"""
        message = """BTCUSDT Buy
Entry: 45,000
TP: 46,000
SL: 42,750"""
        
        # Mock validation failure
        signal_processor.validate_signal = Mock(return_value=(False, ['Low RR ratio']))
        
        result = signal_processor.process_signal(message)
        
        assert result['success'] is False
        assert result['message'] == 'Signal validation failed'
        assert 'Low RR ratio' in result['errors']
    
    def test_process_signal_risk_management_failure(self, signal_processor):
        """Test signal processing with risk management failure"""
        message = """BTCUSDT Buy
Entry: 45,000
TP: 47,250
SL: 42,750"""
        
        # Mock validation success but risk management failure
        signal_processor.validate_signal = Mock(return_value=(True, []))
        signal_processor._check_risk_management = Mock(return_value={
            'allowed': False, 
            'reason': 'Max trades reached'
        })
        
        result = signal_processor.process_signal(message)
        
        assert result['success'] is False
        assert result['message'] == 'Risk management check failed'
        assert 'Max trades reached' in result['errors']
    
    def test_simulate_trade_outcome_win(self, signal_processor):
        """Test trade outcome simulation - winning trade"""
        trade_data = {
            'symbol': 'BTCUSDT',
            'side': 'Buy',
            'entry': 45000.0,
            'tp': 47250.0,
            'sl': 42750.0
        }
        
        # Mock random to always return win
        with patch('signal_processor.random.random', return_value=0.1):  # < win_probability
            result = signal_processor.simulate_trade_outcome(trade_data)
        
        assert result['outcome'] == 'tp'
        assert result['exit_price'] == 47250.0
        assert result['pnl'] > 0
    
    def test_simulate_trade_outcome_loss(self, signal_processor):
        """Test trade outcome simulation - losing trade"""
        trade_data = {
            'symbol': 'BTCUSDT',
            'side': 'Buy', 
            'entry': 45000.0,
            'tp': 47250.0,
            'sl': 42750.0
        }
        
        # Mock random to always return loss
        with patch('signal_processor.random.random', return_value=0.9):  # > win_probability
            result = signal_processor.simulate_trade_outcome(trade_data)
        
        assert result['outcome'] == 'sl'
        assert result['exit_price'] == 42750.0
        assert result['pnl'] < 0