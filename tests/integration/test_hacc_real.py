"""SPEC-010 · REQ-HACC-007 (D-054): a fonte de integracao contra um HACC REAL em execucao.

Opt-in: defina HACC_REAL_URL (ex.: http://127.0.0.1:28000) e HACC_REAL_TOKEN. O HACC usado nos testes e uma COPIA
isolada com a rota de integracao (docs/integration/hacc-patch). So leitura; nunca contra uma instalacao com
dados reais de pessoas. A conferencia cruzada usa o endpoint nativo `GET /beds/summary` do HACC.
"""

import json
import os
import time
import urllib.request

import pytest
from spatial_hacc.integration import HaccIntegrationSource
from spatial_hacc.source import HaccUnavailable

URL = os.environ.get("HACC_REAL_URL")
TOKEN = os.environ.get("HACC_REAL_TOKEN", "")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not (URL and TOKEN), reason="defina HACC_REAL_URL e HACC_REAL_TOKEN"),
]


def _source(token: str = TOKEN) -> HaccIntegrationSource:
    assert URL is not None
    return HaccIntegrationSource(
        URL, token=token, allowed_hosts=["127.0.0.1"], tenant_id="org-a", cache_ttl_s=0.0
    )


def _native_occupied() -> int:
    assert URL is not None
    with urllib.request.urlopen(URL + "/beds/summary", timeout=10) as response:  # noqa: S310
        return int(json.load(response)["occupied"])


def test_the_real_hacc_yields_the_three_sectors_with_every_bed_and_no_invented_alarms() -> None:
    source = _source()

    wards = {w.ward_id: w for w in source.list_wards()}
    beds = {w: source.list_beds(w) for w in wards}

    assert set(wards) == {"HACC-ICU", "HACC-ER", "HACC-WARD"}
    assert {k: len(v) for k, v in beds.items()} == {"HACC-ICU": 5, "HACC-ER": 10, "HACC-WARD": 20}
    assert (wards["HACC-WARD"].width, wards["HACC-WARD"].height) == (5, 4)
    for ward_beds in beds.values():
        assert not any(any(b.flags.model_dump().values()) for b in ward_beds)
        assert len({b.observed_at for b in ward_beds}) == 1  # um unico instantaneo


def test_occupancy_matches_the_hacc_own_summary() -> None:
    """Cruza com `/beds/summary` (fonte independente do HACC); o simulador muda o estado, entao repete."""
    source = _source()
    matches = False
    for _ in range(8):
        mine = sum(b.occupied for w in source.list_wards() for b in source.list_beds(w.ward_id))
        if mine == _native_occupied():
            matches = True
            break
        time.sleep(0.5)

    assert matches


def test_a_wrong_token_is_refused_without_leaking_it() -> None:
    wrong = "wrong-token-wrong-token-1"

    with pytest.raises(HaccUnavailable) as raised:
        _source(wrong).list_wards()

    assert wrong not in str(raised.value)
