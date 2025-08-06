# 🚀 Quick Start Guide - Get Paper Trading Now!

**Want to start paper trading in the next 5 minutes? Follow these steps:**

## ⚡ 5-Minute Setup

### 1. Setup Environment (2 minutes)
```bash
cd C:\Users\cmeredith\source\repos\crypto-paper-trading
python setup.py
```

### 2. Configure Settings (1 minute)
```bash
# Copy template
copy .env.template .env

# Edit .env file - change this line:
SECRET_KEY=your_random_secret_key_here_123456789
```

### 3. Launch Dashboard (1 minute)
```bash
# Activate environment
venv\Scripts\activate

# Start dashboard
streamlit run dashboard/app.py --server.port 8501
```

### 4. Open and Trade (1 minute)
1. Open: http://localhost:8501
2. Go to "Trade Management" 
3. Add your first trade!

## 🎯 Your First Paper Trade

**Try this sample trade:**
- Symbol: `BTCUSDT`
- Side: `Buy`
- Entry: `45000`
- Take Profit: `47000`
- Stop Loss: `43000`

Click "Add Trade" and you're paper trading! 🎉

## 📋 What's Next?

- [ ] Complete TODO.md checklist for full setup
- [ ] Add 2-3 more practice trades
- [ ] Explore all dashboard pages
- [ ] Set up your trading strategy rules
- [ ] Start daily trading routine

## 🔧 Skip Authentication (For Speed)

If Google OAuth is causing issues, temporarily disable it:

Edit `dashboard/app.py` lines 34-36:
```python
# Comment out these lines for now:
# if not auth.require_auth():
#     st.stop()
```

Restart the dashboard and you can trade immediately!

---

**🎯 Goal: Start paper trading today, master it for 30+ days, then consider live trading when consistently profitable!**