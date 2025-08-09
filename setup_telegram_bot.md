# 📱 Setting Up Your Telegram Bot for Alerts

## Quick Setup (2 minutes)

### Step 1: Start a Chat with Your Bot
1. Open Telegram on your phone
2. Search for: **@MonkeyAttack_ProfitHit_Bot**
3. Click "START" or send any message like "Hello"

### Step 2: Get Your Chat ID
After sending a message to the bot, run this command:

```bash
python get_chat_id.py
```

This will show your actual chat ID.

### Step 3: Update Your .env File
Replace the chat ID in your .env with the correct one:

```env
TELEGRAM_CHAT_ID=YOUR_ACTUAL_CHAT_ID
```

### Step 4: Test the Connection
```bash
python test_telegram.py
```

You should receive a test message!

## Troubleshooting

### Bot Not Responding?
The bot token is correct, but you need to:
1. Start a conversation with the bot first
2. The bot can only send messages to users who have initiated contact

### Wrong Chat ID?
The chat ID `6585156851` might be from a different bot or account. You need YOUR chat ID with THIS bot.

### Want a Group Instead?
1. Create a Telegram group
2. Add @MonkeyAttack_ProfitHit_Bot to the group
3. Make the bot an admin
4. Send a message in the group
5. Run `get_chat_id.py` to get the group's ID (will be negative)

## Alternative: Use Your Existing Bot

If you have another bot that's already working with the chat ID `6585156851`, update the token in .env:

```env
TELEGRAM_BOT_TOKEN=your_working_bot_token
TELEGRAM_CHAT_ID=6585156851
```

---

Once you've started a chat with @MonkeyAttack_ProfitHit_Bot, the automation will work perfectly!