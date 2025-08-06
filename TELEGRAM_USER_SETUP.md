# 📱 Telegram User Account Setup Guide

This guide shows how to use **your personal Telegram account** to read trading signals from private groups you're already a member of. No need to add bots to groups!

## 🔑 Step 1: Get Telegram API Credentials

You need to register your application with Telegram to get API access:

### Register Your Application
1. Go to **https://my.telegram.org/apps**
2. Login with your phone number (the same one as your Telegram account)
3. Click **"Create new application"**
4. Fill in the form:
   - **App title**: `Crypto Paper Trading`
   - **Short name**: `crypto_trading`
   - **URL**: Leave blank or use `https://crypto.profithits.app`
   - **Platform**: Choose "Desktop"
   - **Description**: `Personal crypto trading signal monitor`

5. Click **"Create application"**
6. **Save these values** (you'll need them):
   - **API ID**: A number like `1234567`
   - **API Hash**: A string like `abc123def456...`

## ⚙️ Step 2: Update Environment Configuration

Add these to your `.env` file:

```bash
# Telegram User API Configuration
TELEGRAM_API_ID=1234567  # Replace with your API ID
TELEGRAM_API_HASH=abc123def456...  # Replace with your API Hash
TELEGRAM_PHONE_NUMBER=+1234567890  # Your phone number with country code
TELEGRAM_MONITORED_GROUPS=Crypto Signals VIP,Trading Group Pro,Signal Masters  # Group names
TELEGRAM_CHAT_ID=6585156851  # Your chat ID for notifications

# Alternative: Use group IDs instead of names
# TELEGRAM_MONITORED_GROUPS=-1001234567890,-1009876543210
```

**Important**: 
- Use your phone number with country code (e.g., `+1234567890`)
- Group names should match exactly (case sensitive)
- You can mix group names and IDs

## 📦 Step 3: Install Dependencies

```bash
# In your project directory
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install Telethon (Telegram user client library)
pip install telethon cryptg
```

## 🚀 Step 4: First Run and Authentication

### Test Your Setup
```bash
# Run the user client
python telegram_user_client.py
```

### What Will Happen:
1. **First run**: You'll be asked to enter the verification code sent to your phone
2. **Authentication**: Login with your Telegram account
3. **Session saved**: A session string will be generated (save this!)
4. **Groups listed**: All your groups will be displayed
5. **Monitoring starts**: Bot will watch for trading signals

### Save Your Session String
On first run, you'll see something like:
```
Session string (save this to TELEGRAM_SESSION_STRING in .env):
1BVtsOHwAa1b2c3d4e5f6g7h8i9j0k...
```

**Add this to your `.env` file**:
```bash
TELEGRAM_SESSION_STRING=1BVtsOHwAa1b2c3d4e5f6g7h8i9j0k...
```

This prevents having to re-authenticate every time.

## 🎯 Step 5: Configure Group Monitoring

### Find Your Groups
When you run the script, it will list all your groups:
```
📱 Crypto Signals VIP
   ID: -1001234567890
   Username: @cryptosignals

📱 Trading Masters
   ID: -1009876543210
```

### Update Configuration
Choose which groups to monitor by updating `.env`:

**Option 1: By Group Name**
```bash
TELEGRAM_MONITORED_GROUPS=Crypto Signals VIP,Trading Masters,Signal Alerts
```

**Option 2: By Group ID** (more reliable)
```bash
TELEGRAM_MONITORED_GROUPS=-1001234567890,-1009876543210
```

**Option 3: Mixed**
```bash
TELEGRAM_MONITORED_GROUPS=Crypto Signals VIP,-1009876543210,@tradingpro
```

## 🔍 Step 6: Test Signal Detection

### Send a Test Signal
In one of your monitored groups, post a test message:
```
Buy BTCUSDT
Entry: 45000
TP: 47000
SL: 43000
```

### Check Logs
You should see:
```
🎯 Potential signal detected from Crypto Signals VIP
✅ TRADE EXECUTED
Source: Crypto Signals VIP
Signal: Trade added: BTCUSDT Buy @ 45000.0
Mode: PAPER
Stats: 1✅ / 0❌
```

## 📊 Step 7: Monitor Performance

### Check Notifications
The script will send you Telegram messages about:
- ✅ Successful trades
- ❌ Failed trades  
- ⚠️ Rejected signals
- 🚨 Errors

### View Logs
```bash
# See real-time logs
tail -f logs/trading.log

# Or if running as service
journalctl -u telegram-user-client -f
```

## 🌐 Step 8: Deploy to VPS

### Upload to Server
```bash
# On your VPS
cd /root/crypto-paper-trading
git pull origin main

# Install new dependencies
source venv/bin/activate
pip install telethon cryptg
```

### Update VPS Configuration
```bash
# Edit .env on VPS
nano .env

# Add your Telegram credentials:
TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=abc123def456...
TELEGRAM_PHONE_NUMBER=+1234567890
TELEGRAM_SESSION_STRING=1BVtsOHwAa1b2c3d4e5f6g7h8i9j0k...
TELEGRAM_MONITORED_GROUPS=Crypto Signals VIP,Trading Masters
```

### Create Systemd Service
```bash
sudo tee /etc/systemd/system/telegram-user-client.service << EOF
[Unit]
Description=Telegram User Signal Client
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/crypto-paper-trading
Environment=PATH=/root/crypto-paper-trading/venv/bin
ExecStart=/root/crypto-paper-trading/venv/bin/python telegram_user_client.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable telegram-user-client
sudo systemctl start telegram-user-client
```

### Check Service Status
```bash
sudo systemctl status telegram-user-client
journalctl -u telegram-user-client -f
```

## 🔒 Security & Privacy

### What This Script Can Access
- ✅ Messages from groups you're already in
- ✅ Your contact list (for finding group members)
- ✅ Send messages as you (for notifications)

### What It Cannot Access
- ❌ Messages from groups you're not in
- ❌ Private chats (unless you configure it)
- ❌ Other people's private data

### Best Practices
1. **Keep API credentials secure** - Never share API ID/Hash
2. **Monitor activity** - Check notifications regularly
3. **Limit group access** - Only monitor trusted trading groups
4. **Regular updates** - Keep session string updated
5. **Use strong passwords** - Secure your Telegram account

## 🛠️ Advanced Configuration

### Custom Signal Patterns
Edit the `_looks_like_signal()` function in `telegram_user_client.py`:
```python
def _looks_like_signal(self, text: str) -> bool:
    # Add your custom signal detection logic
    signal_keywords = [
        'buy', 'sell', 'long', 'short',
        'entry', 'tp', 'sl', 'target',
        'alert', 'signal'  # Add custom keywords
    ]
    # Your logic here
```

### Message Filtering
You can filter by sender or message content:
```python
async def handle_message(self, event):
    sender = await event.get_sender()
    
    # Only process messages from specific users
    trusted_users = ['TradingExpert', 'SignalMaster']
    if sender.username not in trusted_users:
        return
    
    # Continue processing...
```

### Multiple Trading Modes
Monitor different groups for different trading modes:
```python
# In your config
paper_groups = ['Test Signals', 'Learning Group']
live_groups = ['VIP Signals', 'Premium Trading']

# Process differently based on source group
if chat_title in paper_groups:
    # Force paper trading
    pass
elif chat_title in live_groups:
    # Allow live trading
    pass
```

## 🔍 Troubleshooting

### Common Issues

**"Invalid phone number"**:
- Use international format: `+1234567890`
- Include country code
- No spaces or special characters

**"Session expired"**:
- Delete the session file and re-authenticate
- Generate new session string
- Update `TELEGRAM_SESSION_STRING` in .env

**"No signals detected"**:
- Check group names exactly match
- Verify signal format in logs
- Test `_looks_like_signal()` function

**"Flood wait" errors**:
- Telegram rate limiting - wait and retry
- Reduce notification frequency
- Use delays between operations

### Debug Mode
Enable detailed logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Test Connection
```bash
python -c "
from telethon import TelegramClient
import asyncio
import os

async def test():
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')
    client = TelegramClient('test', api_id, api_hash)
    await client.start()
    me = await client.get_me()
    print(f'Connected as: {me.first_name}')
    await client.disconnect()

asyncio.run(test())
"
```

## 📝 Example Signal Formats Supported

```
# Standard Format
Buy BTCUSDT
Entry: 45000
TP: 47000
SL: 43000

# With additional info
🚀 LONG SIGNAL 🚀
Pair: ETHUSDT
Entry: 2600-2620
Target 1: 2700
Target 2: 2800
Stop Loss: 2500

# Compact format
BUY $BTC @ 45k | TP: 47k | SL: 43k

# With emojis
📈 Buy ADAUSDT
🎯 Entry: 0.45
✅ TP: 0.50
❌ SL: 0.40
```

## 🎯 Next Steps

1. **Get your API credentials** from https://my.telegram.org/apps
2. **Test locally** with paper trading first
3. **Monitor for 1-2 weeks** to ensure reliability
4. **Deploy to VPS** for 24/7 operation
5. **Scale gradually** as confidence builds

---

**✅ Advantages of User Account Method:**
- No need to add bots to groups
- Works with any group you're already in
- Full access to message history
- More reliable than bot API
- Can read from channels and groups

**⚠️ Important**: This uses your personal Telegram account. Keep your API credentials secure and monitor the activity regularly!