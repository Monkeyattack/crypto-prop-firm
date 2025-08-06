#!/usr/bin/env python3
"""
Update trading settings with equity-based position sizing parameters
"""

import sqlite3
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_equity_settings():
    """Update settings with equity-based risk management parameters"""
    try:
        conn = sqlite3.connect('trade_log.db')
        cursor = conn.cursor()
        
        # Get current settings
        cursor.execute('SELECT settings_json FROM trading_settings WHERE id = 1')
        result = cursor.fetchone()
        
        if result and result[0]:
            settings = json.loads(result[0])
        else:
            settings = {}
        
        # Add equity-based risk management settings
        equity_settings = {
            "enabled": True,
            "max_daily_trades": 10,
            "use_market_analysis": True,
            
            # Equity-based position sizing
            "position_sizing_method": "equity_based",  # "fixed" or "equity_based"
            "risk_per_trade_pct": 2.0,               # 2% risk per trade
            "max_portfolio_risk_pct": 10.0,          # 10% max total portfolio risk
            "max_position_size_pct": 20.0,           # 20% max position size of account
            "min_position_size_usd": 100.0,          # $100 minimum position
            "max_position_size_usd": 5000.0,         # $5000 maximum position
            
            # Take profit strategy
            "trailing_take_profit": {
                "enabled": True,
                "target_profit_pct": 5.0,            # 5% target profit
                "activation_pct": 3.0,               # Activate trailing at 3% profit
                "trail_distance_pct": 1.5,           # Trail 1.5% behind high
                "fallback_profit_pct": 3.5           # 3.5% fallback if target not hit
            },
            
            # Risk management
            "stop_loss_pct": 5.0,                    # 5% max loss (overridden by equity sizing)
            "daily_loss_limit_pct": 5.0,             # 5% daily loss limit
            "max_open_positions": 5,                 # Max concurrent positions (dynamic)
            
            # Market conditions
            "market_analysis_enabled": True,
            "skip_poor_market_conditions": True,
            "volatility_adjustment_enabled": True
        }
        
        # Merge with existing settings
        settings.update(equity_settings)
        
        # Update database
        cursor.execute('''
            INSERT OR REPLACE INTO trading_settings (id, settings_json, updated_at)
            VALUES (1, ?, datetime('now'))
        ''', (json.dumps(settings, indent=2),))
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Updated trading settings with equity-based position sizing!")
        logger.info("📊 New Settings:")
        logger.info(f"   • Risk per trade: {equity_settings['risk_per_trade_pct']}%")
        logger.info(f"   • Max portfolio risk: {equity_settings['max_portfolio_risk_pct']}%")
        logger.info(f"   • Position size range: ${equity_settings['min_position_size_usd']:.0f} - ${equity_settings['max_position_size_usd']:.0f}")
        logger.info(f"   • Max position size: {equity_settings['max_position_size_pct']}% of account")
        logger.info(f"   • Target profit: {equity_settings['trailing_take_profit']['target_profit_pct']}%")
        
    except Exception as e:
        logger.error(f"❌ Error updating settings: {e}")

if __name__ == "__main__":
    update_equity_settings()