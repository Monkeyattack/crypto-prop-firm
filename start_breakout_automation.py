"""
Breakout Prop Semi-Automation Launcher
Simple script to start the automation system
"""

import asyncio
import os
import sys
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/breakout_automation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def check_environment():
    """Check if environment is properly configured"""
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID',
        'PROP_FIRM_MODE'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        logger.warning(f"Missing environment variables: {missing}")
        logger.info("Loading from .env file...")
        
        # Try to load from .env
        try:
            from dotenv import load_dotenv
            load_dotenv()
            logger.info(".env file loaded successfully")
        except ImportError:
            logger.error("python-dotenv not installed. Run: pip install python-dotenv")
            sys.exit(1)
    
    # Verify Telegram credentials
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        logger.error("Telegram credentials not configured!")
        logger.info("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file")
        sys.exit(1)
    
    logger.info("Environment configured successfully")
    return True

def display_startup_banner():
    """Display startup information"""
    banner = """
    ╔══════════════════════════════════════════════════╗
    ║                                                  ║
    ║     BREAKOUT PROP SEMI-AUTOMATION SYSTEM        ║
    ║                                                  ║
    ║     Trading Mode: $10,000 One-Step Evaluation   ║
    ║     Risk Mode: Adaptive                         ║
    ║     Alert Destination: Telegram                 ║
    ║                                                  ║
    ╚══════════════════════════════════════════════════╝
    """
    print(banner)
    
    print(f"Starting at: {datetime.now()}")
    print(f"Account Size: $10,000")
    print(f"Profit Target: $1,000 (10%)")
    print(f"Max Drawdown: $600 (6%)")
    print(f"Daily Loss Limit: $500 (5%)")
    print("-" * 54)

async def test_telegram_connection():
    """Test Telegram bot connection"""
    logger.info("Testing Telegram connection...")
    
    try:
        import aiohttp
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        test_message = {
            'chat_id': chat_id,
            'text': f"""
🚀 **Breakout Automation Started**

System is now monitoring for signals.
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Current Settings:
- Account: $10,000
- Risk per trade: 1.5%
- Max daily loss: $500
- Max drawdown: $600

Reply 'STOP' to pause monitoring.
""",
            'parse_mode': 'Markdown'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=test_message) as response:
                if response.status == 200:
                    logger.info("✅ Telegram connection successful")
                    return True
                else:
                    logger.error(f"❌ Telegram connection failed: {await response.text()}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Error testing Telegram: {e}")
        return False

async def main():
    """Main entry point"""
    # Display banner
    display_startup_banner()
    
    # Check environment
    if not check_environment():
        logger.error("Environment check failed")
        sys.exit(1)
    
    # Test Telegram connection
    if not await test_telegram_connection():
        logger.error("Cannot connect to Telegram. Please check your credentials.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Import and start the automation
    try:
        from breakout_semi_automation import BreakoutSemiAutomation
        
        logger.info("Initializing Breakout Semi-Automation...")
        automation = BreakoutSemiAutomation()
        
        logger.info("Starting monitoring loop...")
        logger.info("Press Ctrl+C to stop")
        
        await automation.start_monitoring()
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Automation stopped by user")
        
        # Send shutdown notification
        try:
            import aiohttp
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            shutdown_message = {
                'chat_id': chat_id,
                'text': f"⏹️ **Automation Stopped**\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                'parse_mode': 'Markdown'
            }
            
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=shutdown_message)
        except:
            pass
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 7):
        print("Python 3.7+ required")
        sys.exit(1)
    
    # Run the automation
    asyncio.run(main())