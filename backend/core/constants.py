from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent.parent

# Temp directory for intermediate files
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# Downloads directory
DOWNLOAD_DIR = BASE_DIR / "Downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Thumbnails directory
THUMBNAILS_DIR = BASE_DIR / "thumbnails"
THUMBNAILS_DIR.mkdir(exist_ok=True)

# Clips directory
CLIPS_DIR = BASE_DIR / "clips"
CLIPS_DIR.mkdir(exist_ok=True)

# Upload directory
UPLOAD_DIR = BASE_DIR / "ToUpload"
UPLOAD_DIR.mkdir(exist_ok=True)

# Log file path
LOG_FILE = BASE_DIR / "logs" / "ytclipper.log"
LOG_FILE.parent.mkdir(exist_ok=True)
