import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the paper trading system"""
    
    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', './trade_log.db')
    
    # Server Configuration
    STREAMLIT_PORT = int(os.getenv('STREAMLIT_PORT', 8501))
    N8N_PORT = int(os.getenv('N8N_PORT', 5678))
    
    # Trading Configuration
    INITIAL_CAPITAL = float(os.getenv('INITIAL_CAPITAL', 10000.00))
    DEFAULT_RISK_PERCENT = float(os.getenv('DEFAULT_RISK_PERCENT', 2.0))
    MAX_OPEN_TRADES = int(os.getenv('MAX_OPEN_TRADES', 5))
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', './logs/trading.log')
    
    @staticmethod
    def setup_logging():
        """Setup logging configuration"""
        log_dir = Path(Config.LOG_FILE).parent
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(Config.LOG_FILE),
                logging.StreamHandler()
            ]
        )
    
    @staticmethod
    def get_absolute_db_path():
        """Get absolute path to database file"""
        return os.path.abspath(Config.DATABASE_PATH)
    
    @staticmethod
    def validate_config():
        """Validate critical configuration"""
        errors = []
        
        if not os.path.exists(os.path.dirname(Config.get_absolute_db_path())):
            try:
                os.makedirs(os.path.dirname(Config.get_absolute_db_path()), exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create database directory: {e}")
        
        if Config.DEFAULT_RISK_PERCENT <= 0 or Config.DEFAULT_RISK_PERCENT > 10:
            errors.append("DEFAULT_RISK_PERCENT must be between 0 and 10")
        
        if Config.INITIAL_CAPITAL <= 0:
            errors.append("INITIAL_CAPITAL must be positive")
        
        if errors:
            raise ValueError("Configuration errors: " + "; ".join(errors))
        
        return True