# 🚀 VPS Deployment Guide for crypto.profithits.app

## Prerequisites
- VPS: 172.93.51.42 (Ubuntu 24.04 LTS)
- Domain: crypto.profithits.app (CloudFlare DNS configured)
- SSH Access: `ssh root@172.93.51.42`

## Step 1: Deploy Application

SSH to your VPS and run:

```bash
cd /root
bash <(curl -s https://raw.githubusercontent.com/Monkeyattack/crypto-paper-trading/main/deploy_to_vps.sh)
```

Or manually:

```bash
# Clone repository
git clone https://github.com/Monkeyattack/crypto-paper-trading.git
cd crypto-paper-trading

# Run deployment script
chmod +x deploy_to_vps.sh
./deploy_to_vps.sh
```

## Step 2: Configure Nginx

```bash
# Set up nginx for crypto.profithits.app
chmod +x setup_nginx_crypto.sh
./setup_nginx_crypto.sh
```

## Step 3: Set up Systemd Service

```bash
# Configure auto-start service
chmod +x setup_systemd_service.sh
./setup_systemd_service.sh
```

## Step 4: Set up Telegram Integration

```bash
# Authenticate Telegram (one-time setup)
source venv/bin/activate
python telegram_session_setup.py
```

This will:
1. Send verification code to +14692238202
2. Prompt you to enter the code
3. Save session string to .env file
4. Find your target group

## Step 5: Test Deployment

```bash
# Check service status
sudo systemctl status crypto-trading

# View logs
sudo journalctl -u crypto-trading -f

# Test web access
curl -I http://crypto.profithits.app
```

## Step 6: Start Telegram Monitoring (Optional)

```bash
# Start monitoring SMRT Signals - Crypto Channel
source venv/bin/activate
python telegram_user_client.py
```

## Verification

1. **Web Access**: https://crypto.profithits.app
2. **Service Status**: `sudo systemctl status crypto-trading`
3. **Nginx Status**: `sudo systemctl status nginx`
4. **Logs**: `sudo journalctl -u crypto-trading -n 50`

## Configuration Files

- **App Config**: `/root/crypto-paper-trading/.env`
- **Nginx Config**: `/etc/nginx/sites-available/crypto.profithits.app`
- **Service Config**: `/etc/systemd/system/crypto-trading.service`

## Troubleshooting

### Service Won't Start
```bash
sudo journalctl -u crypto-trading -n 20
sudo systemctl restart crypto-trading
```

### Nginx Issues
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Telegram Authentication
```bash
cd /root/crypto-paper-trading
source venv/bin/activate
python telegram_session_setup.py
```

## CloudFlare Configuration

Your domain crypto.profithits.app should be configured in CloudFlare with:
- **DNS A Record**: crypto.profithits.app → 172.93.51.42
- **SSL Mode**: Flexible (for HTTP origin)
- **Proxy Status**: Enabled (orange cloud)

## Security Notes

- Application runs on port 8501 (localhost only)
- Nginx proxies HTTPS → HTTP internally
- CloudFlare handles SSL termination
- Rate limiting configured for API endpoints

## Commands Reference

```bash
# Service Management
sudo systemctl start crypto-trading
sudo systemctl stop crypto-trading
sudo systemctl restart crypto-trading
sudo systemctl status crypto-trading

# View Logs
sudo journalctl -u crypto-trading -f          # Live logs
sudo journalctl -u crypto-trading -n 50       # Last 50 lines

# Nginx Management
sudo systemctl reload nginx
sudo nginx -t

# Update Application
cd /root/crypto-paper-trading
git pull origin main
sudo systemctl restart crypto-trading
```