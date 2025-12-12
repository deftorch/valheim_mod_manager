"""
Centralized Logging System with Rotation and Multiple Handlers
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from config.settings import Settings


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            )
        return super().format(record)


def setup_logger(name: str = None, level: str = None) -> logging.Logger:
    """
    Setup application logger with file and console handlers
    
    Args:
        name: Logger name (default: root logger)
        level: Logging level (default: from Settings)
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger_name = name or 'valheim_mod_manager'
    logger = logging.getLogger(logger_name)
    
    # Set level
    log_level = level or Settings.LOG_LEVEL
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create logs directory
    Settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # File handler with rotation
    log_file = Settings.LOGS_DIR / f"{logger_name}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=Settings.LOG_MAX_BYTES,
        backupCount=Settings.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler (only warnings and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    
    # Formatters
    file_format = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_format = ColoredFormatter(
        '%(levelname)-8s | %(message)s'
    )
    
    file_handler.setFormatter(file_format)
    console_handler.setFormatter(console_format)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


class LoggerMixin:
    """Mixin to add logging capability to any class"""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        if not hasattr(self, '_logger'):
            self._logger = setup_logger(self.__class__.__name__)
        return self._logger


def log_function_call(func):
    """Decorator to log function calls"""
    def wrapper(*args, **kwargs):
        logger = setup_logger()
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} returned: {result}")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} raised {type(e).__name__}: {e}")
            raise
    return wrapper


def create_session_log():
    """Create a new session log file"""
    session_file = Settings.LOGS_DIR / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    handler = logging.FileHandler(session_file, encoding='utf-8')
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    )
    
    logger = logging.getLogger('valheim_mod_manager')
    logger.addHandler(handler)
    
    return session_file


def cleanup_old_logs(days: int = 30):
    """Remove log files older than specified days"""
    logger = setup_logger()
    cutoff = datetime.now().timestamp() - (days * 86400)
    
    removed_count = 0
    for log_file in Settings.LOGS_DIR.glob("*.log*"):
        if log_file.stat().st_mtime < cutoff:
            try:
                log_file.unlink()
                removed_count += 1
            except Exception as e:
                logger.warning(f"Failed to remove old log {log_file}: {e}")
    
    if removed_count > 0:
        logger.info(f"Cleaned up {removed_count} old log files")
