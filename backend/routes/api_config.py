from fastapi import APIRouter, HTTPException
from models.schemas import ConfigUpdate
from core.config import load_config, save_config

router = APIRouter()

@router.get("/api/config")
async def get_config():
    """Get current configuration"""
    config = load_config()
    return config

@router.post("/api/config")
async def update_config(config_update: ConfigUpdate):
    """Update configuration"""
    try:
        config = load_config()

        if config_update.downloader_backend is not None:
            config['downloader_backend'] = config_update.downloader_backend

        if config_update.caption_settings:
            config['caption_settings'] = {**config.get('caption_settings', {}), **config_update.caption_settings}

        if config_update.watermark_settings:
            config['watermark_settings'] = {**config.get('watermark_settings', {}), **config_update.watermark_settings}

        if config_update.ai_validation:
            config['ai_validation'] = {**config.get('ai_validation', {}), **config_update.ai_validation}

        save_config(config)

        return {"success": True, "config": config}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating config: {str(e)}")

@router.get("/api/strategies")
async def get_strategies():
    """Get list of available AI prompt strategies"""
    from core.constants import BASE_DIR
    try:
        strategy_folder = BASE_DIR / "ai-prompt-strategy"

        if not strategy_folder.exists():
            return {"success": True, "strategies": ["viral-moments"], "count": 1}

        # Find all .txt files in the strategy folder
        strategy_files = list(strategy_folder.glob("*.txt"))

        # Extract strategy names (filename without extension)
        strategies = [f.stem for f in strategy_files]

        # Sort alphabetically for consistent ordering
        strategies.sort()

        return {
            "success": True,
            "strategies": strategies,
            "count": len(strategies)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching strategies: {str(e)}")
