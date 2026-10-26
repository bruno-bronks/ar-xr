"""SPEC-010 · REQ-HACC-007 (D-054): leito BLOQUEADO na API e a fonte de integracao composta pela configuracao."""

from typing import Any

from app.main import build_hacc
from spatial_hacc.integration import HaccIntegrationSource
from spatial_hacc.models import BedRecord, FlagsRecord, WardRecord
from spatial_hacc.simulated import SimulatedHaccSource

from tests.unit.api._app import NOW, auth, make_client

NURSE_A = "demo-nurse-a"
QUIET = FlagsRecord(
    bed_exit_alarm=False, iv_pump_alarm=False, call_button=False, cleaning_due=False
)


def _bed(bed_id: str, x: int, **kw: Any) -> BedRecord:
    return BedRecord(
        bed_id=bed_id, ward_id="W", tenant_id="org-a", label=bed_id, x=x, y=1,
        occupied=kw.pop("occupied", True), flags=kw.pop("flags", QUIET),
        observed_at=NOW, **kw,
    )  # fmt: skip


class _Source:
    def __init__(self, beds: list[BedRecord]) -> None:
        self.beds = beds

    def list_wards(self) -> list[WardRecord]:
        return [WardRecord(ward_id="W", tenant_id="org-a", name="Ala W", width=3, height=1)]

    def list_beds(self, ward_id: str) -> list[BedRecord]:
        return self.beds


def test_a_blocked_bed_is_reported_as_blocked_with_no_alerts() -> None:
    client = make_client(hacc=_Source([_bed("B1", 1, blocked=True), _bed("B2", 2)]))

    body = client.get("/api/v1/hacc/wards/W/beds", headers=auth(NURSE_A)).json()

    beds = {b["bed_id"]: b for b in body["beds"]}
    assert beds["B1"]["status"] == "BLOCKED"
    assert beds["B1"]["alerts"] == []
    assert beds["B2"]["status"] == "NORMAL"
    assert body["status"] == "NORMAL"  # um leito bloqueado nao piora a ala


def test_the_ward_summary_ignores_blocked_beds_for_its_status_and_alert_count() -> None:
    client = make_client(hacc=_Source([_bed("B1", 1, blocked=True), _bed("B2", 2, blocked=True)]))

    [ward] = client.get("/api/v1/hacc/wards", headers=auth(NURSE_A)).json()

    assert (ward["status"], ward["alert_count"], ward["bed_count"]) == ("NORMAL", 0, 2)


def test_an_alarm_on_a_blocked_bed_still_raises_the_ward_to_alert() -> None:
    flags = FlagsRecord(
        bed_exit_alarm=False, iv_pump_alarm=True, call_button=False, cleaning_due=False
    )
    client = make_client(hacc=_Source([_bed("B1", 1, blocked=True, flags=flags)]))

    body = client.get("/api/v1/hacc/wards/W/beds", headers=auth(NURSE_A)).json()

    assert body["beds"][0]["status"] == "ALERT"
    assert body["status"] == "ALERT"


class _Settings:
    hacc_source = "hacc"
    hacc_base_url = "http://127.0.0.1:28000"
    hacc_allowed_hosts = "127.0.0.1"
    hacc_tenant_id = "org-a"
    hacc_allow_plain_http = False

    class hacc_api_token:
        @staticmethod
        def get_secret_value() -> str:
            return "a-sufficiently-long-token-1"


def test_the_composition_root_builds_the_integration_source_only_when_configured() -> None:
    assert isinstance(build_hacc(_Settings(), lambda: NOW), HaccIntegrationSource)  # type: ignore[arg-type]
    assert isinstance(build_hacc(None, lambda: NOW), SimulatedHaccSource)
