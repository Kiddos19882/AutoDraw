import asyncio
import json
import unittest

try:
    import websockets
    from websocket_smoke_server import OneShotAuthenticator, make_handler, parse_message
    from game_monitor_bridge_server import RunRecorder, exact_snapshot, summarize_intervals, valid_origin, make_handler as bridge_make_handler
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
        self.recorder.frame_probe({"startedAtPerformanceMs": 10, "endedAtPerformanceMs": 30,
                                   "visible": True, "intervals": [16.67, 16.67, 16.67]})
        path = self.recorder.finalize("completed")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["chalk"]["status"], "exact")
        self.assertEqual(data["chalk"]["consumed_points"], 52)
        self.assertEqual(data["frame_probe"]["stroke_probe_count"], 1)
        self.assertEqual(data["active_drawing_duration_ms"], 20)

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


    def test_missing_draw_end_is_saved_as_partial_after_idle(self):
        before = {"maxPoints": 6000, "remainingPoints": 6000, "pointCount": 0, "isExact": True}
        self.recorder.event({"type": "DRAW_START", "t": 1, "before": before}, 1.0)
        self.recorder.heartbeat({"droppedEvents": 0, "errors": 0}, 4.0)
        self.assertIsNone(self.recorder.current)
        files = list(self.output.glob("game-monitor-run-*.json"))
        self.assertEqual(len(files), 1)
        data = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertEqual(data["execution_status"], "partial")


@unittest.skipIf(websockets is None, "install game_monitor/requirements-smoke.txt to run transport tests")
class ProductionBridgeIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_authenticated_browser_stream_is_saved_as_run_json(self):
        import tempfile
        import uuid
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            session_id = str(uuid.uuid4())
            token = "local-test-token"
            server = await websockets.serve(
                bridge_make_handler(token, "https://game.example", output, 0.5),
                "127.0.0.1", 0,
                origins=["https://game.example"],
                max_size=65536,
            )
            port = server.sockets[0].getsockname()[1]
            try:
                async with websockets.connect(
                    f"ws://127.0.0.1:{port}", origin="https://game.example"
                ) as ws:
                    await ws.send(json.dumps({"type": "auth", "token": token}))
                    self.assertEqual(json.loads(await ws.recv()), {"type": "ready"})
                    await ws.send(json.dumps({
                        "type": "session_start", "sessionId": session_id, "sequence": 1,
                        "monitorStatus": {"active": True, "boardDetected": True},
                        "browser": "unit-test", "page": {"origin": "https://game.example"},
                    }))
                    before = {"maxPoints": 6000, "remainingPoints": 6000,
                              "pointCount": 0, "isExact": True}
                    after = {"maxPoints": 6000, "remainingPoints": 5998,
                             "pointCount": 2, "isExact": True}
                    await ws.send(json.dumps({
                        "type": "event", "sessionId": session_id, "sequence": 2,
                        "event": {"type": "DRAW_START", "t": 10, "before": before},
                    }))
                    await ws.send(json.dumps({
                        "type": "event", "sessionId": session_id, "sequence": 3,
                        "event": {"type": "DRAW_END", "t": 20, "after": after},
                    }))
                    await asyncio.sleep(0.6)
                    await ws.send(json.dumps({
                        "type": "heartbeat", "sessionId": session_id, "sequence": 4,
                        "monitorStatus": {"active": True, "droppedEvents": 0, "errors": 0},
                    }))
                    await asyncio.sleep(0.05)
                run_files = list((output / session_id).glob("game-monitor-run-*.json"))
                self.assertEqual(len(run_files), 1)
                report = json.loads(run_files[0].read_text(encoding="utf-8"))
                self.assertEqual(report["chalk"]["consumed_points"], 2)
                self.assertEqual(report["execution_status"], "completed")
            finally:
                server.close()
                await server.wait_closed()


if __name__ == "__main__":
    unittest.main()
