import asyncio
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import chzzk_record as recorder
from native_backend import NativeRequestError


class ResponseContext:
    def __init__(self, data):
        self.response = Mock()
        self.response.raise_for_status = Mock()
        self.response.json = AsyncMock(return_value=data)

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class NativeRecordingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.channel = {"id": "a" * 32, "name": "Synthetic channel"}
        self.headers = {
            "User-Agent": "Synthetic test",
            "Cookie": "NID_AUT=fake; NID_SES=fake",
        }
        self.cookies = {"NID_AUT": "fake", "NID_SES": "fake"}
        self.logger_patch = unittest.mock.patch.object(recorder, "logger", Mock())
        self.logger_patch.start()
        self.addCleanup(self.logger_patch.stop)

    def make_session(self, data=None):
        session = Mock()
        context = ResponseContext(data or {"content": {"status": "CLOSE"}})
        session.get = Mock(return_value=context)
        return session, context.response

    async def test_native_open_bypasses_http(self):
        data = {
            "content": {
                "status": "OPEN",
                "membershipBenefitType": "NONE",
                "livePlaybackJson": "{}",
            }
        }
        native = Mock(available=True)
        native.live = AsyncMock(return_value=data)
        session, _ = self.make_session()

        result = await recorder.get_live_info(
            self.channel,
            self.headers,
            self.cookies,
            session,
            native=native,
        )

        self.assertEqual(result, ("OPEN", data["content"]))
        native.live.assert_awaited_once_with(self.channel["id"], self.headers)
        session.get.assert_not_called()

    async def test_native_member_only_permission_matches_python_checks(self):
        member_data = {
            "content": {
                "status": "OPEN",
                "membershipBenefitType": "MEMBER_ONLY",
                "livePlaybackJson": None,
            }
        }
        session, _ = self.make_session()
        native = Mock(available=True)
        native.live = AsyncMock(return_value=member_data)

        no_cookies = await recorder.get_live_info(
            self.channel,
            self.headers,
            {},
            session,
            native=native,
        )
        self.assertEqual(no_cookies, ("MEMBER_ONLY_AUTH_REQUIRED", {}))

        valid_cookies = await recorder.get_live_info(
            self.channel,
            self.headers,
            self.cookies,
            session,
            native=native,
        )
        self.assertEqual(valid_cookies, ("MEMBER_ONLY_ACCESS_REQUIRED", {}))
        self.assertEqual(native.live.await_count, 2)
        session.get.assert_not_called()

    async def test_unavailable_native_falls_back_to_http_once(self):
        session, response = self.make_session({"content": {"status": "CLOSE"}})
        native = Mock(available=False)
        native.live = AsyncMock(return_value=None)

        result = await recorder.get_live_info(
            self.channel,
            self.headers,
            self.cookies,
            session,
            native=native,
        )

        self.assertEqual(result, ("CLOSE", {"status": "CLOSE"}))
        native.live.assert_awaited_once_with(self.channel["id"], self.headers)
        session.get.assert_called_once_with(
            recorder.LIVE_DETAIL_API.format(channel_id=self.channel["id"]),
            headers=self.headers,
        )
        response.json.assert_awaited_once_with()

    async def test_native_http_429_returns_empty_without_python_retry_or_disable(self):
        session, _ = self.make_session()
        native = Mock(available=True)
        native.live = AsyncMock(side_effect=NativeRequestError("http", 429))
        secret = "synthetic-cookie-secret"
        headers = {"Cookie": secret}
        cookies = {"NID_AUT": secret, "NID_SES": "synthetic-session"}

        result = await recorder.get_live_info(
            self.channel,
            headers,
            cookies,
            session,
            native=native,
        )

        self.assertEqual(result, ("", {}))
        self.assertTrue(native.available)
        native.live.assert_awaited_once_with(self.channel["id"], headers)
        session.get.assert_not_called()
        self.assertNotIn(secret, repr(recorder.logger.method_calls))

    async def run_manager(self, resolver):
        shutdown = asyncio.Event()
        stream_started = asyncio.Event()
        stream_finished = asyncio.Event()

        class SessionContext:
            async def __aenter__(self):
                return Mock()

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class NativeContext:
            available = True

            def __init__(self):
                self.exited = False

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                if resolver is None:
                    self_outer.assertTrue(stream_finished.is_set())
                self.exited = True
                return False

        self_outer = self
        native = NativeContext()
        channels = [
            {
                "id": self.channel["id"],
                "name": self.channel["name"],
                "identifier": "synthetic",
                "active": "on",
            }
        ]
        settings = (1, 1, channels, {}, {}, {}, "ts", 0, {}, {}, False)

        async def record_stream(*args):
            stream_started.set()
            try:
                await shutdown.wait()
            finally:
                stream_finished.set()

        with ExitStack() as patches:
            patches.enter_context(patch.object(recorder, "shutdown_event", shutdown))
            patches.enter_context(
                patch.object(
                    recorder,
                    "get_session_cookies",
                    AsyncMock(return_value=self.cookies),
                )
            )
            patches.enter_context(
                patch.object(
                    recorder,
                    "setup_paths",
                    AsyncMock(
                        return_value=Path(__file__),
                    ),
                )
            )
            patches.enter_context(
                patch.object(
                    recorder.aiohttp,
                    "ClientSession",
                    return_value=SessionContext(),
                )
            )
            patches.enter_context(
                patch.object(
                    recorder.aiohttp,
                    "TCPConnector",
                    return_value=object(),
                )
            )
            patches.enter_context(
                patch.object(
                    recorder,
                    "load_settings",
                    AsyncMock(return_value=settings),
                )
            )
            patches.enter_context(
                patch.object(recorder, "record_stream", record_stream)
            )
            native_factory = patches.enter_context(
                patch.object(
                    recorder,
                    "NativeLiveClient",
                    Mock(return_value=native),
                )
            )
            manager = asyncio.create_task(
                recorder.manage_recording_tasks(resolver=resolver)
            )
            await asyncio.wait_for(stream_started.wait(), 1)
            shutdown.set()
            await asyncio.wait_for(manager, 1)

        return native_factory, native, stream_finished

    async def test_manager_skips_native_client_when_doh_resolver_is_enabled(self):
        native_factory, native, stream_finished = await self.run_manager(
            resolver=object()
        )

        native_factory.assert_not_called()
        self.assertFalse(native.exited)
        self.assertTrue(stream_finished.is_set())

    async def test_manager_closes_native_client_after_recording_tasks_stop(self):
        native_factory, native, stream_finished = await self.run_manager(resolver=None)

        native_factory.assert_called_once_with()
        self.assertTrue(native.exited)
        self.assertTrue(stream_finished.is_set())

    async def test_built_helper_hello_invalid_channel_and_eof_cleanup(self):
        import native_backend

        executable = native_backend.native_executable()
        if executable is None:
            self.skipTest("native helper binary is not built")

        with patch.object(native_backend, "_HELLO_TIMEOUT", 2):
            client = native_backend.NativeLiveClient(executable)
            async with client:
                self.assertTrue(client.available)
                self.assertIsNone(
                    await asyncio.wait_for(
                        client.live("invalid", {"Cookie": "synthetic"}),
                        0.1,
                    )
                )
                process = client._process
                process.stdin.close()
                await asyncio.wait_for(process.wait(), 2)

                async def unavailable():
                    while client.available:
                        await asyncio.sleep(0)

                await asyncio.wait_for(unavailable(), 0.5)
            self.assertIsNotNone(process.returncode)

    async def test_built_helper_repeated_concurrent_requests_leave_no_pending_state(self):
        import native_backend

        executable = native_backend.native_executable()
        if executable is None:
            self.skipTest("native helper binary is not built")
        async with native_backend.NativeLiveClient(executable) as client:
            self.assertTrue(client.available)
            for _ in range(32):
                replies = await asyncio.wait_for(asyncio.gather(*(
                    client._request("hello") for _ in range(32)
                )), 5)
                self.assertTrue(all(reply["service"] == "chzzk-native" for reply in replies))
                self.assertEqual(client._pending, {})
            self.assertTrue(client.available)
            process = client._process
        self.assertIsNotNone(process.returncode)


if __name__ == "__main__":
    unittest.main()
