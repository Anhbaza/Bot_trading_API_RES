"""
Bot Trading API REST Configuration Package
Initialize configuration settings and logging
"""

from .settings import setup_environment, load_env_vars
from .logging_config import setup_logging

# Version info
__version__ = "1.0.0"
__author__ = "Anhbaza"
__copyright__ = f"Copyright (c) 2025, {__author__}"

# Initialize package
__all__ = [
    'setup_environment',
    'setup_logging',
    'load_env_vars'
]
