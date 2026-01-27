"""
Structured logging utility for YTClipper
Provides emoji-enhanced logging with file output and live streaming support
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Create logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOG_FILE = LOGS_DIR / "ytclipper.log"

# Emoji prefixes for different log levels
EMOJI_MAP = {
    "DEBUG": "🔍",
    "INFO": "ℹ️",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "CRITICAL": "🚨",
    "SUCCESS": "✅",
    "PROGRESS": "⏳",
    "API": "🌐",
    "DOWNLOAD": "⬇️",
    "TRANSCRIBE": "🎙️",
    "ANALYZE": "🤖",
    "CLIP": "✂️",
    "UPLOAD": "⬆️",
}

class EmojiFormatter(logging.Formatter):
    """Custom formatter that adds emojis and colors to log messages"""

    def format(self, record):
        # Add emoji based on level
        emoji = EMOJI_MAP.get(record.levelname, "📝")

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')

        # Format the message
        message = super().format(record)

        return f"{emoji} [{timestamp}] {record.levelname}: {message}"

class LoggerSetup:
    """Centralized logger setup"""

    _logger = None

    @classmethod
    def get_logger(cls):
        """Get or create the logger instance"""
        if cls._logger is None:
            cls._logger = cls._setup_logger()
        return cls._logger

    @classmethod
    def _setup_logger(cls):
        """Setup the logger with file and console handlers"""
        logger = logging.getLogger("ytclipper")
        logger.setLevel(logging.DEBUG)

        # Remove existing handlers
        logger.handlers = []

        # File handler with rotation (10MB max, keep 5 backups)
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = EmojiFormatter('%(message)s')
        file_handler.setFormatter(file_formatter)

        # Console handler (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = EmojiFormatter('%(message)s')
        console_handler.setFormatter(console_formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

# Convenience function to get logger
def get_logger():
    """Get the ytclipper logger instance"""
    return LoggerSetup.get_logger()

# Custom log methods for specific actions
class CustomLogger:
    """Wrapper for custom logging methods"""

    def __init__(self):
        self.logger = get_logger()

    def success(self, message):
        """Log success message with checkmark emoji"""
        record = self.logger.makeRecord(
            self.logger.name, logging.INFO, "", 0,
            message, (), None
        )
        record.levelname = "SUCCESS"
        self.logger.handle(record)

    def progress(self, message):
        """Log progress message with hourglass emoji"""
        record = self.logger.makeRecord(
            self.logger.name, logging.INFO, "", 0,
            message, (), None
        )
        record.levelname = "PROGRESS"
        self.logger.handle(record)

    def api(self, message):
        """Log API-related message"""
        record = self.logger.makeRecord(
            self.logger.name, logging.INFO, "", 0,
            message, (), None
        )
        record.levelname = "API"
        self.logger.handle(record)

    def download(self, message):
        """Log download-related message"""
        record = self.logger.makeRecord(
            self.logger.name, logging.INFO, "", 0,
            message, (), None
        )
        record.levelname = "DOWNLOAD"
        self.logger.handle(record)

    def transcribe(self, message):
        """Log transcription-related message"""
        record = self.logger.makeRecord(
            self.logger.name, logging.INFO, "", 0,
            message, (), None
        )
        record.levelname = "TRANSCRIBE"
        self.logger.handle(record)

    def analyze(self, message):
        """Log AI analysis message"""
        record = self.logger.makeRecord(
            self.logger.name, logging.INFO, "", 0,
            message, (), None
        )
        record.levelname = "ANALYZE"
        self.logger.handle(record)

    def clip(self, message):
        """Log clip creation message"""
        record = self.logger.makeRecord(
            self.logger.name, logging.INFO, "", 0,
            message, (), None
        )
        record.levelname = "CLIP"
        self.logger.handle(record)

# Global logger instance
app_logger = CustomLogger()
