#!/usr/bin/env python3
"""Enable automated trading in the system"""

import sqlite3
import json

conn = sqlite3.connect('trade_log.db')
cursor = conn.cursor()

# Update trading settings to enable automated trading
settings = {
    "enabled": True,
    "max_daily_trades": 10,
    "position_size": 1000,
    "use_market_analysis": True,
    "trailing_take_profit": {
        "enabled": True,
        "target_profit_pct": 5.0,
        "activation_pct": 3.0,
        "trail_distance_pct": 1.5,
        "fallback_profit_pct": 3.5
    }
}

cursor.execute(
    "UPDATE trading_settings SET settings_json = ? WHERE id = 1",
    (json.dumps(settings),)
)

conn.commit()
conn.close()

print("[OK] Automated trading ENABLED!")
print("The system will now:")
print("- Process incoming signals")
print("- Execute trades automatically")
print("- Apply trailing take profit logic")
print("- Update the dashboard in real-time")