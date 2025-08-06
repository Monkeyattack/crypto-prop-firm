#!/usr/bin/env python3
"""
Deploy updated notification system to VPS
"""

import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_command(command, description):
    """Run a command and log the result"""
    logger.info(f"Running: {description}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✅ {description} - Success")
            if result.stdout:
                logger.info(f"Output: {result.stdout.strip()}")
        else:
            logger.error(f"❌ {description} - Failed")
            logger.error(f"Error: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        logger.error(f"❌ {description} - Exception: {e}")
        return False

def deploy_to_vps():
    """Deploy notification updates to VPS"""
    
    # Files to copy to VPS
    files_to_copy = [
        'telegram_notifier.py',
        'automated_signal_monitor.py', 
        'position_monitor.py'
    ]
    
    logger.info("🚀 Starting notification system deployment to VPS...")
    
    # Copy files to VPS
    for file in files_to_copy:
        success = run_command(
            f'scp -i ~/.ssh/tao_alpha_dca_key {file} root@172.93.51.42:/root/crypto-paper-trading/',
            f"Copy {file} to VPS"
        )
        if not success:
            logger.error(f"Failed to copy {file}")
            return False
    
    # Update .env file on VPS with notification bot token
    env_update = '''
# Telegram notifications
TELEGRAM_BOT_TOKEN=7169619484:AAF2Kea4mskf8kWeq4Ugj-Fop7qZ8cGudT8
TELEGRAM_CHAT_ID=6585156851
'''
    
    success = run_command(
        f'ssh -i ~/.ssh/tao_alpha_dca_key root@172.93.51.42 "echo \'{env_update}\' >> /root/crypto-paper-trading/.env"',
        "Update .env file with notification credentials"
    )
    
    if not success:
        logger.error("Failed to update .env file")
        return False
    
    # Restart PM2 services to load new code
    services = ['signal-monitor', 'position-monitor']
    
    for service in services:
        success = run_command(
            f'ssh -i ~/.ssh/tao_alpha_dca_key root@172.93.51.42 "cd /root/crypto-paper-trading && pm2 restart {service}"',
            f"Restart {service} service"
        )
        if not success:
            logger.warning(f"Failed to restart {service}")
    
    # Check status
    run_command(
        f'ssh -i ~/.ssh/tao_alpha_dca_key root@172.93.51.42 "cd /root/crypto-paper-trading && pm2 status"',
        "Check PM2 status"
    )
    
    logger.info("✅ Notification system deployment completed!")
    logger.info("🔔 The system will now send Telegram notifications for:")
    logger.info("   • New signals detected")
    logger.info("   • Signal processing (accepted/rejected)")
    logger.info("   • Trade openings with targets")
    logger.info("   • Trade closures with P&L")
    logger.info("   • Trailing stop updates")
    logger.info("   • System errors")
    
    return True

if __name__ == "__main__":
    deploy_to_vps()