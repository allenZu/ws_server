import argparse
import asyncio
import json
import os

import websockets


async def run_client() -> None:
    parser = argparse.ArgumentParser(description="B 端 WebSocket 客户端")
    parser.add_argument("--url", default=os.getenv("WS_URL", "ws://127.0.0.1:8765"))
    parser.add_argument("--token", default=os.getenv("B_TOKEN", "demo-token"))
    parser.add_argument("--command", default="")
    parser.add_argument("--message", default="")
    args = parser.parse_args()

    async with websockets.connect(args.url) as websocket:
        await websocket.send(
            json.dumps({"type": "register", "role": "b", "token": args.token})
        )
        print("registered as b")

        if args.command:
            await websocket.send(json.dumps({"type": "command", "command": args.command}))
            print(f"command sent: {args.command}")

        if args.message:
            await websocket.send(
                json.dumps({"type": "message", "to": "a", "payload": args.message})
            )
            print(f"message sent to a: {args.message}")

        async for raw in websocket:
            print(raw)


if __name__ == "__main__":
    asyncio.run(run_client())
