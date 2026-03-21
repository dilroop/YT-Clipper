from fastapi import APIRouter
from fastapi.responses import FileResponse
from core.constants import BASE_DIR

router = APIRouter()

@router.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse(str(BASE_DIR / "frontend" / "pages" / "home" / "index.html"))

@router.get("/gallery.html")
async def gallery():
    """Serve the gallery HTML page"""
    return FileResponse(str(BASE_DIR / "frontend" / "pages" / "gallery" / "index.html"))

@router.get("/clip-detail.html")
async def clip_detail():
    """Serve the clip detail HTML page"""
    return FileResponse(str(BASE_DIR / "frontend" / "pages" / "clip-detail" / "index.html"))

@router.get("/logs.html")
async def logs():
    """Serve the logs HTML page"""
    return FileResponse(str(BASE_DIR / "frontend" / "pages" / "logs" / "index.html"))
