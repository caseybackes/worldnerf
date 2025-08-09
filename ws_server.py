import asyncio
import json
import websockets
from handlers import handlers
import json 
import os 

async def handler(websocket):
    async for message in websocket:
        print(f"[WS] Received: {message}")
        try:
            data = json.loads(message)
            action = data.get("action")
            params = data.get("params", {})

            if action in handlers:
                await handlers[action](websocket, **params)
            else:
                await websocket.send(f"Unknown action: {action}")
        except json.JSONDecodeError:
            await websocket.send("Invalid JSON")

async def main():
    host = os.environ.get("WS_BIND_HOST", "0.0.0.0")
    port = int(os.environ.get("WS_PORT", 9001))

    async with websockets.serve(handler, host, port):
        print(f"[WS] Server listening on ws://{host}:{port}")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
