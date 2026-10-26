"""SPEC-010 · REQ-HACC-007, REQ-HACC-002 (D-054): fonte de integracao com o HACC real (somente leitura).

Servidor HTTP de verdade em loopback. Nenhum dado de pessoa entra: campo fora da lista rejeita a resposta
INTEIRA, o token vai so no cabecalho e nunca em erro/log, e a leitura e feita por GET em um caminho fixo.
"""

import json
import threading
from collections.abc import Iterator
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
from spatial_hacc.integration import DEFAULT_PROFILE, HaccIntegrationSource
from spatial_hacc.source import HaccUnavailable

TOKEN = "integration-test-token-123"  # valor ficticio de teste
GENERATED = "2026-10-26T14:06:17.919909+00:00"


def _body(beds: list[dict[str, Any]] | None = None, generated_at: str = GENERATED) -> bytes:
    if beds is None:
        beds = [
            {"bed_id": "UTI-02", "sector": "ICU", "status": "available", "occupied": False},
            {"bed_id": "UTI-01", "sector": "ICU", "status": "occupied", "occupied": True},
            {"bed_id": "UTI-03", "sector": "ICU", "status": "unavailable", "occupied": True},
            {"bed_id": "ER-01", "sector": "Emergency", "status": "occupied", "occupied": True},
        ]
    return json.dumps({"generated_at": generated_at, "beds": beds}).encode()


class _Server:
    def __init__(self) -> None:
        self.status = 200
        self.body = _body()
        self.requests: list[dict[str, Any]] = []
        self.redirect_to: str | None = None
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                outer.requests.append(
                    {"path": self.path, "auth": self.headers.get("Authorization")}
                )
                if outer.redirect_to:
                    self.send_response(302)
                    self.send_header("Location", outer.redirect_to)
                    self.end_headers()
                    return
                self.send_response(outer.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(outer.body)))
                self.end_headers()
                self.wfile.write(outer.body)

            def log_message(self, format: str, *args: Any) -> None:
                return

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.httpd.server_address[1]}"


@pytest.fixture
def server() -> Iterator[_Server]:
    srv = _Server()
    srv.thread.start()
    yield srv
    srv.httpd.shutdown()
    srv.httpd.server_close()


def _source(server: _Server, **kw: Any) -> HaccIntegrationSource:
    options: dict[str, Any] = {
        "token": TOKEN,
        "allowed_hosts": ["127.0.0.1"],
        "tenant_id": "org-a",
        "cache_ttl_s": 0.0,
    }
    options.update(kw)
    return HaccIntegrationSource(server.url, **options)


def test_sectors_become_wards_from_the_profile_and_only_populated_ones_appear(
    server: _Server,
) -> None:
    wards = {w.ward_id: w for w in _source(server).list_wards()}

    assert set(wards) == {"HACC-ICU", "HACC-ER"}  # Ward nao veio: nao e inventada
    assert wards["HACC-ICU"].name == DEFAULT_PROFILE["ICU"].name
    assert wards["HACC-ICU"].tenant_id == "org-a"
    assert (wards["HACC-ICU"].width, wards["HACC-ICU"].height) == (3, 1)  # 3 leitos, 3 colunas


def test_beds_are_placed_row_major_by_id_order_and_labelled_with_their_id(server: _Server) -> None:
    beds = _source(server).list_beds("HACC-ICU")

    assert [(b.bed_id, b.label, b.x, b.y) for b in beds] == [
        ("UTI-01", "UTI-01", 1, 1),
        ("UTI-02", "UTI-02", 2, 1),
        ("UTI-03", "UTI-03", 3, 1),
    ]
    assert {b.ward_id for b in beds} == {"HACC-ICU"}


def test_status_maps_to_occupied_and_blocked_and_there_are_no_invented_alarms(
    server: _Server,
) -> None:
    beds = {b.bed_id: b for b in _source(server).list_beds("HACC-ICU")}

    assert (beds["UTI-01"].occupied, beds["UTI-01"].blocked) == (True, False)
    assert (beds["UTI-02"].occupied, beds["UTI-02"].blocked) == (False, False)
    assert (beds["UTI-03"].occupied, beds["UTI-03"].blocked) == (True, True)  # indisponivel
    for bed in beds.values():
        assert not any(bed.flags.model_dump().values())  # o HACC nao tem alarmes: nada e inventado


def test_observed_at_is_the_hacc_snapshot_time(server: _Server) -> None:
    beds = _source(server).list_beds("HACC-ICU")

    assert {b.observed_at for b in beds} == {datetime(2026, 10, 26, 14, 6, 17, 919909, tzinfo=UTC)}


def test_the_ward_grid_grows_to_fit_more_beds_than_one_row(server: _Server) -> None:
    server.body = _body(
        [
            {"bed_id": f"WARD-{i:02d}", "sector": "Ward", "status": "available", "occupied": False}
            for i in range(1, 21)
        ]
    )

    ward = _source(server).list_wards()[0]
    beds = _source(server).list_beds("HACC-WARD")

    assert (ward.width, ward.height) == (5, 4)
    assert (beds[0].x, beds[0].y) == (1, 1)
    assert (beds[-1].x, beds[-1].y) == (5, 4)


def test_the_token_goes_only_in_the_authorization_header_to_one_fixed_path(server: _Server) -> None:
    _source(server).list_beds("HACC-ICU")

    assert server.requests == [{"path": "/integration/v1/beds", "auth": f"Bearer {TOKEN}"}]


def test_a_field_outside_the_allow_list_rejects_the_whole_response(server: _Server) -> None:
    server.body = _body(
        [
            {
                "bed_id": "UTI-01",
                "sector": "ICU",
                "status": "occupied",
                "occupied": True,
                "patient_id": "P-123",
            }
        ]
    )

    with pytest.raises(HaccUnavailable):
        _source(server).list_wards()


@pytest.mark.parametrize("field", ["name", "age", "gender", "priority"])
def test_person_fields_are_never_accepted(server: _Server, field: str) -> None:
    bed = {"bed_id": "UTI-01", "sector": "ICU", "status": "occupied", "occupied": True, field: "x"}
    server.body = _body([bed])

    with pytest.raises(HaccUnavailable):
        _source(server).list_beds("HACC-ICU")


def test_unknown_status_or_sector_never_becomes_a_normal_bed(server: _Server) -> None:
    server.body = _body(
        [{"bed_id": "UTI-01", "sector": "ICU", "status": "cleaning-now", "occupied": False}]
    )
    with pytest.raises(HaccUnavailable):
        _source(server).list_wards()

    server.body = _body(
        [{"bed_id": "X-01", "sector": "Cafeteria", "status": "available", "occupied": False}]
    )
    assert _source(server).list_wards() == []  # setor fora do perfil: ignorado, nao desenhado


@pytest.mark.parametrize("status", [401, 403, 404, 500, 503])
def test_non_200_is_unavailable_without_leaking_anything(server: _Server, status: int) -> None:
    server.status = status

    with pytest.raises(HaccUnavailable) as raised:
        _source(server).list_wards()

    assert TOKEN not in str(raised.value)
    assert server.url not in str(raised.value)


def test_redirects_are_not_followed(server: _Server) -> None:
    server.redirect_to = "http://127.0.0.1:1/steal"

    with pytest.raises(HaccUnavailable):
        _source(server).list_wards()

    assert len(server.requests) == 1


def test_invalid_json_and_oversized_bodies_are_unavailable(server: _Server) -> None:
    server.body = b"not json"
    with pytest.raises(HaccUnavailable):
        _source(server).list_wards()

    server.body = _body()
    with pytest.raises(HaccUnavailable):
        _source(server, max_bytes=10).list_wards()


def test_an_unreachable_hacc_is_unavailable_not_a_crash() -> None:
    source = HaccIntegrationSource(
        "http://127.0.0.1:9", token=TOKEN, allowed_hosts=["127.0.0.1"], tenant_id="org-a",
        timeout_s=0.5,
    )  # fmt: skip

    with pytest.raises(HaccUnavailable) as raised:
        source.list_wards()

    assert TOKEN not in str(raised.value)


def test_requests_in_a_short_window_are_coalesced_into_one_call(server: _Server) -> None:
    source = _source(server, cache_ttl_s=60.0)

    source.list_wards()
    source.list_beds("HACC-ICU")
    source.list_beds("HACC-ER")

    assert len(server.requests) == 1


def test_the_cache_expires(server: _Server) -> None:
    now = [1000.0]
    source = _source(server, cache_ttl_s=2.0, clock=lambda: now[0])

    source.list_wards()
    now[0] += 5
    source.list_wards()

    assert len(server.requests) == 2


@pytest.mark.parametrize(
    ("url", "hosts"),
    [
        ("http://hacc.example.test", ["hacc.example.test"]),  # http fora do loopback
        ("https://hacc.example.test", ["other.example.test"]),  # host fora da lista
        ("https://user:pw@hacc.example.test", ["hacc.example.test"]),
        ("ftp://hacc.example.test", ["hacc.example.test"]),
    ],
)
def test_the_base_url_is_validated(url: str, hosts: list[str]) -> None:
    with pytest.raises(ValueError, match="HACC"):
        HaccIntegrationSource(url, token=TOKEN, allowed_hosts=hosts, tenant_id="org-a")


@pytest.mark.parametrize("token", ["", "short", " " * 20])
def test_a_missing_or_weak_token_is_refused_at_construction(server: _Server, token: str) -> None:
    with pytest.raises(ValueError, match="token"):
        HaccIntegrationSource(
            server.url, token=token, allowed_hosts=["127.0.0.1"], tenant_id="org-a"
        )


def test_a_hostile_ward_id_is_rejected_before_any_request(server: _Server) -> None:
    with pytest.raises(HaccUnavailable):
        _source(server).list_beds("../../etc/passwd")

    assert server.requests == []
