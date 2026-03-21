import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.connection_manager import manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time progress updates"""
    print("🎯 WebSocket connection request received")
    client_id = await manager.connect(websocket)
    print(f"✅ WebSocket connection established (ID: {client_id})")

    try:
        # Keep connection alive - ping/pong to prevent timeout
        ping_count = 0
        while True:
            try:
                ping_count += 1
                await websocket.send_json({"type": "ping"})
                print(f"💓 Heartbeat ping #{ping_count} sent to {client_id}")
                await asyncio.sleep(10)
            except Exception as e:
                # Connection closed by client or network error
                print(f"❌ WebSocket send error for {client_id} (breaking loop): {e}")
                break
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected by client ({client_id})")
    except Exception as e:
        print(f"❌ WebSocket error ({client_id}): {e}")
    finally:
        # Always clean up the connection
        manager.disconnect(client_id=client_id)
        print(f"🔚 WebSocket connection closed ({client_id})")
