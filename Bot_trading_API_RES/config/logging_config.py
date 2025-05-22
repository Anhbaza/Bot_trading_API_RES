"""
Logging configuration for Bot Trading API REST
Handles log formatting, file output, and logging levels
"""

import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_logging(
    log_level: str = "INFO",
    log_format: str = '%(asctime)s UTC | %(levelname)s | %(message)s',
    date_format: str = '%Y-%m-%d %H:%M:%S'
) -> logging.Logger:
    """
    Setup logging configuration with both console and file handlers
    
    Parameters:
    -----------
    log_level : str
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_format : str
        Format string for log messages
    date_format : str
        Format string for timestamps
        
    Returns:
    --------
    logging.Logger
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # Generate log filename with timestamp
    current_time = datetime.utcnow()
    log_filename = os.path.join(
        log_dir,
        f"bot_trading_{current_time.strftime('%Y%m%d')}.log"
    )
    
    # Setup basic logging config
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=date_format
    )
    
    # Get the root logger
    logger = logging.getLogger()
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter(log_format, datefmt=date_format)
    )
    logger.addHandler(console_handler)
    
    # Create file handler with rotation
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(
        logging.Formatter(log_format, datefmt=date_format)
    )
    logger.addHandler(file_handler)
    
    # Log startup information
    logger.info("="*50)
    logger.info("Bot Trading API REST - Logging Initialized")
    logger.info(f"Log Level: {log_level}")
    logger.info(f"Log File: {log_filename}")
    logger.info(f"Current Time (UTC): {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"User: Anhbaza")
    logger.info("="*50)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger with the standard configuration
    
    Parameters:
    -----------
    name : str
        Name for the logger, typically __name__
        
    Returns:
    --------
    logging.Logger
        Named logger instance
    """
    return logging.getLogger(name)
