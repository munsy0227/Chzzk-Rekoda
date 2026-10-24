"""DoH integration and bounded HTTP responses, using only local fixtures."""

import asyncio
import socket
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import aiohttp

import chzzk_record as recorder
import dns_over_https as dns


class Socket:
    def __init__(self, data):
        self.data = data
        self.received = 0

    def recv(self, size):
        chunk, self.data = self.data[:size], self.data[size:]
        self.received += len(chunk)
        return chunk


class DnsResponseTests(unittest.TestCase):
    def response(self, framing, body):
        if framing == "length":
            headers = f"Content-Length: {len(body)}\r\n".encode()
        elif framing == "chunked":
            headers = b"Transfer-Encoding: chunked\r\n"
            body = f"{len(body):x}\r\n".encode() + body + b"\r\n0\r\n\r\n"
        else:
            headers = b""
        return Socket(b"HTTP/1.1 200 OK\r\n" + headers + b"\r\n" + body)

    def test_valid_response_at_limit_for_all_framings(self):
        body = b"x" * dns.MAX_DNS_MESSAGE_BYTES
        for framing in ("length", "chunked", "close"):
            with self.subTest(framing=framing):
                _, _, received = dns.DnsOverHttpsResolver._read_http_response(
                    self.response(framing, body)
                )
                self.assertEqual(received, body)

    def test_oversized_response_stops_during_receive(self):
        for framing in ("length", "chunked", "close"):
            with self.subTest(framing=framing):
                sock = self.response(framing, b"x" * (2 * dns.MAX_DNS_MESSAGE_BYTES))
                with self.assertRaises(OSError):
                    dns.DnsOverHttpsResolver._read_http_response(sock)
                maximum = 4096 if framing != "close" else dns.MAX_DNS_MESSAGE_BYTES + 128
                self.assertLessEqual(sock.received, maximum)

    def test_chunked_limit_counts_previous_chunks(self):
        body = b"x" * dns.MAX_DNS_MESSAGE_BYTES
        sock = Socket(f"{len(body):x}\r\n".encode() + body + b"\r\n1\r\nx\r\n0\r\n\r\n")
        with self.assertRaises(OSError):
            dns._read_chunked_body(sock, b"")

    def test_invalid_lengths_and_unbounded_chunk_headers_are_rejected(self):
        with self.assertRaises(OSError):
            dns._read_content_length_body(Socket(b""), b"", -1)
        with self.assertRaises(OSError):
            dns._read_chunked_body(Socket(b"-1\r\n"), b"")
        with self.assertRaises(OSError):
            dns._read_chunked_body(Socket(b"f" * (dns.MAX_DNS_MESSAGE_BYTES + 4096)), b"")


class DnsIntegrationTests(unittest.TestCase):
    def test_socket_patch_accepts_standard_keywords_and_preserves_fallback(self):
        rows = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
        with (
            patch.object(socket, "getaddrinfo"),
            patch.object(dns, "_INSTALLED", False),
            patch.object(dns, "_ORIGINAL_GETADDRINFO", return_value=rows) as original,
            patch.object(
                dns.DnsOverHttpsResolver, "resolve", return_value=["127.0.0.1"]
            ) as resolve,
        ):
            dns.install_doh_dns()
            self.assertEqual(socket.getaddrinfo(
                host="rekoda-audit.invalid", port=443, type=socket.SOCK_STREAM,
            ), rows)
            resolve.side_effect = socket.gaierror(socket.EAI_AGAIN, "fixture")
            self.assertEqual(socket.getaddrinfo(
                host="rekoda-audit.invalid", port=443, type=socket.SOCK_STREAM,
            ), rows)
            original.assert_called_with(
                "rekoda-audit.invalid", 443, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, 0,
            )

    def test_aiohttp_uses_doh_with_default_loop_and_uvloop(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"fixture")

            def log_message(self, *_):
                pass

        factories = [asyncio.new_event_loop]
        if sys.platform != "win32":
            import uvloop

            factories.append(uvloop.new_event_loop)
        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for factory in factories:
                    with (
                        self.subTest(loop=factory.__module__),
                        patch.object(socket, "getaddrinfo", socket.getaddrinfo),
                        patch.object(dns, "_INSTALLED", False),
                        patch.object(
                            dns.DnsOverHttpsResolver, "resolve", return_value=["127.0.0.1"]
                        ) as resolve,
                        patch.object(recorder, "get_dns_settings_sync", return_value={
                            "enable": True, "doh_url": dns.DEFAULT_DOH_URL,
                        }),
                    ):
                        resolver = recorder.install_internal_dns_resolver()

                        async def request():
                            connector = aiohttp.TCPConnector(resolver=resolver)
                            async with aiohttp.ClientSession(connector=connector) as session:
                                url = f"http://rekoda-audit.invalid:{server.server_port}/"
                                async with session.get(url) as response:
                                    self.assertEqual(await response.read(), b"fixture")
                            await resolver.close()

                        with asyncio.Runner(loop_factory=factory) as runner:
                            runner.run(request())
                        resolve.assert_called_with("rekoda-audit.invalid", socket.AF_UNSPEC)
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    unittest.main()
