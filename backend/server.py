"""
YTClipper - FastAPI Server
Mobile-first web app for clipping YouTube videos
"""

import ssl
import certifi

# Disable SSL certificate verification globally (for corporate networks/proxies)
ssl._create_default_https_context = ssl._create_unverified_context

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from pathlib import Path

# Add the project root to sys.path to allow absolute imports from backend.
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import core infrastructure
from backend.core.constants import BASE_DIR
from backend.core.logging_utils import setup_logging
from backend.core.executor import executor
from backend.database import init_database, migrate_database

# Import routers
from backend.routes import (
    pages,
    api_thumbnail,
    api_analyze,
    api_process,
    api_config,
    api_history,
    api_logs,
    api_clips,
    api_upload,
    api_workflow,
    api_workflow2,
    api_workflow2_preview,
    api_workflow3,
    api_generate_metadata,
    api_local_video,
    websocket
)

# Initialize logging (redirects stdout/stderr)
setup_logging()

# Initialize FastAPI app
app = FastAPI(title="YTClipper", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup and migrate if needed
init_database()
migrate_database()

# Mount static files (frontend)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend-react")), name="static")

# Mount ToUpload folder for serving generated clips
app.mount("/clips", StaticFiles(directory=str(BASE_DIR / "ToUpload")), name="clips")

# Mount thumbnails folder for local video previews
from backend.core.constants import THUMBNAILS_DIR
app.mount("/thumbnails", StaticFiles(directory=str(THUMBNAILS_DIR)), name="thumbnails")

# Include all routers
app.include_router(pages.router)
app.include_router(api_thumbnail.router)
app.include_router(api_analyze.router)
app.include_router(api_process.router)
app.include_router(api_config.router)
app.include_router(api_history.router)
app.include_router(api_logs.router)
app.include_router(api_clips.router)
app.include_router(api_upload.router)
app.include_router(api_workflow.router)
app.include_router(api_workflow2.router)
app.include_router(api_workflow2_preview.router)
app.include_router(api_workflow3.router)
app.include_router(api_generate_metadata.router)
app.include_router(api_local_video.router)
app.include_router(websocket.router)

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shutdown thread pool executor"""
    print("🛑 Shutting down thread pool executor...")
    executor.shutdown(wait=True, cancel_futures=False)
    print("✅ Thread pool executor shut down")


if __name__ == "__main__":
    import uvicorn
    import socket

    # Get local IP for display
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "YOUR_LOCAL_IP"

    print("\n" + "="*60)
    print("🎬 YTClipper Server Starting (Modular)...")
    print("="*60)
    print(f"\n📱 Access from your phone (Chrome):")
    print(f"   http://{local_ip}:5000")
    print(f"\n💻 Access from this computer:")
    print(f"   http://localhost:5000")
    print(f"\n⚙️  Server running on all network interfaces (0.0.0.0:5000)")
    print(f"\n📖 Make sure your phone and computer are on the same WiFi!")
    print("="*60 + "\n")

    # Run server on all network interfaces
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info"
    )
