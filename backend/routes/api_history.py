from fastapi import APIRouter, HTTPException
from backend.database import get_history, clear_history

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
