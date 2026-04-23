import json
from .constants import BASE_DIR

def load_config() -> dict:
    """Load configuration from config.json"""
    config_path = BASE_DIR / "config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def get_config_with_defaults() -> dict:
    """Returns the config merged with standard system defaults"""
    config = load_config()
    
    defaults = {
        "ai_settings": {
            "openai": {
                "model": "gpt-4o",
                "temperature": 1.0,
                "api_key": ""
            },
            "deepseek": {
                "model": "deepseek-chat",
                "temperature": 1.0,
                "api_key": ""
            }
        },
        "ai_validation": {
            "min_clip_duration": 15,
            "max_clip_duration": 60
        },
        "caption_settings": {
            "words_per_caption": 2,
            "font_family": "Arial",
            "font_size": 80,
            "vertical_position": 80,
            "text_color": "#FFFFFF",
            "outline_color": "#000000",
            "outline_width": 3,
            "outline_opacity": 100,
            "alignment": 2
        },
        "downloader_backend": "yt-dlp"
    }
    
    # Deep merge defaults with actual config
    def deep_merge(dict1, dict2):
        for key, value in dict2.items():
            if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
                deep_merge(dict1[key], value)
            else:
                dict1[key] = value
        return dict1

    return deep_merge(defaults, config)

def save_config(config: dict):
    """Save configuration to config.json"""
    config_path = BASE_DIR / "config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
