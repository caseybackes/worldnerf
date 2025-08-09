import asyncio

async def handle_ping(websocket, params):
    await websocket.send("pong")

async def handle_stop(websocket, params):
    await websocket.send("stopping")

async def handle_pose(websocket, params):
    pose = params.get("pose", {})
    await websocket.send(f"handling pose: {pose}")
