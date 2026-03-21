import sys
from datetime import datetime
from .constants import LOG_FILE

class TeeOutput:
    """Write to both console and log file"""
    def __init__(self, file_path, original_stream):
        self.file = open(file_path, 'a', encoding='utf-8')
        self.original_stream = original_stream

    def write(self, message):
        # Write to console
        self.original_stream.write(message)
        self.original_stream.flush()
        # Write to file with timestamp
        if message.strip():  # Only log non-empty messages
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.file.write(f"[{timestamp}] {message}")
            self.file.flush()

    def flush(self):
        self.original_stream.flush()
        self.file.flush()

    def isatty(self):
        return self.original_stream.isatty()

def setup_logging():
    """Redirect stdout and stderr to also write to log file"""
    sys.stdout = TeeOutput(LOG_FILE, sys.stdout)
    sys.stderr = TeeOutput(LOG_FILE, sys.stderr)
