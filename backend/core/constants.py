from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent.parent

# Temp directory for intermediate files
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# Log file path
LOG_FILE = BASE_DIR / "logs" / "ytclipper.log"
LOG_FILE.parent.mkdir(exist_ok=True)
