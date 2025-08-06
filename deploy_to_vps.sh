#!/bin/bash
# Deploy crypto paper trading app to VPS with crypto.profithits.app domain

set -e

echo "=== Deploying Crypto Paper Trading to VPS ==="

# Clone or update repository
if [ -d "/root/crypto-paper-trading" ]; then
    echo "Updating existing repository..."
    cd /root/crypto-paper-trading
    git pull origin main
else
    echo "Cloning repository..."
    cd /root
    git clone https://github.com/Monkeyattack/crypto-paper-trading.git
    cd crypto-paper-trading
fi

# Create virtual environment
echo "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
echo "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.template .env
    echo "TELEGRAM_API_ID=27540855" >> .env
    echo "TELEGRAM_API_HASH=0ad0e0e612829f4642c373ff0334df1e" >> .env
    echo "TELEGRAM_PHONE_NUMBER=+14692238202" >> .env
    echo "TELEGRAM_MONITORED_GROUPS=\"SMRT Signals - Crypto Channel\"" >> .env
    echo "TELEGRAM_BOT_TOKEN=8405614465:AAGl1MFkI4T7dksrk93oHXJOilcBXH36Do0" >> .env
    echo "TELEGRAM_CHAT_ID=6585156851" >> .env
    echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env
    echo ".env file created with production settings"
else
    echo ".env file already exists"
fi

# Create logs directory
mkdir -p logs

# Test the application
echo "Testing application..."
source venv/bin/activate
python -c "from database import DatabaseManager; db = DatabaseManager(); print('Database test: OK')"

echo "Application deployment complete!"
echo "Next steps:"
echo "1. Configure nginx for crypto.profithits.app"
echo "2. Set up systemd service"
echo "3. Configure SSL (handled by CloudFlare)"