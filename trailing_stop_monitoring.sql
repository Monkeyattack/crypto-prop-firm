
# Add this to your monitoring dashboard or alerts

# Key Metrics to Monitor with New Trailing Stop Config:

1. Profit Capture Rate:
   - Track how often trades hit 4.0% activation vs old 4.5%
   - Monitor 1.0% trail distance effectiveness
   
2. Exit Distribution:
   - Count trailing stop exits vs time limit exits
   - Measure average profit at exit
   
3. Performance Validation:
   - Daily P&L vs backtest predictions
   - Win rate consistency (should stay ~62.5%)
   - Average holding time (target: ~150 hours)

# SQL Query for Daily Monitoring:
SELECT 
    DATE(timestamp) as trade_date,
    COUNT(*) as total_trades,
    AVG(pnl) as avg_pnl,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate,
    AVG(
        CASE WHEN result IN ('tp', 'trailing_stop') 
        THEN (julianday('now') - julianday(timestamp)) * 24 
        END
    ) as avg_hold_hours
FROM trades 
WHERE timestamp >= date('now', '-7 days')
GROUP BY DATE(timestamp)
ORDER BY trade_date DESC;

# Alert Thresholds:
- If win rate drops below 55% for 3+ days: investigate
- If avg_pnl drops below $0.80/trade for 5+ days: consider reverting
- If hold time increases above 180 hours: check market conditions
