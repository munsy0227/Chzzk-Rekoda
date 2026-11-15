import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import native_backend

CHANNEL_A = "a" * 32
CHANNEL_B = "b" * 32


class NativeBackendTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def helper(self, source):
        path = self.root / "helper.py"
        path.write_text(source, encoding="utf-8")
        original = asyncio.create_subprocess_exec

        async def launch(executable, *args, **kwargs):
            return await original(sys.executable, str(path), *args, **kwargs)

        self.launch_patch = patch.object(native_backend.asyncio, "create_subprocess_exec", launch)
        self.launch_patch.start()
        self.addCleanup(self.launch_patch.stop)
        return path

    @staticmethod
    def helper_source(mode="normal"):
        return f'''import json, os, sys, threading, time
mode = {mode!r}
lock = threading.Lock()
cancelled = set()
def send(row):
    with lock:
        print(json.dumps(row), flush=True)
def work(row):
    if row["op"] == "live":
        time.sleep(0.15 if row["channel_id"].startswith("a") else 0.01)
        if row["id"] not in cancelled:
            send({{"version": 1, "id": row["id"], "ok": True,
                  "data": {{"channel": row["channel_id"],
                           "cookie": row["headers"].get("Cookie", ""),
                           "argv": sys.argv,
                           "env_has_cookie": "private-cookie-value" in os.environ.values()}}}})
    elif row["op"] == "cancel":
        cancelled.add(row["id"])
        if mode != "no-cancel-ack":
            send({{"version": 1, "id": row["id"], "ok": True}})
for line in sys.stdin:
    row = json.loads(line)
    if row["op"] == "hello":
        if mode == "eof": break
        version = 2 if mode == "wrong-version" else 1
        send({{"version": version, "id": row["id"], "ok": True,
              "service": "chzzk-native"}})
    elif mode == "timeout":
        time.sleep(100)
    else:
        threading.Thread(target=work, args=(row,), daemon=True).start()
'''

    async def test_missing_executable_is_unavailable(self):
        async with native_backend.NativeLiveClient(self.root / "missing") as client:
            self.assertFalse(client.available)
            self.assertIsNone(await client.live(CHANNEL_A, {}))

    async def test_wrong_version_and_eof_disable_helper(self):
        for mode in ("wrong-version", "eof"):
            with self.subTest(mode=mode):
                self.helper(self.helper_source(mode))
                async with native_backend.NativeLiveClient(self.root / "unused") as client:
                    self.assertFalse(client.available)
                    self.assertIsNone(await client.live(CHANNEL_A, {}))

    async def test_concurrent_mapping_cancel_and_headers_stay_on_stdin(self):
        self.helper(self.helper_source())
        secret = "private-cookie-value"
        async with native_backend.NativeLiveClient(self.root / "unused") as client:
            self.assertTrue(client.available)
            slow = asyncio.create_task(client.live(CHANNEL_A, {"Cookie": secret}))
            fast = asyncio.create_task(client.live(CHANNEL_B, {"Cookie": "other"}))
            fast_result = await fast
            self.assertEqual(fast_result["channel"], CHANNEL_B)
            self.assertEqual(fast_result["cookie"], "other")
            self.assertNotIn(secret, " ".join(fast_result["argv"]))
            self.assertFalse(fast_result["env_has_cookie"])
            slow.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await slow
            self.assertEqual((await client.live(CHANNEL_B, {}))["channel"], CHANNEL_B)
        self.assertIsNotNone(client._process.returncode)

    async def test_http_failure_is_forwarded_without_disabling_client(self):
        self.helper('''import json, sys
for line in sys.stdin:
 row = json.loads(line)
 if row["op"] == "hello": print(json.dumps({"version":1,"id":row["id"],"ok":True,"service":"chzzk-native"}),flush=True)
 elif row["op"] == "live": print(json.dumps({"version":1,"id":row["id"],"ok":False,"error":"http","status":429}),flush=True)
''')
        async with native_backend.NativeLiveClient(self.root / "unused") as client:
            with self.assertRaises(native_backend.NativeRequestError) as caught:
                await client.live(CHANNEL_A, {"Cookie": "secret"})
            self.assertEqual((caught.exception.category, caught.exception.status), ("http", 429))
            self.assertTrue(client.available)

    async def test_timeout_disables_and_close_terminates(self):
        self.helper(self.helper_source("timeout"))
        with patch.object(native_backend, "_TIMEOUT", 0.05):
            async with native_backend.NativeLiveClient(self.root / "unused") as client:
                self.assertTrue(client.available)
                self.assertIsNone(await client.live(CHANNEL_A, {}))
                self.assertFalse(client.available)
                self.assertIsNotNone(client._process.returncode)

    async def test_redirect_disables_helper_for_existing_python_handling(self):
        self.helper('''import json, sys
for line in sys.stdin:
 row = json.loads(line)
 reply = {"version":1,"id":row["id"],"ok":row["op"] == "hello"}
 if row["op"] == "hello": reply["service"] = "chzzk-native"
 else: reply.update(error="http", status=302)
 print(json.dumps(reply),flush=True)
''')
        async with native_backend.NativeLiveClient(self.root / "unused") as client:
            self.assertIsNone(await client.live(CHANNEL_A, {"Cookie": "dummy"}))
            self.assertFalse(client.available)
            self.assertIsNotNone(client._process.returncode)

    async def test_repeated_cancellation_needs_no_ack_and_does_not_disable(self):
        self.helper(self.helper_source("no-cancel-ack"))
        async with native_backend.NativeLiveClient(self.root / "unused") as client:
            for _ in range(70):
                task = asyncio.create_task(client.live(CHANNEL_A, {}))
                await asyncio.sleep(0)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            self.assertTrue(client.available)


class NativeReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.report = self.root / "large.ndjson"
        self.report.write_bytes(b" " * (256 * 1024))
        self.summary = {
            "version": 1, "passed": True, "gap_count": 0, "gap_seconds": 0,
            "unresolved_count": 0, "checkpoint_count": 1, "duplicate_count": 0,
            "error_count": 0, "gaps": [],
        }

    def call_with(self, output):
        binary = self.root / "fake-native"
        binary.touch()
        with patch.object(native_backend, "native_executable", return_value=binary), \
                patch.object(native_backend.subprocess, "Popen") as popen:
            process = popen.return_value
            process.wait.return_value = 0
            process.returncode = 0

            def write_stdout(*args, **kwargs):
                kwargs["stdout"].write(output)
                kwargs["stdout"].flush()
                kwargs["stdout"].seek(0, os.SEEK_END)
                return process

            popen.side_effect = write_stdout
            return native_backend.native_report_summary(self.report)

    def test_valid_envelope_and_unsupported_fall_back(self):
        payload = json.dumps({"version": 1, "ok": True, "summary": self.summary}).encode()
        self.assertEqual(self.call_with(payload), self.summary)
        self.assertIsNone(self.call_with(b'{"version":1,"ok":false,"error":"unsupported"}'))

    def test_rejects_stale_or_inconsistent_summary(self):
        invalid = dict(self.summary, passed=False)
        payload = json.dumps({"version": 1, "ok": True, "summary": invalid}).encode()
        self.assertIsNone(self.call_with(payload))

    def test_skips_small_files(self):
        self.report.write_bytes(b"x")
        with patch.object(native_backend, "native_executable", return_value=self.root / "bin"):
            self.assertIsNone(native_backend.native_report_summary(self.report))


if __name__ == "__main__":
    unittest.main()
