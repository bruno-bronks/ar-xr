"""SPEC-008 A7 · REQ-AR-003: fixtures JSON do cliente AR sao geradas pela API REAL (nunca escritas a mao).

O cliente C# (tests/csharp) le exatamente estes arquivos. Se a API mudar, este teste falha ate as
fixtures serem regeneradas com `UPDATE_FIXTURES=1 pytest tests/contract/test_ar_fixtures.py`.
Requisitos: REQ-AR-003, REQ-AR-004.
"""

import json
import os
from pathlib import Path

from spatial_domain.status import Quality
from spatial_storage.memory import InMemoryRepository
from spatial_storage.seed_data import SEED

from tests.unit.api._app import Clock, auth, feed, make_client, reading

FIXTURES = Path(__file__).resolve().parents[1] / "csharp" / "fixtures"


def _dump(payload: object) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _generate() -> dict[str, str]:
    out: dict[str, str] = {}

    # --- CRITICAL: EQ-001 com temperatura acima do limite critico, vibracao normal
    repo = InMemoryRepository(SEED)
    feed(repo, reading("EQ-001", "temperature", 101.0), reading("EQ-001", "vibration", 1.0))
    client = make_client(repo=repo)
    out["marker_ok.json"] = _dump(
        client.get("/api/v1/spatial/markers/QR-EQ-001", headers=auth()).json()
    )
    out["twin_critical.json"] = _dump(
        client.get("/api/v1/equipment/EQ-001/twin", headers=auth()).json()
    )
    out["alerts_critical.json"] = _dump(
        client.get("/api/v1/equipment/EQ-001/alerts", headers=auth()).json()
    )

    # --- UNKNOWN: EQ-003 sem nenhum dado
    out["twin_unknown.json"] = _dump(
        client.get("/api/v1/equipment/EQ-003/twin", headers=auth()).json()
    )
    out["alerts_empty.json"] = _dump(
        client.get("/api/v1/equipment/EQ-003/alerts", headers=auth()).json()
    )

    # --- erros uniformes
    out["error_404.json"] = _dump(
        client.get("/api/v1/spatial/markers/QR-NAO-EXISTE", headers=auth()).json()
    )
    out["error_401.json"] = _dump(client.get("/api/v1/equipment").json())
    limited = make_client(marker_rate_limit=1)
    limited.get("/api/v1/spatial/markers/QR-EQ-001", headers=auth())
    out["error_429.json"] = _dump(
        limited.get("/api/v1/spatial/markers/QR-EQ-001", headers=auth()).json()
    )

    # --- OFFLINE: EQ-002 com dado critico, depois silencio de 120 s
    repo2, clock = InMemoryRepository(SEED), Clock()
    feed(repo2, reading("EQ-002", "temperature", 500.0), reading("EQ-002", "vibration", 1.0))
    client2 = make_client(repo=repo2, clock=clock)
    clock.advance(120)
    out["twin_offline.json"] = _dump(
        client2.get("/api/v1/equipment/EQ-002/twin", headers=auth()).json()
    )
    out["alerts_offline.json"] = _dump(
        client2.get("/api/v1/equipment/EQ-002/alerts", headers=auth()).json()
    )

    # --- sensor com qualidade BAD (sensor defeituoso) => valid=false, status UNKNOWN
    repo3 = InMemoryRepository(SEED)
    feed(
        repo3,
        reading("EQ-003", "temperature", 50.0, quality=Quality.BAD),
        reading("EQ-003", "vibration", 1.0),
    )
    out["twin_bad_sensor.json"] = _dump(
        make_client(repo=repo3).get("/api/v1/equipment/EQ-003/twin", headers=auth()).json()
    )
    return out


def test_ar_fixtures_match_what_the_real_api_returns() -> None:
    generated = _generate()
    if os.environ.get("UPDATE_FIXTURES") == "1":
        FIXTURES.mkdir(parents=True, exist_ok=True)
        for name, text in generated.items():
            (FIXTURES / name).write_text(text, encoding="utf-8", newline="\n")

    stale = [
        name
        for name, text in generated.items()
        if not (FIXTURES / name).exists()
        or (FIXTURES / name).read_text("utf-8").replace("\r\n", "\n") != text
    ]
    assert not stale, f"fixtures desatualizadas (rode com UPDATE_FIXTURES=1): {stale}"


def test_no_orphan_fixture_files() -> None:
    assert {p.name for p in FIXTURES.glob("*.json")} == set(_generate())


def test_fixture_semantics_are_what_the_client_tests_assume() -> None:
    generated = {name: json.loads(text) for name, text in _generate().items()}

    assert generated["twin_critical.json"]["status"] == "CRITICAL"
    assert generated["twin_unknown.json"]["status"] == "UNKNOWN"
    assert generated["twin_offline.json"]["status"] == "OFFLINE"
    assert generated["twin_bad_sensor.json"]["status"] == "UNKNOWN"
    assert [a["severity"] for a in generated["alerts_offline.json"]] == ["OFFLINE"]
    assert generated["alerts_empty.json"] == []
    assert generated["error_404.json"] == {"detail": "not found"}
    assert generated["error_401.json"] == {"detail": "not authenticated"}
    assert generated["error_429.json"] == {"detail": "rate limit exceeded"}
