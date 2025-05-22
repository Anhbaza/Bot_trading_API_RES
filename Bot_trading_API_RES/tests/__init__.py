"""
Bot Trading API REST Test Suite
Contains unit tests and integration tests for the trading system
"""

from datetime import datetime

# Test module information
__version__ = "1.0.0"
__author__ = "Anhbaza"
__created_at__ = "2025-05-22 13:48:00"

# Test configuration
TEST_CONFIG = {
    'user_login': 'Anhbaza',
    'start_time': datetime.strptime(__created_at__, '%Y-%m-%d %H:%M:%S'),
    'environment': 'testing'
}

# Import test modules
from .test_analyzers import *

# Export test configuration
__all__ = [
    'TEST_CONFIG'
]
