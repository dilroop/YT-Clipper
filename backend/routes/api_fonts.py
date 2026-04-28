from fastapi import APIRouter
from backend.core.constants import FONTS_DIR
import os

router = APIRouter()

@router.get("/api/fonts")
async def list_fonts():
    """List all available .ttf and .ttc fonts in the fonts/ directory."""
    fonts = []
    if FONTS_DIR.exists():
        for file in os.listdir(FONTS_DIR):
            if file.lower().endswith(('.ttf', '.ttc')):
                # Use filename without extension as the font name for the UI
                name = os.path.splitext(file)[0]
                fonts.append({
                    "name": name,
                    "filename": file
                })
    
    # Also include some common system fonts as fallbacks
    system_fonts = ["Arial", "Helvetica", "Impact", "Times New Roman"]
    for sf in system_fonts:
        if not any(f["name"] == sf for f in fonts):
            fonts.append({"name": sf, "filename": None})
            
    return sorted(fonts, key=lambda x: x["name"])
