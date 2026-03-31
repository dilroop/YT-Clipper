from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import uuid
import os
from pathlib import Path
from backend.core.constants import TEMP_DIR

router = APIRouter()

@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Handle media uploads (e.g. custom AI content for stacked reels).
    Saves the file to TEMP_DIR and returns its absolute path.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    # Ensure TEMP_DIR exists
    os.makedirs(TEMP_DIR, exist_ok=True)

    # Generate a unique path in TEMP_DIR
    ext = Path(file.filename).suffix if file.filename else ""
    file_id = str(uuid.uuid4())
    temp_path = TEMP_DIR / f"upload_{file_id}{ext}"

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    finally:
        file.file.close()

    return {"path": str(temp_path.absolute())}
