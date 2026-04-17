from fastapi import APIRouter, HTTPException
from backend.database import get_history, clear_history, delete_history_entry

router = APIRouter()

@router.get("/api/history")
async def get_history_endpoint(limit: int = 50):
    """Get video history"""
    try:
        history = get_history(limit)
        return {"success": True, "history": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")

@router.delete("/api/history")
async def clear_history_endpoint():
    """Clear all history"""
    try:
        clear_history()
        return {"success": True, "message": "History cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")

@router.delete("/api/history/{video_id}")
async def delete_history_entry_endpoint(video_id: str):
    """Delete a single history entry by video_id"""
    try:
        success = delete_history_entry(video_id)
        if success:
            return {"success": True, "message": "History entry deleted"}
        else:
            raise HTTPException(status_code=404, detail="History entry not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting history entry: {str(e)}")
