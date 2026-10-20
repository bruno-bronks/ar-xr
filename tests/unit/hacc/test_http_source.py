"""SPEC-010 · REQ-HACC-002 (e REQ-HACC-003, campos pessoais rejeitados): adaptador HTTP SOMENTE LEITURA, testado contra um servidor local de teste.

Nao ha HACC real aqui: o servidor abaixo e um dublê que grava cada requisicao recebida.
"""

import contextlib
import json
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
from spatial_hacc.http import HttpHaccSource
from spatial_hacc.source import HaccSource, HaccUnavailable

BED = {
    "bed_id": "BED-1",
    "ward_id": "WARD-1",
    "tenant_id": "org-a",
    "label": "Leito 1",
    "x": 1,
    "y": 1,
    "occupied": True,
    "observed_at": "2026-10-20T12:00:00Z",
    "flags": {
        "bed_exit_alarm": False,
        "iv_pump_alarm": False,
        "call_button": True,
        "cleaning_due": False,
    },
}
WARD = {"ward_id": "WARD-1", "tenant_id": "org-a", "name": "Ala 1", "width": 3, "height": 2}


@dataclass
class Stub:
    base_url: str
    requests: list[tuple[str, str]] = field(default_factory=list)
    routes: dict[str, tuple[int, bytes, dict[str, str], float]] = field(default_factory=dict)

    def route(
        self,
        path: str,
        body: object | bytes,
        status: int = 200,
        headers: dict[str, str] | None = None,
        delay_s: float = 0.0,
    ) -> None:
        payload = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.routes[path] = (status, payload, headers or {}, delay_s)


@pytest.fixture
def stub() -> Iterator[Stub]:
    state = Stub(base_url="")

    class Handler(BaseHTTPRequestHandler):
        def _handle(self) -> None:
            state.requests.append((self.command, self.path))
            if self.command != "GET":
                self.send_response(405)
                self.end_headers()
                return
            status, body, headers, delay = state.routes.get(self.path, (404, b"{}", {}, 0.0))
            time.sleep(delay)
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                self.wfile.write(body)

        do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _handle

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state.base_url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield state
    server.shutdown()
    server.server_close()


def _source(stub: Stub, **options: Any) -> HttpHaccSource:
    return HttpHaccSource(stub.base_url, allowed_hosts=["127.0.0.1"], **options)


def test_lists_wards_and_beds_with_get_only(stub: Stub) -> None:
    stub.route("/v1/wards", [WARD])
    stub.route("/v1/wards/WARD-1/beds", [BED])
    source = _source(stub)

    wards = source.list_wards()
    beds = source.list_beds("WARD-1")

    assert [w.ward_id for w in wards] == ["WARD-1"]
    assert beds[0].flags.call_button is True
    assert stub.requests == [("GET", "/v1/wards"), ("GET", "/v1/wards/WARD-1/beds")]


def test_the_port_and_the_adapter_expose_only_read_operations() -> None:
    forbidden = (
        "create",
        "update",
        "delete",
        "post",
        "put",
        "patch",
        "write",
        "set",
        "save",
        "send",
    )
    for cls in (HaccSource, HttpHaccSource):
        public = [n for n in dir(cls) if not n.startswith("_")]
        assert sorted(public) == ["list_beds", "list_wards"], cls
        assert not [n for n in public if n.startswith(forbidden)]


@pytest.mark.parametrize(
    "ward_id", ["../etc/passwd", "a/b", "a b", "", "x" * 65, "w?x=1", "w#f", "w%2F"]
)
def test_ward_id_cannot_alter_the_path_or_reach_other_endpoints(stub: Stub, ward_id: str) -> None:
    source = _source(stub)

    with pytest.raises(HaccUnavailable):
        source.list_beds(ward_id)

    assert stub.requests == []  # nem chegou a pedir


def test_redirects_are_not_followed(stub: Stub) -> None:
    stub.route("/v1/wards", b"", status=302, headers={"Location": "/v1/other"})
    stub.route("/v1/other", [WARD])

    with pytest.raises(HaccUnavailable):
        _source(stub).list_wards()

    assert stub.requests == [("GET", "/v1/wards")]


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500, 503])
def test_non_200_is_unavailable_without_leaking_the_body(stub: Stub, status: int) -> None:
    stub.route("/v1/wards", b"SEGREDO-INTERNO stack trace", status=status)

    with pytest.raises(HaccUnavailable) as caught:
        _source(stub).list_wards()

    assert "SEGREDO" not in str(caught.value)
    assert stub.base_url not in str(caught.value)


@pytest.mark.parametrize(
    "body",
    [b"nao e json", b"{}", b'{"a": 1}', b"null", b'[{"ward_id": 1}]', b"[1, 2]"],
)
def test_invalid_json_or_shape_is_unavailable(stub: Stub, body: bytes) -> None:
    stub.route("/v1/wards", body)

    with pytest.raises(HaccUnavailable):
        _source(stub).list_wards()


def test_payload_with_personal_fields_is_rejected_whole(stub: Stub) -> None:
    stub.route("/v1/wards/WARD-1/beds", [BED, {**BED, "bed_id": "BED-2", "patient_name": "Fulano"}])

    with pytest.raises(HaccUnavailable) as caught:
        _source(stub).list_beds("WARD-1")

    assert "Fulano" not in str(caught.value)


def test_oversized_body_is_rejected(stub: Stub) -> None:
    stub.route("/v1/wards", b"[" + b" " * 5000 + b"]")

    with pytest.raises(HaccUnavailable, match="too large"):
        _source(stub, max_bytes=1000).list_wards()


def test_too_many_items_are_rejected(stub: Stub) -> None:
    stub.route("/v1/wards", [{**WARD, "ward_id": f"W{i}"} for i in range(1001)])

    with pytest.raises(HaccUnavailable):
        _source(stub).list_wards()


def test_slow_server_times_out(stub: Stub) -> None:
    stub.route("/v1/wards", [WARD], delay_s=1.5)
    started = time.monotonic()

    with pytest.raises(HaccUnavailable):
        _source(stub, timeout_s=0.3).list_wards()

    assert time.monotonic() - started < 1.2


def test_connection_refused_is_unavailable() -> None:
    source = HttpHaccSource("http://127.0.0.1:1", allowed_hosts=["127.0.0.1"], timeout_s=0.5)

    with pytest.raises(HaccUnavailable):
        source.list_wards()


@pytest.mark.parametrize(
    ("url", "allowed"),
    [
        ("https://evil.example.com", ["hacc.example.com"]),  # host fora da lista
        ("ftp://hacc.example.com", ["hacc.example.com"]),
        ("file:///etc/passwd", ["hacc.example.com"]),
        ("http://hacc.example.com", ["hacc.example.com"]),  # http so para loopback
        ("https://user:pw@hacc.example.com", ["hacc.example.com"]),  # credenciais na URL
        ("https://hacc.example.com?x=1", ["hacc.example.com"]),
        ("https://hacc.example.com#f", ["hacc.example.com"]),
        ("hacc.example.com", ["hacc.example.com"]),
        ("https://hacc.example.com", []),  # lista vazia nega tudo
        ("", ["hacc.example.com"]),
    ],
)
def test_unsafe_base_urls_are_refused_at_construction(url: str, allowed: list[str]) -> None:
    with pytest.raises(ValueError, match=r"(?i)hacc"):
        HttpHaccSource(url, allowed_hosts=allowed)


def test_https_with_an_allowed_host_and_http_loopback_are_accepted() -> None:
    HttpHaccSource("https://hacc.example.com", allowed_hosts=["hacc.example.com"])
    HttpHaccSource("https://hacc.example.com/base/", allowed_hosts=["hacc.example.com"])
    HttpHaccSource("http://localhost:8080", allowed_hosts=["localhost"])
    HttpHaccSource("http://127.0.0.1:8080", allowed_hosts=["127.0.0.1"])


def test_base_path_prefix_is_preserved(stub: Stub) -> None:
    stub.route("/api/v1/wards", [WARD])
    source = HttpHaccSource(stub.base_url + "/api", allowed_hosts=["127.0.0.1"])

    assert [w.ward_id for w in source.list_wards()] == ["WARD-1"]
    assert stub.requests == [("GET", "/api/v1/wards")]
