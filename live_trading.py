"""
Live Trading Module for Crypto Trading System
Transition from paper trading to real money trading
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from config import Config
from database import DatabaseManager, Trade
from signal_processor import SignalProcessor

logger = logging.getLogger(__name__)

class TradingMode(Enum):
    PAPER = "paper"
    LIVE = "live"
    HYBRID = "hybrid"  # Paper for new strategies, live for proven ones

@dataclass
class LiveTradeConfig:
    """Configuration for live trading"""
    mode: TradingMode = TradingMode.PAPER
    max_position_size_usd: float = 100.0  # Maximum position size in USD
    daily_loss_limit_usd: float = 50.0    # Stop trading if daily loss exceeds this
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    exchange: str = "binance"  # or "coinbase", "kraken", etc.
    testnet: bool = True  # Start with testnet/sandbox
    
    # Risk management for live trading
    max_daily_trades: int = 10
    min_account_balance: float = 1000.0
    emergency_stop: bool = False

class LiveTradingManager:
    """Manages transition from paper to live trading"""
    
    def __init__(self, config: LiveTradeConfig):
        self.config = config
        self.db = DatabaseManager()
        self.signal_processor = SignalProcessor()
        
        # Track daily statistics
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_reset = datetime.now().date()
        
        # Initialize exchange connection (placeholder)
        self.exchange_client = None
        if config.mode != TradingMode.PAPER:
            self.exchange_client = self._init_exchange()
    
    def _init_exchange(self):
        """Initialize exchange API client"""
        logger.info(f"Initializing {self.config.exchange} exchange client")
        
        # This is where you'd initialize your exchange client
        # Examples for different exchanges:
        
        if self.config.exchange.lower() == "binance":
            # from binance.client import Client
            # return Client(self.config.api_key, self.config.api_secret, testnet=self.config.testnet)
            logger.warning("Binance client not implemented - add binance-python package")
            
        elif self.config.exchange.lower() == "coinbase":
            # from coinbase_pro import AuthenticatedClient
            # return AuthenticatedClient(self.config.api_key, self.config.api_secret, passphrase)
            logger.warning("Coinbase client not implemented - add cbpro package")
            
        else:
            logger.error(f"Unsupported exchange: {self.config.exchange}")
        
        return None
    
    def should_execute_live_trade(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Determine if a signal should be executed as live trade"""
        
        # Always allow paper trading
        if self.config.mode == TradingMode.PAPER:
            return {"execute": True, "mode": "paper", "reason": "Paper trading mode"}
        
        # Reset daily counters if new day
        self._reset_daily_counters()
        
        # Check emergency stop
        if self.config.emergency_stop:
            return {"execute": False, "mode": "none", "reason": "Emergency stop activated"}
        
        # Check daily loss limit
        if self.daily_pnl <= -self.config.daily_loss_limit_usd:
            return {"execute": False, "mode": "none", "reason": f"Daily loss limit reached: ${abs(self.daily_pnl):.2f}"}
        
        # Check daily trade limit
        if self.daily_trades >= self.config.max_daily_trades:
            return {"execute": False, "mode": "none", "reason": f"Daily trade limit reached: {self.daily_trades}"}
        
        # Check account balance (if live trading)
        if self.config.mode == TradingMode.LIVE:
            balance = self._get_account_balance()
            if balance < self.config.min_account_balance:
                return {"execute": False, "mode": "none", "reason": f"Account balance too low: ${balance:.2f}"}
        
        # For hybrid mode, check if strategy is proven
        if self.config.mode == TradingMode.HYBRID:
            strategy_performance = self._analyze_strategy_performance(signal_data)
            if strategy_performance["win_rate"] < 60 or strategy_performance["total_trades"] < 20:
                return {"execute": True, "mode": "paper", "reason": "Strategy not proven, using paper trading"}
            else:
                return {"execute": True, "mode": "live", "reason": "Proven strategy, executing live"}
        
        # Default to live trading if all checks pass
        return {"execute": True, "mode": "live", "reason": "All safety checks passed"}
    
    def execute_trade(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trade based on current mode"""
        
        decision = self.should_execute_live_trade(signal_data)
        
        if not decision["execute"]:
            logger.warning(f"Trade blocked: {decision['reason']}")
            return {"success": False, "reason": decision["reason"]}
        
        if decision["mode"] == "paper":
            return self._execute_paper_trade(signal_data)
        else:
            return self._execute_live_trade(signal_data)
    
    def _execute_paper_trade(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute paper trade using existing system"""
        logger.info(f"Executing PAPER trade: {signal_data['symbol']} {signal_data['side']}")
        
        # Use existing signal processor
        result = self.signal_processor.process_signal(self._format_signal_message(signal_data))
        
        if result["success"]:
            logger.info(f"Paper trade executed: {result['message']}")
        
        return result
    
    def _execute_live_trade(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute live trade on exchange"""
        if not self.exchange_client:
            logger.error("Exchange client not initialized")
            return {"success": False, "reason": "Exchange client not available"}
        
        logger.info(f"Executing LIVE trade: {signal_data['symbol']} {signal_data['side']}")
        
        try:
            # Calculate position size
            position_size = self._calculate_position_size(signal_data)
            
            # Place order on exchange
            order_result = self._place_exchange_order(signal_data, position_size)
            
            if order_result["success"]:
                # Record in database with live trade flag
                self._record_live_trade(signal_data, order_result)
                
                # Update daily counters
                self.daily_trades += 1
                
                logger.info(f"LIVE trade executed: {order_result}")
                return order_result
            else:
                logger.error(f"Live trade failed: {order_result}")
                return order_result
        
        except Exception as e:
            logger.error(f"Live trade execution error: {e}")
            return {"success": False, "reason": f"Execution error: {e}"}
    
    def _calculate_position_size(self, signal_data: Dict[str, Any]) -> float:
        """Calculate position size based on risk management"""
        
        entry_price = signal_data["entry"]
        sl_price = signal_data["sl"]
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - sl_price)
        
        # Risk amount (max position size or percentage of account)
        max_risk_usd = min(
            self.config.max_position_size_usd * (Config.DEFAULT_RISK_PERCENT / 100),
            self.config.max_position_size_usd * 0.02  # Never risk more than 2%
        )
        
        # Calculate quantity
        if risk_per_share > 0:
            quantity = max_risk_usd / risk_per_share
        else:
            quantity = self.config.max_position_size_usd / entry_price
        
        # Ensure we don't exceed max position size
        max_quantity = self.config.max_position_size_usd / entry_price
        quantity = min(quantity, max_quantity)
        
        logger.info(f"Position size calculated: {quantity:.6f} {signal_data['symbol']}")
        return quantity
    
    def _place_exchange_order(self, signal_data: Dict[str, Any], quantity: float) -> Dict[str, Any]:
        """Place order on exchange (placeholder implementation)"""
        
        # This is where you'd implement actual exchange API calls
        # Example for Binance:
        
        try:
            symbol = signal_data["symbol"]
            side = "BUY" if signal_data["side"].lower() == "buy" else "SELL"
            
            # Market order example (you might want limit orders)
            # order = self.exchange_client.order_market(
            #     symbol=symbol,
            #     side=side,
            #     quantity=quantity
            # )
            
            # For now, simulate successful order
            simulated_order = {
                "success": True,
                "orderId": f"LIVE_{int(time.time())}",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": signal_data["entry"],
                "status": "FILLED",
                "timestamp": datetime.now().isoformat()
            }
            
            logger.warning("SIMULATED live order - implement actual exchange API")
            return simulated_order
            
        except Exception as e:
            logger.error(f"Exchange order failed: {e}")
            return {"success": False, "reason": str(e)}
    
    def _record_live_trade(self, signal_data: Dict[str, Any], order_result: Dict[str, Any]):
        """Record live trade in database"""
        
        # Create trade record with live flag
        trade = Trade(
            symbol=signal_data["symbol"],
            side=signal_data["side"],
            entry=order_result["price"],
            tp=signal_data["tp"],
            sl=signal_data["sl"],
            timestamp=order_result["timestamp"]
        )
        
        # Add to database (you might want to extend Trade class for live trades)
        success = self.db.add_trade(trade)
        
        if success:
            logger.info(f"Live trade recorded in database")
        else:
            logger.error(f"Failed to record live trade in database")
    
    def _get_account_balance(self) -> float:
        """Get current account balance from exchange"""
        if not self.exchange_client:
            return 0.0
        
        try:
            # Example for getting balance
            # account = self.exchange_client.get_account()
            # return float(account['totalWalletBalance'])
            
            # Simulated balance
            return 1500.0
            
        except Exception as e:
            logger.error(f"Failed to get account balance: {e}")
            return 0.0
    
    def _analyze_strategy_performance(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance of trading strategy for hybrid mode"""
        
        # Get recent trades for this symbol
        trades_df = self.db.get_trades_df()
        
        if trades_df.empty:
            return {"win_rate": 0, "total_trades": 0, "avg_pnl": 0}
        
        # Filter by symbol (you might want more sophisticated strategy matching)
        symbol_trades = trades_df[trades_df["symbol"] == signal_data["symbol"]]
        closed_trades = symbol_trades[symbol_trades["result"] != "open"]
        
        if closed_trades.empty:
            return {"win_rate": 0, "total_trades": 0, "avg_pnl": 0}
        
        winning_trades = len(closed_trades[closed_trades["pnl"] > 0])
        total_trades = len(closed_trades)
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        avg_pnl = closed_trades["pnl"].mean()
        
        return {
            "win_rate": win_rate,
            "total_trades": total_trades,
            "avg_pnl": avg_pnl,
            "winning_trades": winning_trades
        }
    
    def _reset_daily_counters(self):
        """Reset daily counters if new day"""
        today = datetime.now().date()
        if today != self.last_reset:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset = today
            logger.info("Daily counters reset")
    
    def _format_signal_message(self, signal_data: Dict[str, Any]) -> str:
        """Format signal data as message for paper trading"""
        return f"""
        {signal_data['side']} {signal_data['symbol']}
        Entry: {signal_data['entry']}
        TP: {signal_data['tp']}
        SL: {signal_data['sl']}
        """
    
    def get_trading_status(self) -> Dict[str, Any]:
        """Get current trading status and statistics"""
        self._reset_daily_counters()
        
        return {
            "mode": self.config.mode.value,
            "exchange": self.config.exchange,
            "testnet": self.config.testnet,
            "daily_pnl": self.daily_pnl,
            "daily_trades": self.daily_trades,
            "daily_limit": self.config.max_daily_trades,
            "emergency_stop": self.config.emergency_stop,
            "account_balance": self._get_account_balance() if self.config.mode != TradingMode.PAPER else None
        }
    
    def enable_emergency_stop(self):
        """Enable emergency stop to halt all trading"""
        self.config.emergency_stop = True
        logger.critical("EMERGENCY STOP ACTIVATED - All trading halted")
    
    def disable_emergency_stop(self):
        """Disable emergency stop"""
        self.config.emergency_stop = False
        logger.info("Emergency stop disabled - Trading resumed")

# Usage Examples and Configuration
if __name__ == "__main__":
    # Example 1: Start with paper trading
    paper_config = LiveTradeConfig(
        mode=TradingMode.PAPER
    )
    
    # Example 2: Live trading configuration
    live_config = LiveTradeConfig(
        mode=TradingMode.LIVE,
        max_position_size_usd=100.0,
        daily_loss_limit_usd=50.0,
        exchange="binance",
        testnet=True,  # Start with testnet!
        api_key="your_api_key",
        api_secret="your_api_secret"
    )
    
    # Example 3: Hybrid mode (paper for unproven, live for proven strategies)
    hybrid_config = LiveTradeConfig(
        mode=TradingMode.HYBRID,
        max_position_size_usd=50.0,
        daily_loss_limit_usd=25.0,
        exchange="binance",
        testnet=True
    )
    
    # Initialize trading manager
    trader = LiveTradingManager(paper_config)
    
    # Example signal
    test_signal = {
        "symbol": "BTCUSDT",
        "side": "Buy",
        "entry": 45000,
        "tp": 47000,
        "sl": 43000
    }
    
    # Execute trade
    result = trader.execute_trade(test_signal)
    print(f"Trade result: {result}")
    
    # Get status
    status = trader.get_trading_status()
    print(f"Trading status: {status}")