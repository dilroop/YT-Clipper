from fastapi import WebSocket

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}  # client_id -> websocket

    async def connect(self, websocket: WebSocket, client_id: str = None):
        await websocket.accept()

        # Generate client ID if not provided
        if not client_id:
            client_id = f"client_{id(websocket)}"

        self.active_connections[client_id] = websocket
        print(f"🔌 WebSocket connected (ID: {client_id}). Total connections: {len(self.active_connections)}")

        # Send client ID back to client
        try:
            await websocket.send_json({"type": "connection", "client_id": client_id})
        except:
            pass

        return client_id

    def disconnect(self, client_id: str = None, websocket: WebSocket = None):
        # Support both disconnect by client_id or by websocket object
        if client_id and client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"🔌 WebSocket disconnected (ID: {client_id}). Total connections: {len(self.active_connections)}")
        elif websocket:
            # Find and remove by websocket object
            for cid, ws in list(self.active_connections.items()):
                if ws == websocket:
                    del self.active_connections[cid]
                    print(f"🔌 WebSocket disconnected (ID: {cid}). Total connections: {len(self.active_connections)}")
                    break

    async def broadcast(self, message: dict, target_client_id: str = None):
        """
        Broadcast message to connections.
        If target_client_id is provided, only send to that client.
        Otherwise, broadcast to all.
        """
        if target_client_id:
            # Targeted send
            if target_client_id in self.active_connections:
                connection = self.active_connections[target_client_id]
                print(f"📡 Sending to client {target_client_id}: {message.get('stage', 'unknown')} - {message.get('message', '')}")
                try:
                    await connection.send_json(message)
                    print(f"✅ Message sent successfully")
                except Exception as e:
                    error_str = str(e)
                    if "close message has been sent" in error_str or not error_str:
                        print(f"⚠️  Connection already closed, removing")
                    else:
                        print(f"❌ Failed to send: {e}")
                    self.disconnect(client_id=target_client_id)
            else:
                print(f"⚠️  Client {target_client_id} not found in active connections")
        else:
            # Broadcast to all
            print(f"📡 Broadcasting to {len(self.active_connections)} connection(s): {message.get('stage', 'unknown')} - {message.get('message', '')}")

            disconnected = []
            for client_id, connection in self.active_connections.items():
                try:
                    await connection.send_json(message)
                    print(f"✅ Message sent successfully to {client_id}")
                except Exception as e:
                    error_str = str(e)
                    if "close message has been sent" in error_str or not error_str:
                        print(f"⚠️  Connection {client_id} already closed, skipping")
                    else:
                        print(f"❌ Failed to send to {client_id}: {e}")
                    disconnected.append(client_id)

            # Remove disconnected connections
            for client_id in disconnected:
                self.disconnect(client_id=client_id)
                print(f"🧹 Cleaned up closed connection {client_id}")

manager = ConnectionManager()
