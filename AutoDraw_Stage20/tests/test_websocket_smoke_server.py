import asyncio
import json
import unittest

try:
    import websockets
    from websocket_smoke_server import OneShotAuthenticator, make_handler, parse_message
    from game_monitor_bridge_server import RunRecorder, exact_snapshot, summarize_intervals, valid_origin
except ModuleNotFoundError:
    websockets = None




@unittest.skipIf(websockets is None, "install game_monitor/requirements-smoke.txt to run transport tests")
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


@unittest.skipIf(websockets is None, "install game_monitor/requirements-smoke.txt to run transport tests")
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


@unittest.skipIf(websockets is None, "install game_monitor/requirements-smoke.txt to run transport tests")
class BridgeRecorderTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        self.recorder = RunRecorder(self.output, "session-test", 2.5)

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_chalk_delta_and_run_export(self):
        before = {"maxPoints": 6000, "remainingPoints": 5999, "pointCount": 1, "isExact": True}
        after = {"maxPoints": 6000, "remainingPoints": 5947, "pointCount": 53, "isExact": True}
        self.recorder.event({"type": "DRAW_START", "t": 10, "before": before}, 1.0)
        self.recorder.event({"type": "DRAW_SAMPLE", "t": 20, "strokeId": "s1",
                             "pointDelta": 1, "acceptedPoint": {"x": 10, "y": 10}}, 1.1)
        self.recorder.event({"type": "DRAW_END", "t": 30, "strokeId": "s1",
                             "after": after}, 1.2)
        path = self.recorder.finalize("completed")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["chalk"]["status"], "exact")
        self.assertEqual(data["chalk"]["consumed_points"], 52)

    def test_coalesced_samples_mark_path_as_incomplete(self):
        before = {"maxPoints": 6000, "remainingPoints": 6000, "pointCount": 0, "isExact": True}
        self.recorder.event({"type": "DRAW_START", "t": 1, "before": before}, 1.0)
        self.recorder.event({"type": "DRAW_SAMPLE", "t": 2, "strokeId": "s1",
                             "pointDelta": 3, "acceptedPoint": {"x": 3, "y": 4}}, 1.1)
        self.assertEqual(self.recorder.current["interpretation"]["path_length_status"], "incomplete_samples")

    def test_idle_finalizes_completed_run(self):
        before = {"maxPoints": 6000, "remainingPoints": 6000, "pointCount": 0, "isExact": True}
        self.recorder.event({"type": "DRAW_START", "t": 1, "before": before}, 1.0)
        self.recorder.event({"type": "DRAW_END", "t": 2, "after": before}, 1.1)
        self.recorder.heartbeat({}, 4.0)
        self.assertIsNone(self.recorder.current)

    def test_snapshot_validation_and_frame_summary(self):
        self.assertTrue(exact_snapshot({"maxPoints": 10, "remainingPoints": 8, "pointCount": 2, "isExact": True}))
        self.assertFalse(exact_snapshot({"maxPoints": 10, "remainingPoints": 8, "pointCount": 3, "isExact": True}))
        self.assertAlmostEqual(summarize_intervals([16.67] * 60)["median_fps"], 59.988, places=2)

    def test_origin_validation(self):
        self.assertTrue(valid_origin("https://game.example"))
        self.assertFalse(valid_origin("http://game.example"))
        self.assertFalse(valid_origin("https://game.example/path"))
