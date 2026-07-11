from __future__ import annotations

import ipaddress
import os
import socket
import ssl
import threading
import time
from typing import Iterable
from urllib.parse import urlparse

import dns.exception
import dns.message
import dns.rcode
import dns.rdatatype

DEFAULT_DOH_URL = "https://dns.adguard-dns.com/dns-query"
DEFAULT_BOOTSTRAP_IPS = (
    "94.140.14.14",
    "94.140.15.15",
    "2a10:50c0::ad1:ff",
    "2a10:50c0::ad2:ff",
)
DEFAULT_TIMEOUT_SECONDS = 4.0
MIN_CACHE_TTL_SECONDS = 30
MAX_CACHE_TTL_SECONDS = 3600
MAX_CNAME_DEPTH = 8
MAX_DNS_MESSAGE_BYTES = 65535

_ORIGINAL_GETADDRINFO = socket.getaddrinfo
_INSTALL_LOCK = threading.Lock()
_INSTALLED = False


class DnsOverHttpsResolver:
    def __init__(
        self,
        url: str = DEFAULT_DOH_URL,
        bootstrap_ips: Iterable[str] | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("DoH URL must be an HTTPS URL with a hostname")

        self.url = url
        self.host = parsed.hostname
        self.port = parsed.port or 443
        self.path = parsed.path or "/dns-query"
        if parsed.query:
            self.path = f"{self.path}?{parsed.query}"
        self.bootstrap_ips = self._normalize_bootstrap_ips(bootstrap_ips)
        self.timeout = timeout
        self._context = ssl.SSLContext(
            getattr(ssl, "PROTOCOL_TLS_CLIENT", ssl.PROTOCOL_TLS)
        )
        self._context.check_hostname = True
        self._context.verify_mode = ssl.CERT_REQUIRED
        self._context.load_default_certs()
        if hasattr(self._context, "minimum_version") and hasattr(ssl, "TLSVersion"):
            self._context.minimum_version = ssl.TLSVersion.TLSv1_2
        else:
            self._context.options |= getattr(ssl, "OP_NO_TLSv1", 0)
            self._context.options |= getattr(ssl, "OP_NO_TLSv1_1", 0)
        self._cache: dict[tuple[str, int], tuple[float, tuple[str, ...]]] = {}
        self._cache_lock = threading.Lock()

    def resolve(self, hostname: str, family: int = socket.AF_UNSPEC) -> list[str]:
        qtypes = _qtypes_for_family(family)
        addresses: list[str] = []
        for qtype in qtypes:
            addresses.extend(self._resolve_qtype(hostname, qtype))
        return list(dict.fromkeys(addresses))

    def _resolve_qtype(
        self, hostname: str, qtype: int, depth: int = 0
    ) -> tuple[str, ...]:
        if depth > MAX_CNAME_DEPTH:
            raise socket.gaierror(socket.EAI_FAIL, "CNAME chain is too deep")

        cache_key = (hostname.rstrip(".").lower(), qtype)
        now = time.monotonic()
        with self._cache_lock:
            cached = self._cache.get(cache_key)
            if cached and cached[0] > now:
                return cached[1]

        try:
            response = self._query(hostname, qtype)
            addresses, cnames, ttl = self._parse_response(response, qtype)
            child_expirations: list[float] = []
            if not addresses and cnames:
                for cname in cnames:
                    cname_key = (cname.rstrip(".").lower(), qtype)
                    if cname_key[0] == cache_key[0]:
                        continue
                    addresses.extend(
                        self._resolve_qtype(cname, qtype, depth=depth + 1)
                    )
                    with self._cache_lock:
                        child_cached = self._cache.get(cname_key)
                    if child_cached is not None:
                        child_expirations.append(child_cached[0])

            unique_addresses = tuple(dict.fromkeys(addresses))
            cache_ttl = max(0, min(ttl, MAX_CACHE_TTL_SECONDS))
            expires_at = now + cache_ttl
            if child_expirations:
                expires_at = min(expires_at, *child_expirations)
            with self._cache_lock:
                self._cache[cache_key] = (expires_at, unique_addresses)
            return unique_addresses
        except (OSError, ssl.SSLError, dns.exception.DNSException, ValueError) as exc:
            raise socket.gaierror(socket.EAI_AGAIN, str(exc)) from exc

    def _query(self, hostname: str, qtype: int) -> dns.message.Message:
        query = dns.message.make_query(hostname, qtype, use_edns=True)
        response_wire = self._post_dns_message(query.to_wire())
        response = dns.message.from_wire(response_wire)
        if not query.is_response(response):
            raise dns.exception.FormError
        return response

    def _post_dns_message(self, body: bytes) -> bytes:
        request = self._build_http_request(body)
        last_error: Exception | None = None
        for endpoint_ip in self._endpoint_ips():
            try:
                with socket.create_connection(
                    (endpoint_ip, self.port), timeout=self.timeout
                ) as raw_sock:
                    raw_sock.settimeout(self.timeout)
                    with self._context.wrap_socket(
                        raw_sock, server_hostname=self.host
                    ) as tls_sock:
                        tls_sock.settimeout(self.timeout)
                        tls_sock.sendall(request)
                        status_code, headers, response_body = (
                            self._read_http_response(tls_sock)
                        )

                if status_code != 200:
                    raise OSError(f"DoH server returned HTTP {status_code}")
                content_type = headers.get("content-type", "").split(";", 1)[0].strip()
                if content_type != "application/dns-message":
                    raise OSError(
                        f"Unexpected DoH content type: {content_type or 'unknown'}"
                    )
                if len(response_body) > MAX_DNS_MESSAGE_BYTES:
                    raise OSError("DNS response is too large")
                return response_body
            except OSError as exc:
                last_error = exc

        raise last_error or OSError("No DoH endpoint address available")

    def _endpoint_ips(self) -> tuple[str, ...]:
        if self.bootstrap_ips:
            return self.bootstrap_ips

        try:
            resolver = DnsOverHttpsResolver(
                url=DEFAULT_DOH_URL,
                bootstrap_ips=DEFAULT_BOOTSTRAP_IPS,
                timeout=self.timeout,
            )
            addresses = resolver.resolve(self.host)
            if addresses:
                return tuple(addresses)
        except (OSError, ssl.SSLError, dns.exception.DNSException, ValueError):
            pass

        addresses = []
        for result in _ORIGINAL_GETADDRINFO(
            self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM
        ):
            addresses.append(result[4][0])
        return tuple(dict.fromkeys(addresses))

    def _normalize_bootstrap_ips(
        self, bootstrap_ips: Iterable[str] | None
    ) -> tuple[str, ...]:
        if bootstrap_ips is not None:
            return tuple(bootstrap_ips)
        if self.host == urlparse(DEFAULT_DOH_URL).hostname:
            return DEFAULT_BOOTSTRAP_IPS
        return ()

    def _build_http_request(self, body: bytes) -> bytes:
        host = f"[{self.host}]" if ":" in self.host else self.host
        if self.port != 443:
            host = f"{host}:{self.port}"

        headers = [
            f"POST {self.path} HTTP/1.1",
            f"Host: {host}",
            "Accept: application/dns-message",
            "Content-Type: application/dns-message",
            f"Content-Length: {len(body)}",
            "Connection: close",
            "User-Agent: Chzzk-Rekoda/DoH",
            "",
            "",
        ]
        return "\r\n".join(headers).encode("ascii") + body

    @staticmethod
    def _read_http_response(sock: ssl.SSLSocket) -> tuple[int, dict[str, str], bytes]:
        raw = bytearray()
        while b"\r\n\r\n" not in raw:
            chunk = sock.recv(4096)
            if not chunk:
                raise OSError("connection closed before HTTP headers completed")
            raw.extend(chunk)
            if len(raw) > 65536:
                raise OSError("HTTP headers are too large")

        header_bytes, body = bytes(raw).split(b"\r\n\r\n", 1)
        header_lines = header_bytes.decode("iso-8859-1").split("\r\n")
        status_parts = header_lines[0].split(" ", 2)
        if len(status_parts) < 2 or not status_parts[1].isdigit():
            raise OSError("Invalid HTTP response from DoH server")
        status_code = int(status_parts[1])
        headers = {}
        for line in header_lines[1:]:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()

        if headers.get("transfer-encoding", "").lower() == "chunked":
            body = _read_chunked_body(sock, body)
        elif "content-length" in headers:
            content_length = int(headers["content-length"])
            body = _read_content_length_body(sock, body, content_length)
        else:
            body += _read_until_close(sock)

        return status_code, headers, body

    @staticmethod
    def _parse_response(
        response: dns.message.Message, qtype: int
    ) -> tuple[list[str], list[str], int]:
        rcode = response.rcode()
        if rcode == dns.rcode.NXDOMAIN:
            return [], [], MIN_CACHE_TTL_SECONDS
        if rcode != dns.rcode.NOERROR:
            raise socket.gaierror(socket.EAI_FAIL, dns.rcode.to_text(rcode))

        addresses: list[str] = []
        cnames: list[str] = []
        ttl_values: list[int] = []

        if not response.question:
            raise socket.gaierror(socket.EAI_FAIL)

        question = response.question[0]
        if question.rdtype != qtype:
            raise socket.gaierror(socket.EAI_FAIL)

        def normalize_name(name) -> str:
            return name.to_text(omit_final_dot=True).lower()

        address_records: dict[str, list[tuple[str, int]]] = {}
        cname_records: dict[str, list[tuple[str, str, int]]] = {}
        for section in (response.answer, response.additional):
            for rrset in section:
                owner = normalize_name(rrset.name)
                for item in rrset:
                    if qtype == dns.rdatatype.A and item.rdtype == dns.rdatatype.A:
                        address_records.setdefault(owner, []).append(
                            (item.address, rrset.ttl)
                        )
                    elif (
                        qtype == dns.rdatatype.AAAA
                        and item.rdtype == dns.rdatatype.AAAA
                    ):
                        address_records.setdefault(owner, []).append(
                            (item.address, rrset.ttl)
                        )
                    elif item.rdtype == dns.rdatatype.CNAME:
                        target = normalize_name(item.target)
                        cname_records.setdefault(owner, []).append(
                            (
                                target,
                                item.target.to_text(omit_final_dot=True),
                                rrset.ttl,
                            )
                        )

        pending = [normalize_name(question.name)]
        visited: set[str] = set()
        while pending:
            owner = pending.pop(0)
            if owner in visited:
                continue
            visited.add(owner)

            for address, ttl in address_records.get(owner, []):
                addresses.append(address)
                ttl_values.append(ttl)

            for target, display_target, ttl in cname_records.get(owner, []):
                cnames.append(display_target)
                ttl_values.append(ttl)
                if target not in visited:
                    pending.append(target)

        return addresses, cnames, min(ttl_values, default=MIN_CACHE_TTL_SECONDS)


def install_doh_dns(
    url: str | None = None,
    bootstrap_ips: Iterable[str] | None = None,
    timeout: float | None = None,
) -> None:
    global _INSTALLED

    with _INSTALL_LOCK:
        if _INSTALLED:
            return

        resolver = DnsOverHttpsResolver(
            url=url or os.environ.get("CHZZK_REKODA_DOH_DNS_URL", DEFAULT_DOH_URL),
            bootstrap_ips=(
                bootstrap_ips if bootstrap_ips is not None else _env_bootstrap_ips()
            ),
            timeout=timeout
            or _env_float("CHZZK_REKODA_DOH_DNS_TIMEOUT", DEFAULT_TIMEOUT_SECONDS),
        )

        def getaddrinfo(
            host_arg,
            port_arg,
            family=socket.AF_UNSPEC,
            socktype=0,
            proto=0,
            flags=0,
        ):
            if _should_use_original_resolver(host_arg, family, flags):
                return _ORIGINAL_GETADDRINFO(
                    host_arg, port_arg, family, socktype, proto, flags
                )

            hostname = _normalize_hostname(host_arg)
            try:
                addresses = resolver.resolve(hostname, family)
                results = _getaddrinfo_from_addresses(
                    addresses, port_arg, family, socktype, proto, flags
                )
                if results:
                    return results
                raise socket.gaierror(socket.EAI_NONAME, hostname)
            except socket.gaierror as doh_error:
                try:
                    return _ORIGINAL_GETADDRINFO(
                        host_arg, port_arg, family, socktype, proto, flags
                    )
                except socket.gaierror as system_error:
                    message = (
                        f"{hostname} via {resolver.url}: "
                        f"{doh_error.strerror or doh_error}"
                    )
                    raise socket.gaierror(doh_error.errno, message) from system_error

        socket.getaddrinfo = getaddrinfo
        _INSTALLED = True


def _read_content_length_body(
    sock: ssl.SSLSocket, body: bytes, content_length: int
) -> bytes:
    chunks = bytearray(body)
    while len(chunks) < content_length:
        chunk = sock.recv(content_length - len(chunks))
        if not chunk:
            raise OSError("connection closed before HTTP body completed")
        chunks.extend(chunk)
    return bytes(chunks[:content_length])


def _read_chunked_body(sock: ssl.SSLSocket, initial_body: bytes) -> bytes:
    buffer = bytearray(initial_body)
    body = bytearray()
    while True:
        line = _read_http_line(sock, buffer)
        size_text = line.split(b";", 1)[0].strip()
        chunk_size = int(size_text, 16)
        if chunk_size == 0:
            _read_exact_from_buffer(sock, buffer, 2)
            break
        body.extend(_read_exact_from_buffer(sock, buffer, chunk_size))
        _read_exact_from_buffer(sock, buffer, 2)
    return bytes(body)


def _read_http_line(sock: ssl.SSLSocket, buffer: bytearray) -> bytes:
    while b"\r\n" not in buffer:
        chunk = sock.recv(4096)
        if not chunk:
            raise OSError("connection closed before HTTP line completed")
        buffer.extend(chunk)
    line, rest = bytes(buffer).split(b"\r\n", 1)
    buffer[:] = rest
    return line


def _read_exact_from_buffer(
    sock: ssl.SSLSocket, buffer: bytearray, size: int
) -> bytes:
    while len(buffer) < size:
        chunk = sock.recv(size - len(buffer))
        if not chunk:
            raise OSError("connection closed before HTTP body completed")
        buffer.extend(chunk)
    result = bytes(buffer[:size])
    del buffer[:size]
    return result


def _read_until_close(sock: ssl.SSLSocket) -> bytes:
    chunks = bytearray()
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        chunks.extend(chunk)
    return bytes(chunks)


def _getaddrinfo_from_addresses(
    addresses: Iterable[str],
    port,
    requested_family: int,
    socktype: int,
    proto: int,
    flags: int,
):
    results = []
    last_error: socket.gaierror | None = None
    for address in addresses:
        address_family = _family_for_ip(address)
        if requested_family not in (socket.AF_UNSPEC, 0, address_family):
            continue
        try:
            results.extend(
                _ORIGINAL_GETADDRINFO(
                    address, port, address_family, socktype, proto, flags
                )
            )
        except socket.gaierror as exc:
            last_error = exc
    if not results and last_error is not None:
        raise last_error
    return results


def _qtypes_for_family(family: int) -> tuple[int, ...]:
    if family in (socket.AF_UNSPEC, 0):
        return (dns.rdatatype.A, dns.rdatatype.AAAA)
    if family == socket.AF_INET:
        return (dns.rdatatype.A,)
    if family == socket.AF_INET6:
        return (dns.rdatatype.AAAA,)
    raise socket.gaierror(socket.EAI_FAMILY, "unsupported address family")


def _family_for_ip(address: str) -> int:
    parsed = ipaddress.ip_address(address)
    return socket.AF_INET6 if parsed.version == 6 else socket.AF_INET


def _should_use_original_resolver(host, family: int, flags: int) -> bool:
    if host is None:
        return True
    if family not in (socket.AF_UNSPEC, 0, socket.AF_INET, socket.AF_INET6):
        return True
    if flags & getattr(socket, "AI_NUMERICHOST", 0):
        return True

    hostname = _normalize_hostname(host)
    if not hostname or hostname == "localhost" or hostname.endswith(".local"):
        return True
    try:
        ipaddress.ip_address(hostname.strip("[]"))
        return True
    except ValueError:
        return False


def _normalize_hostname(host) -> str:
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    return str(host).rstrip(".").lower()


def _env_bootstrap_ips() -> tuple[str, ...] | None:
    raw = os.environ.get("CHZZK_REKODA_DOH_DNS_BOOTSTRAP_IPS", "")
    values = tuple(value.strip() for value in raw.split(",") if value.strip())
    return values or None


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, ""))
    except ValueError:
        return default
