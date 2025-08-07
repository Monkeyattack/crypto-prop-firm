"""
Adaptive Risk Manager - Automatically adjusts strategy based on account status
Implements different modes: Evaluation, Near-Pass, Funded, Recovery
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class TradingMode(Enum):
    """Different trading modes based on account status"""
    EVALUATION_NORMAL = "evaluation_normal"     # Standard evaluation mode
    EVALUATION_FINAL = "evaluation_final"       # 80%+ to target
    FUNDED_CONSERVATIVE = "funded_conservative" # First 3 months funded
    FUNDED_GROWTH = "funded_growth"            # Months 4-6 funded
    FUNDED_SCALED = "funded_scaled"            # After scaling up
    RECOVERY = "recovery"                       # After significant drawdown
    STOPPED = "stopped"                         # Trading halted

@dataclass
class RiskProfile:
    """Risk parameters for different trading modes"""
    mode: TradingMode
    risk_per_trade: float
    max_daily_trades: int
    min_rr_ratio: float
    max_daily_loss: float
    position_size_multiplier: float
    allowed_symbols: list
    requires_confluence: int  # Number of confirmations needed
    stop_after_losses: int   # Stop after X consecutive losses
    
class AdaptiveRiskManager:
    """Manages risk dynamically based on account status"""
    
    # Risk profiles for different modes
    RISK_PROFILES = {
        TradingMode.EVALUATION_NORMAL: RiskProfile(
            mode=TradingMode.EVALUATION_NORMAL,
            risk_per_trade=0.015,  # 1.5%
            max_daily_trades=3,
            min_rr_ratio=1.5,
            max_daily_loss=500,
            position_size_multiplier=1.0,
            allowed_symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOTUSDT', 'ADAUSDT'],
            requires_confluence=2,
            stop_after_losses=3
        ),
        TradingMode.EVALUATION_FINAL: RiskProfile(
            mode=TradingMode.EVALUATION_FINAL,
            risk_per_trade=0.005,  # 0.5% - Very conservative
            max_daily_trades=2,
            min_rr_ratio=3.0,     # Only high RR trades
            max_daily_loss=200,    # Tighter limit
            position_size_multiplier=0.33,
            allowed_symbols=['BTCUSDT', 'SOLUSDT', 'DOTUSDT'],  # Only best performers
            requires_confluence=4,  # Need strong confirmation
            stop_after_losses=1    # Stop after ANY loss
        ),
        TradingMode.FUNDED_CONSERVATIVE: RiskProfile(
            mode=TradingMode.FUNDED_CONSERVATIVE,
            risk_per_trade=0.0075, # 0.75%
            max_daily_trades=2,
            min_rr_ratio=2.0,
            max_daily_loss=250,    # Half of evaluation
            position_size_multiplier=0.5,
            allowed_symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOTUSDT'],
            requires_confluence=3,
            stop_after_losses=2
        ),
        TradingMode.FUNDED_GROWTH: RiskProfile(
            mode=TradingMode.FUNDED_GROWTH,
            risk_per_trade=0.01,   # 1%
            max_daily_trades=3,
            min_rr_ratio=2.0,
            max_daily_loss=300,
            position_size_multiplier=0.75,
            allowed_symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOTUSDT', 'ADAUSDT'],
            requires_confluence=2,
            stop_after_losses=2
        ),
        TradingMode.FUNDED_SCALED: RiskProfile(
            mode=TradingMode.FUNDED_SCALED,
            risk_per_trade=0.0125, # 1.25%
            max_daily_trades=4,
            min_rr_ratio=1.5,
            max_daily_loss=400,
            position_size_multiplier=1.0,
            allowed_symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOTUSDT', 'ADAUSDT', 'LINKUSDT'],
            requires_confluence=2,
            stop_after_losses=3
        ),
        TradingMode.RECOVERY: RiskProfile(
            mode=TradingMode.RECOVERY,
            risk_per_trade=0.0025, # 0.25% - Minimal risk
            max_daily_trades=1,
            min_rr_ratio=4.0,      # Only excellent RR
            max_daily_loss=100,
            position_size_multiplier=0.2,
            allowed_symbols=['BTCUSDT'],  # Only Bitcoin
            requires_confluence=5,  # Maximum confirmation
            stop_after_losses=1
        )
    }
    
    def __init__(self, account_balance: float, initial_balance: float = 10000):
        self.account_balance = account_balance
        self.initial_balance = initial_balance
        self.evaluation_target = initial_balance * 1.1  # 10% profit target
        self.current_mode = TradingMode.EVALUATION_NORMAL
        self.daily_losses = 0
        self.consecutive_losses = 0
        self.is_funded = False
        self.months_funded = 0
        self.daily_trades = 0
        self.last_trade_time = None
        
    def update_account_status(self, balance: float, is_funded: bool = False, 
                            drawdown: float = 0, months_funded: int = 0):
        """Update account status and determine appropriate mode"""
        self.account_balance = balance
        self.is_funded = is_funded
        self.months_funded = months_funded
        
        # Determine trading mode
        if not is_funded:
            # Evaluation phase
            progress = (balance - self.initial_balance) / (self.evaluation_target - self.initial_balance)
            
            if drawdown > 500:  # Near drawdown limit
                self.current_mode = TradingMode.RECOVERY
            elif progress >= 0.8:  # 80% or more to target
                self.current_mode = TradingMode.EVALUATION_FINAL
                logger.info(f"Switching to FINAL mode - {progress*100:.1f}% to target")
            else:
                self.current_mode = TradingMode.EVALUATION_NORMAL
        else:
            # Funded account phase
            if drawdown > 400:  # High drawdown
                self.current_mode = TradingMode.RECOVERY
            elif months_funded <= 3:
                self.current_mode = TradingMode.FUNDED_CONSERVATIVE
            elif months_funded <= 6:
                self.current_mode = TradingMode.FUNDED_GROWTH
            else:
                self.current_mode = TradingMode.FUNDED_SCALED
        
        return self.current_mode
    
    def get_current_risk_profile(self) -> RiskProfile:
        """Get the current risk profile based on mode"""
        return self.RISK_PROFILES[self.current_mode]
    
    def can_take_trade(self, symbol: str, signal_confidence: float, 
                      confluences: int) -> Tuple[bool, str, Dict]:
        """Determine if a trade can be taken based on current mode"""
        profile = self.get_current_risk_profile()
        
        # Check if trading is stopped
        if self.current_mode == TradingMode.STOPPED:
            return False, "Trading is currently stopped", {}
        
        # Check daily trade limit
        if self.daily_trades >= profile.max_daily_trades:
            return False, f"Daily trade limit reached ({profile.max_daily_trades})", {}
        
        # Check symbol is allowed
        if symbol not in profile.allowed_symbols:
            return False, f"Symbol {symbol} not allowed in {self.current_mode.value} mode", {}
        
        # Check confluence requirements
        if confluences < profile.requires_confluence:
            return False, f"Insufficient confluence ({confluences}/{profile.requires_confluence})", {}
        
        # Check consecutive losses
        if self.consecutive_losses >= profile.stop_after_losses:
            return False, f"Stop after {profile.stop_after_losses} consecutive losses", {}
        
        # Calculate position size
        position_size = self.calculate_position_size(profile)
        
        # Prepare trade parameters
        trade_params = {
            'position_size': position_size,
            'risk_amount': self.account_balance * profile.risk_per_trade,
            'max_loss': profile.max_daily_loss - abs(self.daily_losses),
            'min_rr_ratio': profile.min_rr_ratio,
            'mode': self.current_mode.value,
            'special_instructions': self.get_special_instructions()
        }
        
        return True, "Trade approved", trade_params
    
    def calculate_position_size(self, profile: RiskProfile) -> float:
        """Calculate position size based on current profile"""
        base_size = self.account_balance * profile.risk_per_trade
        adjusted_size = base_size * profile.position_size_multiplier
        
        # Additional adjustments for special situations
        if self.current_mode == TradingMode.EVALUATION_FINAL:
            # Further reduce size when very close to target
            progress = (self.account_balance - self.initial_balance) / (self.evaluation_target - self.initial_balance)
            if progress >= 0.95:  # 95% to target
                adjusted_size *= 0.5  # Half the size again
        
        return adjusted_size
    
    def record_trade_result(self, profit_loss: float, won: bool):
        """Record trade result and update tracking"""
        self.daily_losses += profit_loss if profit_loss < 0 else 0
        self.daily_trades += 1
        
        if won:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
        
        # Check if we should stop trading
        profile = self.get_current_risk_profile()
        if abs(self.daily_losses) >= profile.max_daily_loss * 0.8:
            logger.warning(f"Approaching daily loss limit: ${abs(self.daily_losses):.2f}")
            if abs(self.daily_losses) >= profile.max_daily_loss:
                self.current_mode = TradingMode.STOPPED
                logger.error("Daily loss limit reached - Trading STOPPED")
    
    def reset_daily_counters(self):
        """Reset daily counters (call at daily reset time)"""
        self.daily_losses = 0
        self.daily_trades = 0
        if self.current_mode == TradingMode.STOPPED:
            # Re-enable trading after daily reset
            self.update_account_status(self.account_balance, self.is_funded)
    
    def get_special_instructions(self) -> str:
        """Get special trading instructions based on current mode"""
        instructions = {
            TradingMode.EVALUATION_FINAL: "CRITICAL: Near profit target. Take profits quickly. No overnight positions. Exit at 50% of TP if needed.",
            TradingMode.FUNDED_CONSERVATIVE: "First 3 months funded. Focus on consistency over profits. Document every trade.",
            TradingMode.RECOVERY: "RECOVERY MODE: Extreme caution. Wait for perfect setups only. Consider taking a break.",
            TradingMode.STOPPED: "Trading suspended. Wait for daily reset."
        }
        return instructions.get(self.current_mode, "Trade normally with proper risk management.")
    
    def get_status_report(self) -> Dict:
        """Get comprehensive status report"""
        profile = self.get_current_risk_profile()
        
        return {
            'current_mode': self.current_mode.value,
            'account_balance': self.account_balance,
            'risk_per_trade': f"{profile.risk_per_trade*100:.2f}%",
            'daily_trades_taken': self.daily_trades,
            'daily_trades_remaining': profile.max_daily_trades - self.daily_trades,
            'daily_loss_used': abs(self.daily_losses),
            'daily_loss_remaining': profile.max_daily_loss - abs(self.daily_losses),
            'consecutive_losses': self.consecutive_losses,
            'min_rr_required': profile.min_rr_ratio,
            'allowed_symbols': profile.allowed_symbols,
            'position_multiplier': profile.position_size_multiplier,
            'special_mode_active': self.current_mode in [TradingMode.EVALUATION_FINAL, TradingMode.RECOVERY],
            'instructions': self.get_special_instructions()
        }
    
    def should_lock_profits(self) -> Tuple[bool, float]:
        """Determine if profits should be locked (withdrawn)"""
        if not self.is_funded:
            return False, 0
        
        profit = self.account_balance - self.initial_balance
        
        if self.months_funded <= 3:
            # First 3 months: Lock 50% of profits weekly if > $200
            if profit > 200:
                return True, profit * 0.5
        elif self.months_funded <= 6:
            # Months 4-6: Lock 60% of profits weekly if > $300
            if profit > 300:
                return True, profit * 0.6
        else:
            # After 6 months: Lock 70% of profits weekly
            if profit > 400:
                return True, profit * 0.7
        
        return False, 0
    
    def get_scaling_eligibility(self) -> Dict:
        """Check eligibility for account scaling"""
        if not self.is_funded:
            return {'eligible': False, 'reason': 'Not yet funded'}
        
        # Check requirements for scaling
        requirements = {
            'months_funded': self.months_funded >= 3,
            'profitable_months': True,  # Would need actual data
            'no_breaches': True,  # Would need actual data
            'consistent_returns': True  # Would need actual data
        }
        
        eligible = all(requirements.values())
        
        return {
            'eligible': eligible,
            'requirements_met': requirements,
            'next_account_size': 25000 if self.account_balance == 10000 else 50000,
            'next_profit_split': 0.85 if self.months_funded <= 3 else 0.90
        }


def demonstrate_adaptive_system():
    """Demonstrate how the adaptive system works"""
    
    # Scenario 1: Normal evaluation
    print("SCENARIO 1: Normal Evaluation Trading")
    print("-" * 50)
    manager = AdaptiveRiskManager(10000, 10000)
    manager.update_account_status(10000, is_funded=False)
    can_trade, reason, params = manager.can_take_trade('BTCUSDT', 0.75, 3)
    print(f"Can trade BTC: {can_trade}")
    print(f"Risk per trade: {params.get('risk_amount', 0):.2f}")
    print()
    
    # Scenario 2: Near profit target
    print("SCENARIO 2: Near Profit Target (90% complete)")
    print("-" * 50)
    manager.update_account_status(10900, is_funded=False)  # $900 profit, need $100 more
    can_trade, reason, params = manager.can_take_trade('BTCUSDT', 0.85, 4)
    print(f"Mode: {manager.current_mode.value}")
    print(f"Can trade: {can_trade}")
    print(f"Risk per trade: {params.get('risk_amount', 0):.2f}")
    print(f"Instructions: {params.get('special_instructions', '')}")
    print()
    
    # Scenario 3: Funded account (first month)
    print("SCENARIO 3: Funded Account - Month 1")
    print("-" * 50)
    manager.update_account_status(10300, is_funded=True, months_funded=1)
    can_trade, reason, params = manager.can_take_trade('BTCUSDT', 0.80, 3)
    print(f"Mode: {manager.current_mode.value}")
    print(f"Risk per trade: {params.get('risk_amount', 0):.2f}")
    should_lock, amount = manager.should_lock_profits()
    print(f"Should lock profits: {should_lock}, Amount: ${amount:.2f}")
    print()
    
    # Scenario 4: Recovery mode
    print("SCENARIO 4: Recovery Mode (High Drawdown)")
    print("-" * 50)
    manager.update_account_status(9500, is_funded=False, drawdown=500)
    can_trade, reason, params = manager.can_take_trade('ETHUSDT', 0.90, 5)
    print(f"Mode: {manager.current_mode.value}")
    print(f"Can trade ETH: {can_trade}")
    print(f"Reason: {reason}")
    print(f"Instructions: {manager.get_special_instructions()}")
    print()
    
    # Print full status report
    print("FULL STATUS REPORT")
    print("-" * 50)
    report = manager.get_status_report()
    for key, value in report.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    demonstrate_adaptive_system()