import json
from .constants import BASE_DIR

def load_config() -> dict:
    """Load configuration from config.json"""
    config_path = BASE_DIR / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

def save_config(config: dict):
    """Save configuration to config.json"""
    config_path = BASE_DIR / "config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
