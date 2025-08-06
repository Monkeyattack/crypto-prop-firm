#!/usr/bin/env python3
"""
Dynamic Risk Manager - Real-time symbol risk assessment and position sizing
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import json
import logging
from typing import Dict, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DynamicRiskManager:
    def __init__(self, db_path: str = 'trading.db'):
        self.db_path = db_path
        self.symbol_metrics = {}
        self.load_config()
        self.initialize_metrics()
    
    def load_config(self):
        """Load risk management configuration"""
        try:
            with open('enhanced_strategy_config.json', 'r') as f:
                config = json.load(f)
                self.risk_config = config.get('symbol_management', {})
        except:
            # Default configuration
            self.risk_config = {
                'greylist_threshold': {
                    'consecutive_losses': 4,
                    'total_loss_pct': -15
                },
                'greylist_recovery': {
                    'consecutive_wins': 3
                },
                'risk_scoring_weights': {
                    'win_rate': 0.3,
                    'avg_loss': 0.4,
                    'volatility': 0.3
                }
            }
    
    def initialize_metrics(self):
        """Initialize metrics from recent trading history"""
        conn = sqlite3.connect(self.db_path)
        
        # Get recent trades (last 30 days)
        query = '''
            SELECT symbol, side, profit_loss, created_at,
                   (exit_price - entry_price) / entry_price as price_change
            FROM trades 
            WHERE created_at >= datetime('now', '-30 days')
            ORDER BY created_at DESC
        '''
        
        try:
            recent_trades = pd.read_sql_query(query, conn)
            
            # Initialize metrics for each symbol
            for symbol in recent_trades['symbol'].unique():
                symbol_trades = recent_trades[recent_trades['symbol'] == symbol]
                
                self.symbol_metrics[symbol] = {
                    'performance': deque(symbol_trades['profit_loss'].tolist()[:10], maxlen=10),
                    'volatility': deque(symbol_trades['price_change'].abs().tolist()[:20], maxlen=20),
                    'last_trades': deque(symbol_trades['profit_loss'].tolist()[:5], maxlen=5),
                    'greylist': False,
                    'greylist_reason': None,
                    'last_update': datetime.now()
                }
        except Exception as e:
            logger.warning(f"Could not load historical metrics: {e}")
        
        conn.close()
    
    def update_symbol_metrics(self, symbol: str, profit_loss: float, price_change: float):
        """Update metrics after a trade completes"""
        if symbol not in self.symbol_metrics:
            self.symbol_metrics[symbol] = {
                'performance': deque(maxlen=10),
                'volatility': deque(maxlen=20),
                'last_trades': deque(maxlen=5),
                'greylist': False,
                'greylist_reason': None,
                'last_update': datetime.now()
            }
        
        metrics = self.symbol_metrics[symbol]
        metrics['performance'].append(profit_loss)
        metrics['volatility'].append(abs(price_change))
        metrics['last_trades'].append(profit_loss)
        metrics['last_update'] = datetime.now()
        
        # Check greylist conditions
        self._check_greylist_conditions(symbol)
    
    def _check_greylist_conditions(self, symbol: str):
        """Check if symbol should be greylisted or removed from greylist"""
        metrics = self.symbol_metrics[symbol]
        last_trades = list(metrics['last_trades'])
        
        if len(last_trades) >= 3:
            # Check for consecutive losses
            consecutive_losses = 0
            for trade in last_trades:
                if trade < 0:
                    consecutive_losses += 1
                else:
                    break
            
            # Check total loss in recent trades
            total_loss = sum(t for t in last_trades if t < 0)
            
            threshold = self.risk_config['greylist_threshold']
            
            # Greylist conditions
            if consecutive_losses >= threshold['consecutive_losses']:
                metrics['greylist'] = True
                metrics['greylist_reason'] = f"{consecutive_losses} consecutive losses"
                logger.warning(f"Greylisting {symbol}: {metrics['greylist_reason']}")
            
            elif total_loss < threshold['total_loss_pct']:
                metrics['greylist'] = True
                metrics['greylist_reason'] = f"Total loss {total_loss:.1f}% in last {len(last_trades)} trades"
                logger.warning(f"Greylisting {symbol}: {metrics['greylist_reason']}")
            
            # Recovery conditions
            elif metrics['greylist']:
                recovery = self.risk_config['greylist_recovery']
                consecutive_wins = 0
                
                for trade in last_trades:
                    if trade > 0:
                        consecutive_wins += 1
                    else:
                        break
                
                if consecutive_wins >= recovery['consecutive_wins']:
                    metrics['greylist'] = False
                    metrics['greylist_reason'] = None
                    logger.info(f"Removing {symbol} from greylist - {consecutive_wins} consecutive wins")
    
    def get_symbol_risk_score(self, symbol: str) -> float:
        """Calculate risk score for a symbol (0-1, higher is riskier)"""
        if symbol not in self.symbol_metrics:
            return 0.5  # Neutral for unknown symbols
        
        metrics = self.symbol_metrics[symbol]
        
        # Greylisted symbols get high risk score
        if metrics['greylist']:
            return 0.9
        
        performance = list(metrics['performance'])
        if not performance:
            return 0.5
        
        weights = self.risk_config['risk_scoring_weights']
        
        # Calculate win rate
        win_rate = sum(1 for p in performance if p > 0) / len(performance)
        
        # Calculate average loss
        losses = [p for p in performance if p < 0]
        avg_loss = abs(np.mean(losses)) if losses else 0
        
        # Calculate volatility score
        volatility = list(metrics['volatility'])
        avg_volatility = np.mean(volatility) if volatility else 0.05
        
        # Combine factors
        risk_score = (
            weights['win_rate'] * (1 - win_rate) +
            weights['avg_loss'] * min(avg_loss / 10, 1) +
            weights['volatility'] * min(avg_volatility / 0.15, 1)
        )
        
        return min(max(risk_score, 0), 1)
    
    def get_position_size(self, symbol: str, base_size: float = 100) -> float:
        """Calculate risk-adjusted position size"""
        risk_score = self.get_symbol_risk_score(symbol)
        
        if risk_score < 0.3:
            return base_size * 1.0
        elif risk_score < 0.6:
            return base_size * 0.7
        elif risk_score < 0.8:
            return base_size * 0.4
        else:
            return 0  # Don't trade very high risk symbols
    
    def should_trade_symbol(self, symbol: str) -> Tuple[bool, Optional[str]]:
        """Determine if a symbol should be traded"""
        if symbol not in self.symbol_metrics:
            return True, None  # Allow new symbols
        
        metrics = self.symbol_metrics[symbol]
        
        if metrics['greylist']:
            return False, metrics['greylist_reason']
        
        risk_score = self.get_symbol_risk_score(symbol)
        if risk_score >= 0.8:
            return False, f"Risk score too high: {risk_score:.2f}"
        
        return True, None
    
    def get_risk_report(self) -> Dict:
        """Generate comprehensive risk report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_symbols': len(self.symbol_metrics),
            'greylisted_symbols': [],
            'high_risk_symbols': [],
            'low_risk_symbols': [],
            'symbol_details': {}
        }
        
        for symbol, metrics in self.symbol_metrics.items():
            risk_score = self.get_symbol_risk_score(symbol)
            performance = list(metrics['performance'])
            
            symbol_info = {
                'risk_score': round(risk_score, 3),
                'greylist': metrics['greylist'],
                'greylist_reason': metrics['greylist_reason'],
                'recent_trades': len(performance),
                'win_rate': round(sum(1 for p in performance if p > 0) / len(performance) * 100, 1) if performance else 0,
                'avg_profit': round(np.mean([p for p in performance if p > 0]), 2) if any(p > 0 for p in performance) else 0,
                'avg_loss': round(np.mean([p for p in performance if p < 0]), 2) if any(p < 0 for p in performance) else 0,
                'position_size_multiplier': self.get_position_size(symbol, 1.0)
            }
            
            report['symbol_details'][symbol] = symbol_info
            
            if metrics['greylist']:
                report['greylisted_symbols'].append(symbol)
            elif risk_score >= 0.7:
                report['high_risk_symbols'].append(symbol)
            elif risk_score <= 0.3:
                report['low_risk_symbols'].append(symbol)
        
        return report
    
    def save_risk_state(self):
        """Save current risk state to file"""
        state = {
            'timestamp': datetime.now().isoformat(),
            'symbol_metrics': {}
        }
        
        for symbol, metrics in self.symbol_metrics.items():
            state['symbol_metrics'][symbol] = {
                'performance': list(metrics['performance']),
                'volatility': list(metrics['volatility']),
                'last_trades': list(metrics['last_trades']),
                'greylist': metrics['greylist'],
                'greylist_reason': metrics['greylist_reason'],
                'last_update': metrics['last_update'].isoformat()
            }
        
        with open('risk_manager_state.json', 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_risk_state(self):
        """Load saved risk state"""
        try:
            with open('risk_manager_state.json', 'r') as f:
                state = json.load(f)
            
            for symbol, data in state['symbol_metrics'].items():
                self.symbol_metrics[symbol] = {
                    'performance': deque(data['performance'], maxlen=10),
                    'volatility': deque(data['volatility'], maxlen=20),
                    'last_trades': deque(data['last_trades'], maxlen=5),
                    'greylist': data['greylist'],
                    'greylist_reason': data['greylist_reason'],
                    'last_update': datetime.fromisoformat(data['last_update'])
                }
            
            logger.info(f"Loaded risk state for {len(self.symbol_metrics)} symbols")
        except Exception as e:
            logger.warning(f"Could not load risk state: {e}")

# Example usage and integration
if __name__ == "__main__":
    risk_manager = DynamicRiskManager()
    
    # Example: Check if we should trade a symbol
    symbol = "BTCUSDT"
    can_trade, reason = risk_manager.should_trade_symbol(symbol)
    
    if can_trade:
        position_size = risk_manager.get_position_size(symbol)
        risk_score = risk_manager.get_symbol_risk_score(symbol)
        print(f"Can trade {symbol}: Position size ${position_size:.0f}, Risk score {risk_score:.3f}")
    else:
        print(f"Cannot trade {symbol}: {reason}")
    
    # Generate risk report
    report = risk_manager.get_risk_report()
    print(f"\nRisk Report:")
    print(f"Total symbols tracked: {report['total_symbols']}")
    print(f"Greylisted: {report['greylisted_symbols']}")
    print(f"High risk: {report['high_risk_symbols']}")
    print(f"Low risk: {report['low_risk_symbols']}")
    
    # Save state
    risk_manager.save_risk_state()