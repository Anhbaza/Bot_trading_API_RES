"""
Bot Trading API REST Analyzer Module
Contains market analysis and trading signal generation components
"""

from datetime import datetime

# Module information
__version__ = "1.0.0"
__author__ = "Anhbaza"
__created_at__ = "2025-05-22 13:37:56"

# Import analyzers
from .market_trend import MarketTrendAnalyzer
from .futures import FuturesAnalyzer

# Runtime configuration
ANALYZER_CONFIG = {
    'user_login': 'Anhbaza',
    'start_time': datetime.strptime(__created_at__, '%Y-%m-%d %H:%M:%S'),
    'environment': 'production'
}

# Export components
__all__ = [
    'MarketTrendAnalyzer',
    'FuturesAnalyzer',
    'ANALYZER_CONFIG'
]
