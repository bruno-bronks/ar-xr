"""SPEC-012 · REQ-OPS-008: modelo de custo reproduzivel, com premissas e precos de lista datados."""

from datetime import date
from pathlib import Path

import pytest
from spatial_ops.cost import (
    PRICES,
    SCENARIOS,
    Price,
    Scenario,
    monthly_cost,
    render_markdown,
    storage_growth_gb_per_month,
)

DOC = Path(__file__).resolve().parents[3] / "docs" / "cloud" / "cost-estimate.md"


def test_every_price_has_a_source_a_date_and_an_honest_verification_flag() -> None:
    assert PRICES
    for price in PRICES.values():
        assert price.source_url.startswith("https://")
        assert isinstance(price.retrieved, date)
        assert price.currency in {"EUR", "USD"}
        assert price.amount > 0
        assert isinstance(price.official, bool)


def test_prices_not_confirmed_against_the_official_page_are_flagged_as_such() -> None:
    unofficial = [p for p in PRICES.values() if not p.official]

    assert unofficial, "os precos coletados de terceiros nao podem se passar por oficiais"


def test_monthly_cost_adds_compute_storage_backup_and_egress() -> None:
    prices = {
        "vm": Price("vm", "mes", 10.0, "EUR", "https://example.test/vm", date(2026, 10, 20), False),
        "disk": Price(
            "disk", "GB-mes", 0.1, "EUR", "https://example.test/d", date(2026, 10, 20), False
        ),
        "backup": Price(
            "backup", "GB-mes", 0.02, "EUR", "https://example.test/b", date(2026, 10, 20), False
        ),
        "egress": Price(
            "egress", "GB", 0.01, "EUR", "https://example.test/e", date(2026, 10, 20), False
        ),
    }
    scenario = Scenario(
        "t", "teste", hosts=2, disk_gb=50, backup_gb=100, egress_gb=200,
        vm="vm", disk="disk", backup="backup", egress="egress",
    )  # fmt: skip

    cost = monthly_cost(scenario, prices)

    assert cost.items == {"compute": 20.0, "disk": 10.0, "backup": 2.0, "egress": 2.0}
    assert cost.total == pytest.approx(34.0)
    assert cost.currency == "EUR"


def test_a_scenario_cannot_mix_currencies_because_no_exchange_rate_is_sourced() -> None:
    prices = {
        "vm": Price("vm", "mes", 10.0, "EUR", "https://example.test/vm", date(2026, 10, 20), False),
        "disk": Price(
            "disk", "GB-mes", 0.1, "USD", "https://example.test/d", date(2026, 10, 20), False
        ),
    }
    scenario = Scenario("t", "teste", 1, 10, 0, 0, vm="vm", disk="disk", backup=None, egress=None)

    with pytest.raises(ValueError, match="currenc"):
        monthly_cost(scenario, prices)


def test_storage_growth_follows_devices_sensors_interval_and_row_size() -> None:
    # 10 dispositivos x 3 sensores a cada 2 s, 200 B/linha: 10*3*43200*30 = 38,88 M linhas/mes
    growth = storage_growth_gb_per_month(devices=10, sensors=3, interval_s=2.0, bytes_per_row=200)

    assert growth == pytest.approx(38_880_000 * 200 / 1e9, rel=1e-9)


def test_every_scenario_resolves_against_the_price_table_and_costs_something() -> None:
    assert SCENARIOS
    for scenario in SCENARIOS:
        cost = monthly_cost(scenario, PRICES)
        assert cost.total > 0, scenario.key


def test_the_committed_report_is_exactly_what_the_model_generates() -> None:
    """A doc nao pode divergir do modelo: se preco/premissa mudar, regenere (scripts/cost_model.py --write)."""
    assert DOC.read_text("utf-8").strip() == render_markdown().strip()


def test_the_report_states_the_limits_in_plain_words() -> None:
    text = render_markdown()

    assert "Nenhum serviço pago foi contratado" in text
    assert "terceiros" in text.lower()
    assert "estimativa" in text.lower()
