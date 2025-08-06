# 📱 Telegram Signal Integration Setup

## Your Configuration

**Phone Number:** +14692238202  
**Monitored Group:** SMRT Signals - Crypto Channel  
**API ID:** 7540855  
**API Hash:** 0ad0e0e612829f4642c373ff0334df1e  

## Quick Setup Steps

### 1. Create your .env file
```bash
# Copy the template
cp .env.template .env
```

### 2. Add your Telegram configuration to .env
```bash
# Add these lines to your .env file:
TELEGRAM_API_ID=7540855
TELEGRAM_API_HASH=0ad0e0e612829f4642c373ff0334df1e
TELEGRAM_PHONE_NUMBER=+14692238202
TELEGRAM_MONITORED_GROUPS="SMRT Signals - Crypto Channel"
TELEGRAM_SESSION_STRING=  # This will be generated automatically
```

### 3. Install Telegram dependencies
```bash
pip install telethon cryptg
```

### 4. Run the setup script
```bash
python setup_telegram.py
```

This will:
- Connect to your Telegram account
- Generate a session string
- Show you all your groups
- Test the connection

### 5. Save the session string
After running the setup, you'll get a session string. Add it to your .env file:
```bash
TELEGRAM_SESSION_STRING=your_generated_session_string_here
```

### 6. Test the integration
```bash
python telegram_user_client.py
```

This will start monitoring "SMRT Signals - Crypto Channel" for trading signals.

## What happens next?

The system will:
1. Monitor your Telegram group for messages
2. Automatically detect trading signals (Buy/Sell, Entry, TP, SL)
3. Parse the signals and add them to your paper trading dashboard
4. Send you notifications when signals are detected

## Signal Format Examples

The system can detect various signal formats:
```
Buy BTCUSDT
Entry: 45000
TP: 47000
SL: 43000
```

```
🚀 LONG SIGNAL 🚀
Pair: ETHUSDT
Entry: 2600
Target: 2750
Stop Loss: 2450
```

```
BUY $ADA @ 0.45 | TP: 0.50 | SL: 0.40
```

## Troubleshooting

### Authentication Error
- Make sure your phone number is correct: +14692238202
- Check that your API credentials are valid
- Run `python setup_telegram.py` again

### Group Not Found
- Make sure the group name is exact: "SMRT Signals - Crypto Channel"
- Try using the group ID instead (shown during setup)

### No Signals Detected
- Check that messages in the group contain trading keywords
- Verify signal format matches expected patterns
- Use test mode: `python telegram_user_client.py --test`

## Security Notes

- Your session string is sensitive - keep it secure
- The system only reads messages, never sends them
- All trading is paper trading by default (no real money at risk)

## Ready to Start

Once setup is complete:
1. Start your Streamlit dashboard: `streamlit run dashboard/app.py`
2. Start Telegram monitoring: `python telegram_user_client.py`
3. Watch for signals in "SMRT Signals - Crypto Channel"
4. Review detected trades in your dashboard

Happy trading! 🚀

---

## Alternative: Bot Setup (if you can add bots to groups)

### Using Existing Bot
Your existing bot token: `7169619484:AAF2Kea4mskf8kWeq4Ugj-Fop7qZ8cGudT8`

### Or Create a New Bot (Optional)
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`
3. Choose a name: `Crypto Paper Trading Bot`
4. Choose a username: `crypto_paper_trading_bot` (must end in 'bot')
5. Save the bot token

## 🔧 Step 2: Configure Bot for Group Access

### Add Bot to Your Private Group
1. **Add the bot to your private trading group**:
   - Go to your private Telegram group
   - Click "Add Member" 
   - Search for your bot username
   - Add the bot as a member

2. **Give the bot admin permissions** (Required to read all messages):
   - Go to group settings → Administrators
   - Add your bot as administrator
   - Enable "Delete Messages" permission (minimum required)

### Get Group Chat ID
You need to find the group's chat ID. Here are two methods:

#### Method 1: Send a message and check
1. Add your bot to the group
2. Send any message in the group mentioning the bot: `@your_bot_name hello`
3. Go to: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Look for the `chat` object and find the `id` (it will be negative for groups)

#### Method 2: Use a web tool
1. Add [@userinfobot](https://t.me/userinfobot) to your group temporarily
2. It will show the group ID
3. Remove the bot after getting the ID

## ⚙️ Step 3: Update Environment Configuration

Add these to your `.env` file:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=7169619484:AAF2Kea4mskf8kWeq4Ugj-Fop7qZ8cGudT8
TELEGRAM_CHAT_ID=6585156851  # Your personal chat ID for notifications
TELEGRAM_ALLOWED_GROUPS=-1001234567890,-1009876543210  # Group IDs (comma-separated)

# Optional: Specific group names/usernames
# TELEGRAM_ALLOWED_GROUPS=@cryptosignals,@tradinggroup,-1001234567890
```

**Important**: Group IDs are usually negative numbers starting with `-100`

## 🚀 Step 4: Install Additional Dependencies

```bash
# In your project directory
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

pip install python-telegram-bot==20.7
```

## 🎯 Step 5: Test the Bot

### Test Signal Processing
```bash
# Test the signal processor first
python signal_processor.py
```

### Run the Telegram Bot
```bash
# Start the bot
python telegram_bot.py
```

### Test in Your Group
1. Send a test trading signal in your group:
```
Buy BTCUSDT
Entry: 45000
TP: 47000
SL: 43000
```

2. Check the logs - you should see:
   - "Received message from [Group Name]"
   - "Processing potential signal"
   - "TRADE EXECUTED" or error message

## 📊 Step 6: Monitor and Control

### Bot Commands (Send to your bot privately)
- `/status` - Check bot status and statistics
- `/stop` - Stop signal processing
- `/emergency` - Enable emergency stop for all trading

### Monitoring
The bot will send you notifications for:
- ✅ Successful trades executed
- ❌ Failed trades with reasons
- ⚠️ Rejected signals
- 🚨 Errors and issues

## 🔒 Security Best Practices

### Bot Permissions
- **Minimal permissions**: Only give "Delete Messages" admin permission
- **Monitor access**: Regularly check who has access to your trading groups
- **Bot security**: Keep your bot token secret and secure

### Group Security
- **Private groups only**: Never add the bot to public groups
- **Trusted members**: Only allow trusted people in your trading groups
- **Regular audits**: Check group members periodically

## 🛠️ Advanced Configuration

### Signal Filtering
Edit `telegram_bot.py` to customize signal detection:
```python
def _looks_like_signal(self, text: str) -> bool:
    # Customize signal detection logic
    signal_keywords = [
        'buy', 'sell', 'long', 'short',
        'entry', 'tp', 'sl', 'target'
    ]
    # Add your custom logic here
```

### Multiple Groups
To monitor multiple groups, add all group IDs:
```bash
TELEGRAM_ALLOWED_GROUPS=-1001111111111,-1002222222222,-1003333333333
```

### Custom Signal Formats
If your group uses different signal formats, update the regex pattern in `signal_processor.py`:
```python
self.signal_pattern = re.compile(
    r'(?P<side>Buy|Sell|Long|Short)\s+(?P<symbol>\w+)\s*\n'
    r'Entry:\s*(?P<entry>[\d,.]+)\s*\n'
    r'TP:\s*(?P<tp>[\d,.]+)\s*\n'
    r'SL:\s*(?P<sl>[\d,.]+)',
    re.IGNORECASE | re.MULTILINE
)
```

## 📈 Production Deployment

### Deploy to VPS
```bash
# On your VPS
cd /root/crypto-paper-trading
source venv/bin/activate
pip install python-telegram-bot==20.7

# Update .env with your Telegram configuration
nano .env

# Test the bot
python telegram_bot.py
```

### Run as Service
Create systemd service:
```bash
sudo tee /etc/systemd/system/telegram-signal-bot.service << EOF
[Unit]
Description=Telegram Signal Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/crypto-paper-trading
Environment=PATH=/root/crypto-paper-trading/venv/bin
ExecStart=/root/crypto-paper-trading/venv/bin/python telegram_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable telegram-signal-bot
sudo systemctl start telegram-signal-bot
```

## 🔍 Troubleshooting

### Common Issues

**Bot can't read messages**:
- Make sure bot is admin in the group
- Check bot has "Delete Messages" permission
- Verify group ID is correct (negative number)

**No signals detected**:
- Check signal format matches the regex pattern
- Verify `_looks_like_signal()` function logic
- Enable debug logging to see all messages

**Bot not responding**:
- Check bot token is correct
- Verify internet connection
- Check Telegram API status

**Permission errors**:
- Bot needs admin rights to read all messages
- Only group admins can add bots as admins

### Debug Mode
Enable detailed logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Check Bot Status
```bash
# View bot logs
journalctl -u telegram-signal-bot -f

# Check if bot is running
ps aux | grep telegram_bot
```

## 📝 Example Signal Formats Supported

The bot can detect these signal formats:

```
# Format 1: Standard
Buy BTCUSDT
Entry: 45000
TP: 47000
SL: 43000

# Format 2: With labels
LONG ETHUSDT
Entry Price: 2600.50
Take Profit: 2750.00
Stop Loss: 2450.00

# Format 3: Compact
BUY $BTC @ 45000 | TP: 47000 | SL: 43000
```

## 🎯 Next Steps

1. **Test with small positions** in paper trading mode
2. **Monitor for 1-2 weeks** to ensure reliability
3. **Gradually increase position sizes** as confidence builds
4. **Consider live trading** only after proven success

---

**⚠️ Important**: Always test thoroughly in paper trading mode before using real money. Monitor the bot closely for the first few days to ensure it's working correctly with your specific group's signal format.