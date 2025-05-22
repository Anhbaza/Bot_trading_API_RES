

from datetime import datetime

# Module information
__version__ = "1.0.0"
__author__ = "Anhbaza"
__created_at__ = "2025-05-22 13:40:19"

# Import all entities
from .entities import (
    MarketState,
    MarketTrend,
    VolumeZone,
    SignalData,
    OrderBookLevel,
    TradingPosition,
    OrderStatus,
    TradingStats
)

# Module configuration
MODEL_CONFIG = {
    'user_login': 'Anhbaza',
    'start_time': datetime.strptime(__created_at__, '%Y-%m-%d %H:%M:%S'),
    'environment': 'production'
}

def get_model_version() -> str:
    """Get current model version with timestamp"""
    return f"{__version__} ({__created_at__})"

# Export all models
__all__ = [
    'MarketState',
    'MarketTrend',
    'VolumeZone',
    'SignalData',
    'OrderBookLevel',
    'TradingPosition',
    'OrderStatus',
    'TradingStats',
    'get_model_version',
    'MODEL_CONFIG'
]
