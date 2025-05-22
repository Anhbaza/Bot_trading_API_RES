"""
Bot Trading API REST Core Module
Contains the main trading logic and analysis components
"""

from datetime import datetime
from typing import Dict, Any

# Core module information
__version__ = "1.0.0"
__author__ = "Anhbaza"
__copyright__ = f"Copyright (c) 2025, {__author__}"

# Runtime information
RUNTIME_INFO: Dict[str, Any] = {
    'start_time': datetime.strptime('2025-05-22 13:36:32', '%Y-%m-%d %H:%M:%S'),
    'user_login': 'Anhbaza',
    'environment': 'production'
}

# Import core components
from .analyzer import MarketTrendAnalyzer, FuturesAnalyzer
from .models import MarketState, MarketTrend, VolumeZone, SignalData
from .utils import calculations

def get_runtime_info() -> Dict[str, Any]:
    """
    Get current runtime information
    
    Returns:
    --------
    Dict[str, Any]
        Runtime information including start time, user, and status
    """
    return {
        **RUNTIME_INFO,
        'uptime': (datetime.utcnow() - RUNTIME_INFO['start_time']).total_seconds(),
        'current_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }

# Export core components
__all__ = [
    'MarketTrendAnalyzer',
    'FuturesAnalyzer',
    'MarketState',
    'MarketTrend',
    'VolumeZone',
    'SignalData',
    'calculations',
    'get_runtime_info',
    'RUNTIME_INFO'
]
