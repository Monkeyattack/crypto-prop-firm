# CLAUDE.md - Crypto Prop Firm

## Project Overview
A professional proprietary trading system for cryptocurrency, forked from crypto-paper-trading. Features institutional-grade risk management, automated Telegram signal processing, and comprehensive analytics.

## Architecture
- **Framework**: Streamlit (Python)
- **Backend Port**: 8501 (Streamlit default)
- **Domain**: crypto.profithits.app
- **Alternative Domain**: webdev.monkeyattack.com (recommended to use)

## Infrastructure Configuration

### VPS Connection Info
- **SSH Command**: `ssh -i ~/.ssh/tao_alpha_dca_key root@172.93.51.42`
- **Server IP**: 172.93.51.42
- **SSH Key**: ~/.ssh/tao_alpha_dca_key
- **Domain**: crypto.profithits.app

### Port Configuration
- **Streamlit Port**: 8501 (default)
- **VPS Status**: NGINX configured but app not deployed
- **NGINX Config**: /etc/nginx/sites-available/crypto.profithits.app

### Deployment Info
- **App Directory**: Not yet deployed to VPS
- **Git Repository**: https://github.com/Monkeyattack/crypto-paper-trading (assumed)
- **PM2 Process**: Not configured

## Development Commands
- Setup: `pip install -r requirements.txt`
- Run: `streamlit run app.py --server.port 8501`
- Test: `pytest`
- Deploy: Need to create deployment script

## Current Status
- NGINX configuration exists on VPS
- Application not yet deployed
- Needs PM2 setup for Streamlit app

## Action Items
1. Deploy application to VPS
2. Configure PM2 for Streamlit
3. Update domain from crypto.profithits.app to webdev.monkeyattack.com
4. Test NGINX proxy configuration

## Access Notes
- Remember you have VPS access on all projects

---
Last Updated: 2025-08-03