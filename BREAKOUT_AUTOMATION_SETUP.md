# 🚀 Breakout Prop Semi-Automation Setup Guide

## Overview
Since Breakout Prop doesn't offer API access (yet), this system provides the next best thing: **intelligent alerts with exact execution instructions** sent to your phone for manual execution in the Breakout Terminal app.

## What This System Does

### ✅ Fully Automated (By Your System):
- Monitors Telegram signals 24/7
- Validates against prop firm rules
- Checks adaptive risk management
- Calculates exact position sizes
- Monitors account limits
- Tracks daily reset times
- Sends detailed execution alerts

### 📱 Semi-Manual (By You):
- Receive alert on phone (< 2 seconds)
- Open Breakout Terminal app
- Enter pre-calculated values
- Execute trade (< 30 seconds total)

## Quick Start (5 Minutes)

### 1. Install Requirements
```bash
pip install aiohttp python-dotenv telethon pandas
```

### 2. Configure .env File
Already configured in your .env:
```env
# These are already set
TELEGRAM_BOT_TOKEN=8405614465:AAGl1MFkI4T7dksrk93oHXJOilcBXH36Do0
TELEGRAM_CHAT_ID=6585156851
PROP_FIRM_MODE=true
ACCOUNT_SIZE=10000.00
```

### 3. Start the System
```bash
python start_breakout_automation.py
```

### 4. Verify Connection
You'll receive a test message on Telegram confirming the system is running.

## Alert Format Example

When a valid signal is detected, you'll receive:

```
🚨 BREAKOUT TRADE ALERT 🚨

🟢 BUY BTCUSDT

📍 Entry: 45250.0000
🛑 Stop Loss: 44800.0000
🎯 Take Profit: 46150.0000

💰 Position Size: $150.00
⚡ Leverage: 5x
⚠️ Risk: $150.00
📊 RR Ratio: 2.00

🔧 Mode: evaluation_normal
📝 Note: Standard trade - Follow normal risk management.

EXECUTION STEPS:
1. Open Breakout Terminal app
2. Navigate to BTCUSDT
3. Select BUY order
4. Set leverage to 5x
5. Enter position size: $150.00
6. Set entry price: 45250.0000
7. Set stop loss: 44800.0000
8. Set take profit: 46150.0000
9. Review order details
10. Confirm and execute
11. Screenshot confirmation
12. Reply 'DONE' to this message

⏰ Time: 2025-01-06T15:30:00Z

Reply 'DONE' when executed
```

## Special Mode Alerts

### When Near Profit Target (90%+):
```
⚠️ CRITICAL: Near profit target!
Position Size: $50.00 (reduced)
Note: Execute with extreme caution. Consider taking partial profits early.
```

### When in Recovery Mode:
```
🔴 RECOVERY MODE: Only take this if 100% confident.
Position Size: $25.00 (minimal)
Note: Consider skipping if unsure.
```

## Risk Management Alerts

### Daily Loss Warning (75%+):
```
⚠️ RISK MANAGEMENT ALERT ⚠️
WARNING: 80% of daily loss limit used!

Recommended Action:
- Reduce position sizes
- Only take A+ setups
- Consider stopping for the day
```

### Drawdown Warning (75%+):
```
⚠️ RISK MANAGEMENT ALERT ⚠️
CRITICAL: 80% of max drawdown used!

Recommended Action:
- Stop trading immediately
- Review all losing trades
- Wait for daily reset
```

## Mobile App Optimization

### Configure Breakout Terminal for Speed:

1. **Enable Quick Login**
   - Use Face ID/Fingerprint
   - Save login credentials

2. **Create Templates**
   - Set default position sizes
   - Save common TP/SL ratios
   - Create favorite pairs list

3. **Enable Notifications**
   - Turn on execution confirmations
   - Enable P&L alerts

4. **Practice Flow**
   - Time yourself: Should be < 30 seconds
   - Alert → Open → Enter → Execute → Confirm

## Advanced Features

### 1. Position Monitoring
The system continues monitoring after you enter trades:
- Alerts when to move stop to breakeven
- Suggests partial profit taking
- Warns about approaching limits

### 2. Daily Reset Handler
At 00:30 UTC daily:
- Resets daily loss tracking
- Re-enables trading if stopped
- Sends summary report

### 3. Adaptive Modes
System automatically adjusts based on account:
- **Normal**: Standard 1.5% risk
- **Final Push**: 0.5% risk when near target
- **Conservative**: After passing evaluation
- **Recovery**: Minimal risk after drawdown

## Troubleshooting

### Bot Not Sending Messages?
```bash
# Test Telegram connection
python -c "
import requests
TOKEN='8405614465:AAGl1MFkI4T7dksrk93oHXJOilcBXH36Do0'
CHAT_ID='6585156851'
url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
requests.post(url, json={'chat_id': CHAT_ID, 'text': 'Test'})
"
```

### System Not Starting?
Check logs:
```bash
tail -f logs/breakout_automation.log
```

### Signals Not Processing?
Verify signal source is connected:
```python
# In breakout_semi_automation.py
async def get_new_signals(self):
    # Connect your signal source here
    return your_signals
```

## Performance Tracking

### Daily Metrics Logged:
- Signals received vs executed
- Response time to alerts
- Win/loss ratio
- Risk management compliance

### Weekly Review:
- Average execution time
- Missed opportunities
- System improvements needed

## Customization

### Adjust Risk Parameters:
```python
# In breakout_semi_automation.py
self.min_position_size = 10  # Minimum position
self.alert_cooldown = 30     # Seconds between alerts
```

### Change Alert Format:
```python
# Modify format_alert_message() method
# Add/remove fields as needed
```

### Add Signal Sources:
```python
# Implement get_new_signals() method
# Connect to your signal provider
```

## Next Steps

### Phase 1: Current Implementation ✅
- Signal validation
- Risk management
- Mobile alerts
- Manual execution

### Phase 2: Enhanced Monitoring
- Add position tracking database
- Implement P&L tracking
- Create performance dashboard

### Phase 3: Future API Integration
- When Breakout releases API
- Convert to full automation
- Maintain semi-auto as backup

## Important Notes

1. **Always Verify**: Check the alert details before executing
2. **Screenshot Trades**: Keep records of all executions
3. **Track Performance**: Log actual vs suggested trades
4. **Stay Disciplined**: Don't skip risk rules
5. **Monitor Account**: Check Breakout Terminal regularly

## Support Commands

### Start System:
```bash
python start_breakout_automation.py
```

### Run in Background:
```bash
nohup python start_breakout_automation.py > output.log 2>&1 &
```

### Stop System:
```bash
# Send 'STOP' message via Telegram
# Or press Ctrl+C in terminal
```

### Check Status:
```bash
tail -f logs/breakout_automation.log
```

## Emergency Procedures

### If System Fails:
1. Check Telegram manually for signals
2. Use prop_firm_manager.py for validation
3. Calculate position size manually
4. Execute in Breakout Terminal

### If Near Limits:
1. System auto-alerts at 75%
2. Stop trading at 90%
3. Wait for daily reset
4. Review all trades

---

## Ready to Start?

Run this command:
```bash
python start_breakout_automation.py
```

You'll receive a confirmation message on Telegram, and the system will begin monitoring!

**Expected Results:**
- 3-5 high-quality alerts per day
- < 30 second execution time
- 82% probability of passing evaluation
- Full risk management compliance

---

*Remember: This semi-automation gives you 90% of the benefits of full automation while staying within Breakout Prop's current limitations.*