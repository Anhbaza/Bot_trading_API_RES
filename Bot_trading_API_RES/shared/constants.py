#!/usr/bin/env python3
"""
Constants Module
Author: Anhbaza01
Version: 1.0.0
Last Updated: 2025-05-23 19:19:10 UTC
"""

# Bot Configuration
TRADING_BOT_NAME = "BinanceFuturesBot"
VERSION = "1.0.0"

# Trading Parameters
MAX_TRADES_PER_SYMBOL = 5
MIN_VOLUME_USDT = 1000000  # 1M USDT minimum volume
UPDATE_INTERVAL = 60       # 60 seconds

# Technical Indicators
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
EMA_SHORT = 20
EMA_LONG = 50

# Signal Parameters
VOLUME_RATIO_MIN = 2.0    # Minimum volume increase
MIN_RR_RATIO = 1.5        # Minimum Risk:Reward ratio
CONFIDENCE_THRESHOLD = 65  # Minimum confidence score

# Message Types
MSG_TYPE_SIGNAL = "SIGNAL"
MSG_TYPE_UPDATE = "UPDATE"
MSG_TYPE_CLOSE = "CLOSE"

# Scanning Modes
SCAN_MODE_ALL = "ALL"
SCAN_MODE_WATCHED = "WATCHED"