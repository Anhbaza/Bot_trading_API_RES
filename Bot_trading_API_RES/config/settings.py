"""
Configuration settings for Bot Trading API REST
Loads environment variables and defines global constants
"""

import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

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
    """
    Setup and validate environment configuration
    
    Returns:
    --------
    bool
        True if setup successful, False otherwise
    """
    # Required environment variables
    required_vars = [
        'BINANCE_API_KEY',
        'BINANCE_API_SECRET',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]
    
    # Load environment variables
    env_vars = load_env_vars()
    
    # Check for missing variables
    missing_vars = [var for var in required_vars if var not in env_vars]
    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    # Store configuration
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
    
    # Create configuration file
    config_file = DATA_DIR / 'config.json'
    with open(config_file, 'w') as f:
        # Remove sensitive data before saving
        safe_config = CONFIG.copy()
        for key in ['BINANCE_API_KEY', 'BINANCE_API_SECRET', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']:
            safe_config[key] = '***'
        json.dump(safe_config, f, indent=4)
    
    print("\n✅ Environment setup completed successfully")
    print(f"📝 Configuration saved to: {config_file}")
    return True

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
