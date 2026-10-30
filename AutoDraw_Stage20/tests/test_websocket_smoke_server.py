import asyncio
import json
import unittest

import websockets

from websocket_smoke_server import OneShotAuthenticator, make_handler, parse_message


class SmokeServerUnitTests(unittest.TestCase):
    def test_token_is_one_shot(self):
        auth = OneShotAuthenticator("secret")
        self.assertTrue(auth.verify("secret"))
        self.assertFalse(auth.verify("secret"))
        self.assertFalse(auth.verify("wrong"))

    def test_message_parser_rejects_invalid_shapes(self):
        self.assertEqual(parse_message('{"type":"ping"}'), {"type": "ping"})
        self.assertIsNone(parse_message("not-json"))
        self.assertIsNone(parse_message("[]"))
        self.assertIsNone(parse_message('"' + ("x" * 1100) + '"'))


class SmokeServerIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_authorized_ping_pong_and_origin_filter(self):
        auth = OneShotAuthenticator("one-time")
        server = await websockets.serve(
            make_handler(auth), "127.0.0.1", 0,
            origins=["https://game.example"],
            max_size=1024,
        )
        port = server.sockets[0].getsockname()[1]
        try:
            with self.assertRaises(websockets.InvalidStatusCode):
                async with websockets.connect(
                    f"ws://127.0.0.1:{port}",
                    origin="https://wrong.example",
                ):
                    pass

            async with websockets.connect(
                f"ws://127.0.0.1:{port}",
                origin="https://game.example",
            ) as ws:
                await ws.send(json.dumps({"type": "auth", "token": "wrong-token"}))
                with self.assertRaises(websockets.ConnectionClosedError) as rejected:
                    await ws.recv()
                self.assertEqual(rejected.exception.code, 4003)

            async with websockets.connect(
                f"ws://127.0.0.1:{port}",
                origin="https://game.example",
            ) as ws:
                await ws.send(json.dumps({"type": "auth", "token": "one-time"}))
                self.assertEqual(json.loads(await ws.recv()), {"type": "ready"})
                await ws.send(json.dumps({"type": "ping", "nonce": "test-123"}))
                self.assertEqual(
                    json.loads(await ws.recv()),
                    {"type": "pong", "nonce": "test-123"},
                )
        finally:
            server.close()
            await server.wait_closed()


if __name__ == "__main__":
    unittest.main()
