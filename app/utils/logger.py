import os
import logging
from logging.handlers import RotatingFileHandler
import sys

# Create logs directory if it doesn't exist
logs_dir = os.environ.get('LOGS_DIR', '/logs')
if not os.path.exists(logs_dir):
    try:
        os.makedirs(logs_dir)
    except Exception as e:
        print(f"Error creating logs directory: {e}")
        logs_dir = '/tmp'  # Fallback to /tmp if logs directory can't be created

# Configure logging format
log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_logger(name):
    """
    Get a logger with the specified name
    
    Args:
        name: Logger name (usually the module name)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set log level from environment variable or default to INFO
    log_level_name = os.environ.get('LOG_LEVEL', 'INFO')
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Add console handler if not already added
    if not any(isinstance(h, logging.StreamHandler) and h.stream == sys.stdout for h in logger.handlers):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)
    
    # Add file handler if not already added
    log_file = os.path.join(logs_dir, f"{name.split('.')[-1]}.log")
    if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == log_file for h in logger.handlers):
        try:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10 MB
                backupCount=5
            )
            file_handler.setFormatter(log_format)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"Failed to create log file handler: {e}")
    
    return logger
