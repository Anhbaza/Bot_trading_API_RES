"""
Bot Trading API REST Utilities Module
Contains utility functions and helpers for calculations and validations
"""

from datetime import datetime

# Module information
__version__ = "1.0.0"
__author__ = "Anhbaza"
__created_at__ = "2025-05-22 13:42:28"

# Import utilities
from .calculations import (
    calculate_delta,
    calculate_ma,
    calculate_rsi,
    calculate_poc,
    calculate_volume_profile,
    calculate_support_resistance,
    calculate_risk_reward_ratio
)

from .validators import (
    validate_price,
    validate_quantity,
    validate_symbol,
    validate_timeframe,
    validate_trade_parameters
)

# Module configuration
UTILS_CONFIG = {
    'user_login': 'Anhbaza',
    'start_time': datetime.strptime(__created_at__, '%Y-%m-%d %H:%M:%S'),
    'environment': 'production'
}

# Export all utilities
__all__ = [
    # Calculations
    'calculate_delta',
    'calculate_ma',
    'calculate_rsi',
    'calculate_poc',
    'calculate_volume_profile',
    'calculate_support_resistance',
    'calculate_risk_reward_ratio',
    
    # Validators
    'validate_price',
    'validate_quantity',
    'validate_symbol',
    'validate_timeframe',
    'validate_trade_parameters',
    
    # Configuration
    'UTILS_CONFIG'
]
