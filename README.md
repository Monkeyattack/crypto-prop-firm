
# 💼 Crypto Prop Firm Trading System

A professional proprietary trading system for cryptocurrency, forked from crypto-paper-trading. Features institutional-grade risk management, automated signal processing from Telegram, and comprehensive analytics through a modern web dashboard.

## ✨ Features

### 🔒 **Security & Authentication**
- Google OAuth 2.0 authentication
- Role-based access control
- Session management with timeout
- Email whitelist for access control

### 📈 **Trading Features**
- Real-time signal processing from Telegram
- Advanced input validation and error handling
- Risk management with position sizing
- Multiple take-profit and stop-loss strategies
- Performance tracking and analytics

### 🎯 **Risk Management**
- Configurable position sizing (1-2% rule)
- Maximum open trades limit
- Risk-reward ratio validation
- Capital preservation safeguards
- Duplicate signal detection

### 📊 **Dashboard & Analytics**
- Modern Streamlit web interface
- Real-time portfolio tracking
- Performance metrics and statistics
- Interactive charts and visualizations
- Trade management interface

### 🔧 **Technical Features**
- Environment-based configuration
- Comprehensive logging system
- Database backup and recovery
- n8n workflow automation
- Production-ready deployment

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js (for n8n)
- Google OAuth credentials (optional)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd crypto-paper-trading
python setup.py
```

### 2. Configure Environment
Edit `.env` file with your settings:
```bash
# Database
DATABASE_PATH=./trade_log.db

# Trading Configuration
INITIAL_CAPITAL=10000.00
DEFAULT_RISK_PERCENT=2.0
MAX_OPEN_TRADES=5

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
ALLOWED_GOOGLE_EMAILS=your-email@gmail.com
```

### 3. Start Services
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Start dashboard
streamlit run dashboard/app.py --server.port 8501

# Start n8n (in another terminal)
n8n --port 5678
```

### 4. Access Dashboard
Open http://localhost:8501 in your browser.

## 📋 System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram      │    │   n8n Workflow   │    │   Database      │
│   Signals       │───►│   Processing     │───►│   (SQLite)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Streamlit      │    │  Signal          │    │   Risk          │
│  Dashboard      │◄───│  Processor       │◄───│   Management    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🗄️ Database Schema

### Tables
- **`trades`**: Individual trade records with entry, TP, SL, PnL
- **`capital`**: Total account balance history over time  
- **`capital_by_symbol`**: Current balance per trading pair

### Key Fields
```sql
trades (
    id, symbol, side, entry, tp, sl, result, pnl, timestamp
)

capital (
    id, value, timestamp
)

capital_by_symbol (
    id, symbol, value, timestamp
)
```

## 🔄 Signal Processing Flow

1. **Signal Reception**: Telegram webhook or manual input
2. **Parsing**: Extract symbol, side, entry, TP, SL
3. **Validation**: Check format, risk-reward ratio, duplicates
4. **Risk Check**: Verify position limits, capital requirements
5. **Execution**: Add to database, update capital tracking
6. **Notification**: Log results, send confirmations

## 📊 Trading Strategies & Theory

### Risk Management Principles
- **Position Sizing**: Never risk more than 1-2% per trade
- **Diversification**: Spread across multiple assets and timeframes
- **Risk-Reward**: Minimum 1:1 ratio, preferably 1:2 or better
- **Stop Losses**: Always defined before entry
- **Emotional Control**: Systematic approach, no FOMO trading

### Paper Trading Benefits
- **Risk-Free Learning**: Test strategies without financial loss
- **Strategy Development**: Refine entry/exit rules
- **Confidence Building**: Practice before live trading
- **Performance Analysis**: Track and improve results

## 🛠️ Configuration

### Environment Variables
```bash
# Required
DATABASE_PATH=./trade_log.db
SECRET_KEY=your-secret-key

# Trading
INITIAL_CAPITAL=10000.00
DEFAULT_RISK_PERCENT=2.0
MAX_OPEN_TRADES=5

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
ALLOWED_GOOGLE_EMAILS=user1@gmail.com,user2@gmail.com

# Optional
TELEGRAM_BOT_TOKEN=your-telegram-token
LOG_LEVEL=INFO
```

### Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add your domain to authorized origins
6. Set redirect URI to `http://your-domain.com`

## 🚀 Production Deployment

### Using Docker (Recommended)
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Using Systemd
```bash
# Copy service file
sudo cp crypto-paper-trading.service /etc/systemd/system/

# Enable and start
sudo systemctl enable crypto-paper-trading
sudo systemctl start crypto-paper-trading
```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## 🔧 Development

### Project Structure
```
crypto-paper-trading/
├── dashboard/
│   ├── app.py              # Main Streamlit application
│   └── requirements.txt    # Dashboard dependencies
├── auth.py                 # Google OAuth authentication
├── config.py               # Configuration management
├── database.py             # Database operations
├── signal_processor.py     # Signal parsing and validation
├── setup.py                # Automated setup script
├── requirements.txt        # Main dependencies
├── .env.template           # Environment template
└── n8n_workflow_sqlite.json # n8n workflow definition
```

### Adding New Features
1. Create feature branch
2. Add tests for new functionality
3. Update documentation
4. Submit pull request

### Running Tests
```bash
python -m pytest tests/
# or
python setup.py  # includes basic tests
```

## 📈 Performance Metrics

The dashboard tracks:
- **Total PnL**: Cumulative profit/loss
- **Win Rate**: Percentage of profitable trades
- **Risk-Reward Ratio**: Average reward vs risk
- **Drawdown**: Maximum loss from peak
- **Sharpe Ratio**: Risk-adjusted returns
- **Trade Frequency**: Trades per time period

## 🔐 Security Considerations

- Store credentials in environment variables
- Use HTTPS in production
- Regularly rotate API keys
- Monitor access logs
- Implement rate limiting
- Keep dependencies updated

## 🐛 Troubleshooting

### Common Issues
1. **Database locked**: Restart the application
2. **OAuth errors**: Check redirect URIs and credentials
3. **Signal parsing fails**: Verify message format
4. **Port conflicts**: Change ports in configuration

### Logs Location
- Application logs: `./logs/trading.log`
- Streamlit logs: Terminal output
- n8n logs: n8n interface

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 📞 Support

- Create an issue on GitHub
- Check the troubleshooting section
- Review logs for error details

---

**⚠️ Disclaimer**: This is a paper trading system for educational purposes. Past performance does not guarantee future results. Always conduct thorough testing before using any trading strategy with real money.
