import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional

import websockets
from websockets.server import WebSocketServerProtocol


logging.basicConfig(level=logging.INFO)

B_TOKENS = {
    token.strip()
    for token in os.getenv("B_TOKENS", "demo-token").split(",")
    if token.strip()
}


class Hub:
    def __init__(self) -> None:
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        self.b_token: Optional[str] = None

    async def register(self, role: str, websocket: WebSocketServerProtocol, token: str | None) -> None:
        if role == "b":
            if token is None or token not in B_TOKENS:
                raise ValueError("invalid token")
            self.b_token = token
        self.connections[role] = websocket
        await self.send(websocket, {"type": "registered", "role": role})
        if role == "b":
            await self.notify_c({"type": "b_connected", "token": token})

    async def unregister(self, role: str) -> None:
        if role in self.connections:
            del self.connections[role]
        if role == "b":
            await self.notify_c({"type": "b_disconnected", "token": self.b_token})
            self.b_token = None

    async def send(self, websocket: WebSocketServerProtocol, message: Dict[str, Any]) -> None:
        await websocket.send(json.dumps(message, ensure_ascii=False))

    async def notify_c(self, message: Dict[str, Any]) -> None:
        c_socket = self.connections.get("c")
        if c_socket:
            await self.send(c_socket, message)

    async def forward(self, target: str, message: Dict[str, Any]) -> None:
        target_socket = self.connections.get(target)
        if target_socket:
            await self.send(target_socket, message)


hub = Hub()


def parse_json(raw: str) -> Dict[str, Any]:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("payload must be a json object")
    return data


async def handle_messages(role: str, websocket: WebSocketServerProtocol) -> None:
    async for raw in websocket:
        data = parse_json(raw)
        msg_type = data.get("type")
        if msg_type == "command" and role == "b":
            await hub.notify_c({"type": "command", "command": data.get("command")})
            continue
        if msg_type == "message":
            target = data.get("to")
            payload = data.get("payload")
            if target not in {"a", "b"}:
                await hub.send(websocket, {"type": "error", "error": "invalid target"})
                continue
            await hub.forward(
                target,
                {"type": "message", "from": role, "payload": payload},
            )
            continue
        await hub.send(websocket, {"type": "error", "error": "unsupported message"})


async def handler(websocket: WebSocketServerProtocol) -> None:
    role = ""
    try:
        raw = await websocket.recv()
        data = parse_json(raw)
        if data.get("type") != "register":
            await hub.send(websocket, {"type": "error", "error": "first message must register"})
            return
        role = data.get("role")
        if role not in {"a", "b", "c"}:
            await hub.send(websocket, {"type": "error", "error": "invalid role"})
            return
        await hub.register(role, websocket, data.get("token"))
        await handle_messages(role, websocket)
    except (ValueError, json.JSONDecodeError) as exc:
        logging.warning("bad payload: %s", exc)
        await hub.send(websocket, {"type": "error", "error": str(exc)})
    except websockets.ConnectionClosed:
        logging.info("connection closed")
    finally:
        if role:
            await hub.unregister(role)


async def main() -> None:
    host = os.getenv("WS_HOST", "0.0.0.0")
    port = int(os.getenv("WS_PORT", "8765"))
    async with websockets.serve(handler, host, port):
        logging.info("ws server listening on %s:%s", host, port)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
