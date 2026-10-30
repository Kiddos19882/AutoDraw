"""Local, one-shot WebSocket transport smoke server for Firefox.

This is a transport test only. It does not connect to or control the game.
Requires: pip install -r requirements-smoke.txt
"""
from __future__ import annotations

import argparse
import asyncio
import hmac
import json
import secrets
import sys
from dataclasses import dataclass
from urllib.parse import urlsplit

import websockets
from websockets.exceptions import ConnectionClosed


MAX_MESSAGE_BYTES = 1024
MAX_NONCE_LENGTH = 64
HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def parse_message(raw: str) -> dict | None:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_MESSAGE_BYTES:
        return None
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def is_valid_origin(origin: str) -> bool:
    try:
        parsed = urlsplit(origin)
        return (
            parsed.scheme == "https"
            and bool(parsed.netloc)
            and parsed.username is None
            and parsed.password is None
            and parsed.path in ("", "/")
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        return False


@dataclass
class OneShotAuthenticator:
    token: str
    consumed: bool = False

    def verify(self, candidate: object) -> bool:
        if self.consumed or not isinstance(candidate, str):
            return False
        valid = hmac.compare_digest(self.token, candidate)
        if valid:
            self.consumed = True
        return valid


def make_handler(authenticator: OneShotAuthenticator):
    async def handler(websocket):
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=5)
            message = parse_message(raw)
            if not message or set(message) != {"type", "token"} or message["type"] != "auth":
                await websocket.close(code=4001, reason="invalid auth message")
                return
            if not authenticator.verify(message["token"]):
                await websocket.close(code=4003, reason="authentication failed")
                return

            await websocket.send(json.dumps({"type": "ready"}, separators=(",", ":")))
            raw = await asyncio.wait_for(websocket.recv(), timeout=5)
            message = parse_message(raw)
            if (
                not message
                or set(message) != {"type", "nonce"}
                or message["type"] != "ping"
                or not isinstance(message["nonce"], str)
                or not 1 <= len(message["nonce"]) <= MAX_NONCE_LENGTH
            ):
                await websocket.close(code=4002, reason="invalid smoke-test message")
                return

            await websocket.send(json.dumps(
                {"type": "pong", "nonce": message["nonce"]},
                separators=(",", ":"),
            ))
            await websocket.close(code=1000, reason="smoke test complete")
        except (asyncio.TimeoutError, ConnectionClosed):
            return

    return handler


async def run_server(origin: str, port: int) -> None:
    token = secrets.token_urlsafe(32)
    authenticator = OneShotAuthenticator(token)
    print("AutoDraw local WebSocket transport smoke test")
    print(f"Listening only on ws://{HOST}:{port}")
    print(f"Allowed Origin: {origin}")
    print("One-time token (paste into the iframe console; do not share):")
    print(token)
    print("Waiting for one browser connection. Press Ctrl+C to stop.")
    async with websockets.serve(
        make_handler(authenticator),
        HOST,
        port,
        origins=[origin],
        max_size=MAX_MESSAGE_BYTES,
        max_queue=1,
        ping_interval=20,
        ping_timeout=10,
        close_timeout=3,
    ):
        await asyncio.Future()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True, help="Exact HTTPS origin of the game iframe, without a path")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    if not is_valid_origin(args.origin):
        parser.error("--origin must be an exact HTTPS origin without a path, query, or fragment")
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    try:
        asyncio.run(run_server(args.origin.rstrip("/"), args.port))
    except KeyboardInterrupt:
        print("\nSmoke server stopped.")
    except OSError as exc:
        print(f"Could not start local server: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
