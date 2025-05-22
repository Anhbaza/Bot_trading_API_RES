"""
Bot Trading API REST Services Module
Contains external service integrations like Binance and Telegram
"""

from datetime import datetime

# Module information
__version__ = "1.0.0"
__author__ = "Anhbaza"
__created_at__ = "2025-05-22 13:45:47"

# Import services
from .binance_client import BinanceClient
from .telegram_notifier import TelegramNotifier

# Module configuration
SERVICES_CONFIG = {
    'user_login': 'Anhbaza',
    'start_time': datetime.strptime(__created_at__, '%Y-%m-%d %H:%M:%S'),
    'environment': 'production'
}

# Export services
__all__ = [
    'BinanceClient',
    'TelegramNotifier',
    'SERVICES_CONFIG'
]
