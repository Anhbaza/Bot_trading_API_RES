"""
Configuration settings for Bot Trading API REST
Loads environment variables and defines global constants
"""

import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import os
from dotenv import load_dotenv


# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

# Ensure directories exist
for directory in [DATA_DIR, LOG_DIR]:
    directory.mkdir(exist_ok=True)

# Trading Parameters
TRADING_CONFIG = {
    # Timeframes
    'TIMEFRAMES': ['3m', '5m', '15m'],
    'PRIMARY_TIMEFRAME': '5m',
    
    # Volume Parameters
    'MIN_24H_VOLUME': 300_000,     # 300K USDT
    'MAX_SPREAD': 0.003,           # 0.3%
    'MAX_FUNDING_RATE': 0.001,     # 0.1%
    'MIN_OI': 200_000,             # 200K USDT
    'MAX_OI': 200_000_000_000,     # 200B USDT
    
    # Technical Analysis
    'RSI_OVERBOUGHT': 65,
    'RSI_OVERSOLD': 35,
    'DELTA_THRESHOLD': 0.0,
    
    # Volume Zones
    'PRICE_RANGE_PERCENT': 0.2,
    'VOLUME_THRESHOLD': 1.2,
    'COUNT_THRESHOLD': 1.2,
    'MIN_LS_RATIO': 1.3,
    'MAX_LS_RATIO': 10.0,
    
    # Rate Limiting
    'RATE_LIMIT_DELAY': 0.5,
    'MAX_RETRIES': 3,
    
    # Position Management
    'MAX_POSITIONS': 5,
    'MAX_RISK_PER_TRADE': 0.02,    # 2% risk per trade
    'DEFAULT_LEVERAGE': 5,
    
    # Time Settings
    'SCAN_INTERVAL': 30,           # seconds
    'POSITION_CHECK_INTERVAL': 10,  # seconds
    
    # User Settings
    'USER_LOGIN': 'Anhbaza',
    'CURRENT_TIME': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
}

def load_env_vars(env_file: str = 'data.env') -> Dict[str, str]:
    """
    Load environment variables from .env file
    
    Parameters:
    -----------
    env_file : str
        Path to the environment file
        
    Returns:
    --------
    Dict[str, str]
        Dictionary of loaded environment variables
    """
    env_vars = {}
    
    if os.path.exists(env_file):
        print(f"\n📁 Loading environment from: {os.path.abspath(env_file)}")
        
        with open(env_file) as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
                    env_vars[key] = value
                    print(f"✅ Loaded: {key}")
                    
    return env_vars

def setup_environment() -> bool:
    """Setup and validate environment"""
    env_vars = load_env_vars()
    if not env_vars:
        return False
        
    # Setup configuration
    global CONFIG
    CONFIG = {
        # API Configuration
        'BINANCE_API_KEY': env_vars.get('BINANCE_API_KEY', ''),
        'BINANCE_API_SECRET': env_vars.get('BINANCE_API_SECRET', ''),
        'TELEGRAM_BOT_TOKEN': env_vars.get('TELEGRAM_BOT_TOKEN', ''),
        'TELEGRAM_CHAT_ID': env_vars.get('TELEGRAM_CHAT_ID', ''),
        
        # Trading Configuration
        **TRADING_CONFIG
    }
    
    # Validate configuration
    return validate_config()

def get_config(key: str) -> Any:
    """
    Get configuration value by key
    
    Parameters:
    -----------
    key : str
        Configuration key
        
    Returns:
    --------
    Any
        Configuration value or None if not found
    """
    return CONFIG.get(key)
def validate_config() -> bool:
    """
    Validate configuration values
    
    Returns:
    --------
    bool
        True if valid, False otherwise
    """
    try:
        # Validate trading parameters
        if CONFIG['MIN_24H_VOLUME'] <= 0:
            raise ValueError("MIN_24H_VOLUME must be positive")
        if not 0 <= CONFIG['MAX_SPREAD'] <= 1:
            raise ValueError("MAX_SPREAD must be between 0 and 1")
        if not 0 <= CONFIG['MAX_FUNDING_RATE'] <= 1:
            raise ValueError("MAX_FUNDING_RATE must be between 0 and 1")
        if CONFIG['MIN_OI'] <= 0:
            raise ValueError("MIN_OI must be positive")
        if CONFIG['MAX_OI'] <= CONFIG['MIN_OI']:
            raise ValueError("MAX_OI must be greater than MIN_OI")
            
        # Validate risk parameters
        if not 0 < CONFIG['MAX_POSITIONS'] <= 10:
            raise ValueError("MAX_POSITIONS must be between 1 and 10")
        if not 0 < CONFIG['MAX_RISK_PER_TRADE'] <= 0.05:
            raise ValueError("MAX_RISK_PER_TRADE must be between 0 and 0.05")
        if not 1 <= CONFIG['DEFAULT_LEVERAGE'] <= 125:
            raise ValueError("DEFAULT_LEVERAGE must be between 1 and 125")
            
        return True
        
    except Exception as e:
        print(f"Configuration validation failed: {str(e)}")
        return False
def load_settings() -> Dict[str, Any]:
    """
    Load settings from environment variables and data.env file
    
    Returns
    -------
    Dict[str, Any]
        Dictionary containing all settings
    """
    # Load .env file
    env_file = 'data.env'
    if not os.path.exists(env_file):
        raise FileNotFoundError(
            f"Missing {env_file} file. Please create it with your configuration settings."
        )
    
    load_dotenv(env_file)
    
    # Required settings with validation
    required_settings = {
        'BINANCE_API_KEY': {
            'type': str,
            'min_length': 64,
            'error': 'Invalid Binance API key format'
        },
        'BINANCE_API_SECRET': {
            'type': str,
            'min_length': 64,
            'error': 'Invalid Binance API secret format'
        },
        'TELEGRAM_BOT_TOKEN': {
            'type': str,
            'min_length': 45,
            'error': 'Invalid Telegram bot token format'
        },
        'TELEGRAM_CHAT_ID': {
            'type': str,
            'min_length': 5,
            'error': 'Invalid Telegram chat ID format'
        }
    }
    
    # Optional settings with defaults
    optional_settings = {
        'ENVIRONMENT': ('development', str),
        'LOG_LEVEL': ('INFO', str),
        'RATE_LIMIT_DELAY': (0.5, float),
        'MIN_24H_VOLUME': (300000, float),
        'MAX_SPREAD': (0.003, float),
        'MAX_FUNDING_RATE': (0.001, float),
        'MIN_OI': (200000, float),
        'MAX_OI': (200000000000, float),
        'TREND_MIN_STRENGTH': (1.0, float),
        'TREND_IDEAL_STRENGTH': (1.5, float),
        'MIN_LS_RATIO': (1.3, float),
        'MAX_LS_RATIO': (10.0, float)
    }
    
    settings = {}
    
    # Validate required settings
    missing_vars = []
    invalid_vars = []
    
    for var_name, validation in required_settings.items():
        value = os.getenv(var_name)
        if not value:
            missing_vars.append(var_name)
            continue
            
        if len(value) < validation['min_length']:
            invalid_vars.append(f"{var_name}: {validation['error']}")
            continue
            
        settings[var_name] = value
        
    if missing_vars:
        raise ValueError(
            "Missing required environment variables in data.env:\n- " + 
            "\n- ".join(missing_vars)
        )
        
    if invalid_vars:
        raise ValueError(
            "Invalid environment variables in data.env:\n- " + 
            "\n- ".join(invalid_vars)
        )
    
    # Load optional settings with defaults
    for var_name, (default_value, var_type) in optional_settings.items():
        value = os.getenv(var_name)
        if value is None:
            settings[var_name] = default_value
        else:
            try:
                settings[var_name] = var_type(value)
            except ValueError:
                settings[var_name] = default_value
    
    return settings

# Initialize global configuration
CONFIG: Dict[str, Any] = {}

# Export configuration
__all__ = [
    'setup_environment',
    'load_env_vars',
    'get_config',
    'CONFIG',
    'BASE_DIR',
    'DATA_DIR',
    'LOG_DIR'
]
