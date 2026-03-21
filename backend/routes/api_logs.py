import asyncio
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from core.constants import BASE_DIR
from core.logging_utils import LOG_FILE

router = APIRouter()

@router.get("/api/logs")
async def get_logs(lines: int = 500):
    """Get the last N lines from the log file"""
    try:
        # Ensure logs directory exists
        LOG_FILE.parent.mkdir(exist_ok=True)

        if not LOG_FILE.exists():
            return {"success": True, "logs": [], "count": 0}

        # Read the last N lines efficiently
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            # Read all lines
            all_lines = f.readlines()
            # Get last N lines
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        return {
            "success": True,
            "logs": last_lines,
            "count": len(last_lines),
            "total_lines": len(all_lines)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")

@router.delete("/api/logs")
async def clear_logs():
    """Clear/truncate the log file"""
    try:
        # Ensure logs directory exists
        LOG_FILE.parent.mkdir(exist_ok=True)

        if LOG_FILE.exists():
            # Truncate the file to 0 bytes
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.write('')  # Clear the file

            print("Log file cleared successfully")
            return {
                "success": True,
                "message": "Log file cleared successfully"
            }
        else:
            # File doesn't exist, create empty file
            LOG_FILE.touch()
            print("Log file did not exist, created empty file")
            return {
                "success": True,
                "message": "Log file cleared successfully"
            }
    except Exception as e:
        print(f"Error clearing log file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing log file: {str(e)}"
        )

@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket for live log streaming"""
    await websocket.accept()
    client_id = f"logs_{id(websocket)}"
    print(f"🔌 WebSocket connected from logs panel (ID: {client_id})")

    try:
        # Send initial log content (last 500 lines)
        if LOG_FILE.exists():
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                last_lines = all_lines[-500:] if len(all_lines) > 500 else all_lines
                for line in last_lines:
                    await websocket.send_json({"type": "history", "line": line.rstrip()})
        
        # Track the last position in the file
        last_position = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0

        # Stream new log lines as they appear
        while True:
            await asyncio.sleep(1.5)

            if not LOG_FILE.exists():
                continue

            current_size = LOG_FILE.stat().st_size

            if current_size > last_position:
                # File has grown, read new content
                try:
                    with open(LOG_FILE, 'r', encoding='utf-8') as f:
                        f.seek(last_position)
                        new_lines = f.readlines()

                        for line in new_lines:
                            await websocket.send_json({"type": "new", "line": line.rstrip()})

                    last_position = current_size
                except Exception as e:
                    error_str = str(e)
                    if "close message has been sent" in error_str or "closed" in error_str.lower():
                        break
                    print(f"⚠️ Error reading log file for {client_id}: {e}")
    except WebSocketDisconnect:
        print(f"🔌 Log viewer disconnected ({client_id})")
    except Exception as e:
        print(f"❌ Error in log stream ({client_id}): {e}")
