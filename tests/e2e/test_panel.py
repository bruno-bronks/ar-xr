"""SPEC-007 · REQ-UX-001: painel web 2D no navegador REAL (Playwright + Microsoft Edge instalado).

Roda contra a pilha Compose no ar (BASE_URL). O simulador e parado para controlar os dados.
Evidencias (screenshots) sao gravadas em docs/evidence/phase-1/.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, Route, expect, sync_playwright
from sqlalchemy import text

from tests.integration._stack import (
    BASE_URL,
    compose,
    db_engine,
    equipment_status,
    feed_equipment,
    requires_stack,
    wait_until,
)

pytestmark = [pytest.mark.e2e, requires_stack]

EVIDENCE = Path(__file__).resolve().parents[2] / "docs/evidence/phase-1"
CHANNEL = os.environ.get("E2E_BROWSER_CHANNEL", "msedge")


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    with sync_playwright() as p:
        instance = p.chromium.launch(channel=CHANNEL, headless=True)
        yield instance
        instance.close()


@pytest.fixture(scope="module", autouse=True)
def quiet_simulator() -> Iterator[None]:
    """Simulador parado: so os dados publicados por estes testes existem."""
    compose("stop", "simulator")
    yield
    compose("start", "simulator")


@pytest.fixture(autouse=True)
def controlled_data(quiet_simulator: None) -> None:
    """Antes de CADA teste: EQ-001 critico e EQ-002 normal, ambos frescos (<30 s).

    EQ-003 nunca recebe dado novo: vira OFFLINE em 30 s. Reaplicar por teste evita dependencia de
    ordem/tempo (a abertura do navegador sozinha pode levar >15 s).
    """
    feed_equipment("EQ-001", temperature=101.0, vibration=1.0)
    feed_equipment("EQ-002", temperature=40.0, vibration=1.0)
    wait_until(lambda: equipment_status("EQ-001") == "CRITICAL", 20, what="EQ-001 critico")
    wait_until(lambda: equipment_status("EQ-002") == "NORMAL", 20, what="EQ-002 normal")


@pytest.fixture
def page(browser: Browser) -> Iterator[Page]:
    context = browser.new_context(viewport={"width": 1100, "height": 800}, locale="pt-BR")
    page = context.new_page()
    assert BASE_URL is not None
    page.goto(BASE_URL + "/panel/")
    yield page
    context.close()


def _shot(page: Page, name: str) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(EVIDENCE / name), full_page=True)


def test_panel_shows_critical_alert_and_normal_equipment(page: Page) -> None:
    expect(page.get_by_test_id("card-EQ-001")).to_have_attribute(
        "data-status", "CRITICAL", timeout=10_000
    )
    expect(page.get_by_test_id("card-EQ-002")).to_have_attribute("data-status", "NORMAL")
    expect(page.get_by_test_id("status-EQ-001")).to_contain_text("Crítico")
    alert = page.get_by_test_id("alert").first
    expect(alert).to_contain_text("EQ-001")
    expect(alert).to_contain_text("temperature")
    expect(alert).to_have_attribute("data-severity", "CRITICAL")
    expect(page.locator("#alert-count")).not_to_have_text("0")
    expect(page.locator("#error-banner")).to_be_hidden()
    _shot(page, "panel-critical-alert.png")


def test_silent_equipment_is_shown_as_offline_never_as_normal(page: Page) -> None:
    card = page.get_by_test_id("card-EQ-003")

    expect(card).to_have_attribute("data-status", "OFFLINE", timeout=60_000)
    expect(page.get_by_test_id("status-EQ-003")).to_contain_text("Offline")
    expect(card).to_contain_text("Sem dados recentes")
    expect(card).not_to_contain_text("Normal")
    offline_alerts = page.locator('[data-testid="alert"][data-severity="OFFLINE"]')
    expect(offline_alerts.filter(has_text="EQ-003")).to_have_count(1)
    _shot(page, "panel-offline.png")


def test_switching_organization_shows_only_that_orgs_equipment(page: Page) -> None:
    expect(page.get_by_test_id("card-EQ-001")).to_be_visible(timeout=10_000)

    page.select_option("#org", "demo-operator-b")

    expect(page.get_by_test_id("card-EQ-B01")).to_be_visible(timeout=10_000)
    expect(page.get_by_test_id("card-EQ-001")).to_have_count(0)
    expect(page.locator("#cards")).not_to_contain_text("Compressor")


def test_invalid_token_shows_visible_error_and_no_data(page: Page) -> None:
    page.select_option("#org", "invalid-token")

    expect(page.locator("#error-banner")).to_be_visible(timeout=10_000)
    expect(page.locator("#error-banner")).to_contain_text("401")
    expect(page.locator("#cards [data-testid^='card-']")).to_have_count(0)
    _shot(page, "panel-error.png")


def test_when_api_fails_last_state_stays_visible_but_marked_stale(page: Page) -> None:
    expect(page.get_by_test_id("card-EQ-001")).to_be_visible(timeout=10_000)

    page.route("**/api/v1/**", lambda route: route.abort())
    expect(page.locator("#error-banner")).to_be_visible(timeout=10_000)

    card = page.get_by_test_id("card-EQ-001")
    expect(card).to_be_visible()  # nao apaga o ultimo estado
    expect(card).to_have_attribute("data-stale", "true")
    expect(page.locator("#freshness")).to_have_attribute("data-stale", "true")


def test_panel_is_usable_on_a_360px_phone_without_horizontal_scroll(browser: Browser) -> None:
    assert BASE_URL is not None
    context = browser.new_context(viewport={"width": 360, "height": 740})
    page = context.new_page()
    page.goto(BASE_URL + "/panel/")
    expect(page.get_by_test_id("card-EQ-001")).to_be_visible(timeout=10_000)

    overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    _shot(page, "panel-mobile-360.png")
    context.close()

    assert overflow <= 0


def test_hostile_equipment_name_is_rendered_as_text_and_never_executes(page: Page) -> None:
    """Nome malicioso vindo do banco/API: textContent + CSP => aparece literal, nada executa."""
    hostile = "<img src=x onerror=window.__xss=1>"
    with db_engine().begin() as conn:
        conn.execute(text("UPDATE equipment SET name = :n WHERE id = 'EQ-002'"), {"n": hostile})
    try:
        page.reload()
        card = page.get_by_test_id("card-EQ-002")
        expect(card).to_contain_text(hostile, timeout=10_000)  # texto literal, com os sinais < >

        assert page.locator("#cards img").count() == 0
        assert page.evaluate("window.__xss === undefined")
    finally:
        with db_engine().begin() as conn:
            conn.execute(
                text("UPDATE equipment SET name = 'Bomba centrifuga 02' WHERE id = 'EQ-002'")
            )


def test_late_response_from_previous_org_is_discarded_after_switching(page: Page) -> None:
    """Regressao: respostas EM VOO da org A (fase dos twins) nao podem ser desenhadas apos trocar p/ B."""
    expect(page.get_by_test_id("card-EQ-001")).to_be_visible(timeout=10_000)

    def delay_org_a_twins(route: Route) -> None:
        if route.request.headers.get("authorization") == "Bearer demo-operator-a":
            page.wait_for_timeout(4000)  # a resposta de A chega bem DEPOIS da troca
        route.continue_()

    page.route("**/api/v1/equipment/*/twin", delay_org_a_twins)
    page.evaluate(
        """() => {
            window.__leaked = false;
            window.__armed = false;
            new MutationObserver(() => {
                // defeito transitorio: qualquer aparicao do cartao da org A apos a troca conta
                if (window.__armed && document.querySelector('[data-testid="card-EQ-001"]')) window.__leaked = true;
            }).observe(document.getElementById('cards'), { childList: true, subtree: true });
        }"""
    )
    page.wait_for_timeout(2600)  # o proximo poll (2 s) de A fica em voo na fase dos twins
    page.select_option("#org", "demo-operator-b")
    page.evaluate("() => { window.__armed = true; }")

    expect(page.get_by_test_id("card-EQ-B01")).to_be_visible(timeout=10_000)
    page.wait_for_timeout(5500)  # as respostas atrasadas de A ja chegaram (e foram ignoradas)
    assert page.evaluate("window.__leaked") is False, "dados da org A apareceram apos a troca p/ B"
    assert "EQ-001" not in page.locator("#alerts").inner_text()
