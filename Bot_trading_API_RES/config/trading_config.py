"""Trading configuration parameters"""

CONFIDENCE_WEIGHTS = {
    'base': 0.4,
    'ls_ratio': 0.2,
    'trend': 0.2,
    'liquidity': 0.2
}

MARKET_PARAMS = {
    'price_range_percent': 1.0,
    'depth_limit': 100,
    'vol_threshold': 1.5,
    'cnt_threshold': 1.5,
    'lookback_period': 100
}

TECHNICAL_PARAMS = {
    'rsi_period': 14,
    'trend_period': 14,
    'ma_short': 20,
    'ma_long': 50
}

LOGGING_CONFIG = {
    'enabled': True,
    'log_file': 'trading_confidence.log',
    'level': 'INFO'
}
