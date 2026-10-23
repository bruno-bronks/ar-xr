"""SPEC-007 · REQ-UX-001, REQ-UX-003: painel web 2D (cartoes + planta) no navegador REAL (Playwright + Microsoft Edge instalado).

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
EVIDENCE_P3 = Path(__file__).resolve().parents[2] / "docs/evidence/phase-3"
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


def _shot(page: Page, name: str, folder: Path = EVIDENCE) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(folder / name), full_page=True)


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


# --- Assistente no painel (SPEC-009, REQ-UX-002, REQ-AI-001, REQ-AI-004, REQ-AI-006) ------------------------


def _ask(page: Page, question: str, equipment: str = "EQ-001") -> None:
    expect(page.get_by_test_id("card-" + equipment)).to_be_visible(timeout=10_000)
    page.select_option("#assistant-equipment", equipment)
    page.fill("#assistant-question", question)
    page.click("#assistant-submit")


def test_assistant_answers_with_sources_confidence_and_rule_based_state(page: Page) -> None:
    _ask(page, "Por que a temperatura do compressor está alta?")

    result = page.get_by_test_id("assistant-result")
    expect(result).to_be_visible(timeout=10_000)
    expect(page.get_by_test_id("assistant-outcome")).to_have_attribute("data-outcome", "answered")
    expect(page.get_by_test_id("assistant-source").first).to_contain_text("DOC-COMP-001")
    expect(page.get_by_test_id("assistant-source").first).to_contain_text("Temperatura elevada")
    expect(result).to_contain_text("Confiança")
    expect(result).to_contain_text("Estado pelas regras: CRITICAL")  # EQ-001 critico nestes testes
    expect(
        page.get_by_test_id("assistant-review")
    ).to_be_visible()  # estado critico => revisao humana
    expect(page.locator("#assistant-submit")).to_be_enabled()
    _shot(page, "panel-assistant-answer.png", EVIDENCE_P3)


def test_assistant_refuses_physical_actions_in_the_ui(page: Page) -> None:
    _ask(page, "Desligue o compressor agora")

    expect(page.get_by_test_id("assistant-outcome")).to_have_attribute(
        "data-outcome", "refused", timeout=10_000
    )
    expect(page.get_by_test_id("assistant-result")).to_contain_text("apenas informativo")
    expect(page.get_by_test_id("assistant-source")).to_have_count(0)
    _shot(page, "panel-assistant-refused.png", EVIDENCE_P3)


def test_assistant_output_is_rendered_as_text_never_as_html(page: Page) -> None:
    dialogs: list[str] = []
    page.on("dialog", lambda d: dialogs.append(d.message))

    def hostile(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=(
                '{"outcome":"answered","answer":"<img src=x onerror=alert(1)> <b>negrito</b>",'
                '"confidence":"high","sources":[{"document_id":"D","chunk_id":"D#1",'
                '"title":"<script>alert(2)</script>","section":"<i>s</i>","version":"1",'
                '"excerpt":"<img src=x onerror=alert(3)>"}],"human_review_required":false,'
                '"provider":"extractive","fallback_used":false,"refusal_reason":null,'
                '"live_state":{"status":"NORMAL","alerts":[]}}'
            ),
        )

    page.route("**/api/v1/assistant/questions", hostile)
    _ask(page, "qualquer pergunta")

    result = page.get_by_test_id("assistant-result")
    expect(result).to_contain_text("<img src=x onerror=alert(1)>", timeout=10_000)
    expect(result.locator("img, script, b, i")).to_have_count(0)
    assert dialogs == []


def test_assistant_errors_are_visible_and_not_silent(page: Page) -> None:
    expect(page.get_by_test_id("card-EQ-001")).to_be_visible(timeout=10_000)
    page.route(
        "**/api/v1/assistant/questions",
        lambda route: route.fulfill(
            status=429, content_type="application/json", body='{"detail":"rate limit exceeded"}'
        ),
    )
    _ask(page, "Por que a temperatura está alta?")

    expect(page.get_by_test_id("assistant-error")).to_be_visible(timeout=10_000)
    expect(page.get_by_test_id("assistant-error")).to_contain_text("limite")
    expect(page.get_by_test_id("assistant-result")).to_be_hidden()


def test_switching_organization_clears_the_assistant_and_its_equipment_list(page: Page) -> None:
    _ask(page, "Por que a temperatura do compressor está alta?")
    expect(page.get_by_test_id("assistant-result")).to_be_visible(timeout=10_000)

    page.select_option("#org", "demo-operator-b")

    expect(page.get_by_test_id("assistant-result")).to_be_hidden(timeout=10_000)
    expect(page.locator("#assistant-equipment option")).to_have_text(
        ["EQ-B01 · Equipamento sentinela B01"], timeout=10_000
    )
    expect(page.locator("#assistant-question")).to_have_value("")


def test_assistant_form_fits_a_360px_phone(browser: Browser) -> None:
    assert BASE_URL is not None
    context = browser.new_context(viewport={"width": 360, "height": 740})
    page = context.new_page()
    page.goto(BASE_URL + "/panel/")
    _ask(page, "Por que a temperatura do compressor está alta?")
    expect(page.get_by_test_id("assistant-result")).to_be_visible(timeout=10_000)

    overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    context.close()

    assert overflow <= 0


# --- HACC Spatial: planta 2D de leitos (SPEC-010, REQ-HACC-006) ---------------------------------

EVIDENCE_P4 = Path(__file__).resolve().parents[2] / "docs/evidence/phase-4"


def _nurse(page: Page, token: str = "demo-nurse-a") -> None:  # noqa: S107 - token demo publico
    page.select_option("#org", token)


def test_nurse_sees_the_ward_floor_plan_with_status_text_and_icon(page: Page) -> None:
    _nurse(page)

    plan = page.get_by_test_id("hacc-plan")
    expect(page.get_by_test_id("bed-A1-05")).to_be_visible(timeout=15_000)
    expect(page.locator("#hacc-ward option")).to_have_text(
        ["WARD-A1 · Ala A - Clínica (demo)", "WARD-UTI · UTI (demo)"]
    )
    expect(page.locator("[data-testid^='bed-']")).to_have_count(6)
    expect(page.get_by_test_id("bed-A1-05")).to_have_attribute("data-status", "NORMAL")
    expect(page.get_by_test_id("bed-A1-05")).to_contain_text("Normal")
    unknown = page.get_by_test_id("bed-A1-06")  # leito sem nenhuma leitura
    expect(unknown).to_have_attribute("data-status", "UNKNOWN")
    expect(unknown).to_contain_text("Desconhecido")
    expect(unknown).to_contain_text("sem leitura")
    expect(unknown).not_to_contain_text("Normal")
    expect(page.get_by_test_id("hacc-msg")).to_be_hidden()
    expect(plan).to_have_attribute("data-stale", "false")
    EVIDENCE_P4.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(EVIDENCE_P4 / "panel-hacc-ward.png"), full_page=True)


def test_silent_bed_is_offline_in_the_icu_ward(page: Page) -> None:
    _nurse(page)
    expect(page.get_by_test_id("bed-A1-05")).to_be_visible(timeout=15_000)

    page.select_option("#hacc-ward", "WARD-UTI")

    silent = page.get_by_test_id("bed-U-03")
    expect(silent).to_have_attribute("data-status", "OFFLINE", timeout=10_000)
    expect(silent).to_contain_text("Offline")
    expect(silent).to_contain_text("Sem dados recentes")
    expect(page.locator("[data-testid^='bed-']")).to_have_count(4)


def test_user_without_hacc_scope_sees_a_notice_and_no_beds(page: Page) -> None:
    expect(page.get_by_test_id("card-EQ-001")).to_be_visible(timeout=10_000)  # operador A (padrao)

    notice = page.get_by_test_id("hacc-msg")
    expect(notice).to_be_visible(timeout=10_000)
    expect(notice).to_contain_text("Sem permissão")
    expect(page.locator("[data-testid^='bed-']")).to_have_count(0)
    expect(page.locator("#hacc-ward option")).to_have_count(0)


def test_org_b_nurse_only_sees_its_own_ward_and_switching_clears_the_plan(page: Page) -> None:
    _nurse(page, "demo-nurse-a")
    expect(page.get_by_test_id("bed-A1-05")).to_be_visible(timeout=15_000)

    _nurse(page, "demo-nurse-b")

    expect(page.get_by_test_id("bed-B-01")).to_be_visible(timeout=15_000)
    expect(page.locator("#hacc-ward option")).to_have_text(["WARD-B1 · Ala B1 sentinela (demo)"])
    expect(page.get_by_test_id("bed-A1-05")).to_have_count(0)
    expect(page.locator("[data-testid^='bed-']")).to_have_count(2)


def test_hacc_text_is_rendered_as_text_never_as_html(page: Page) -> None:
    dialogs: list[str] = []
    page.on("dialog", lambda d: dialogs.append(d.message))
    ward = (
        '[{"ward_id":"W","name":"<img src=x onerror=alert(1)>","bed_count":1,'
        '"status":"ALERT","alert_count":1}]'
    )
    beds = (
        '{"ward":{"ward_id":"W","name":"<img src=x onerror=alert(2)>","width":1,"height":1},'
        '"evaluated_at":"2026-10-20T12:00:00Z","status":"ALERT","beds":[{"bed_id":"B",'
        '"label":"<script>alert(3)</script>","x":1,"y":1,"occupied":true,"status":"ALERT",'
        '"observed_at":"2026-10-20T12:00:00Z","alerts":[{"severity":"ALERT","rule":"<b>x</b>"}]}]}'
    )
    page.route(
        "**/api/v1/hacc/wards",
        lambda r: r.fulfill(status=200, content_type="application/json", body=ward),
    )
    page.route(
        "**/api/v1/hacc/wards/W/beds",
        lambda r: r.fulfill(status=200, content_type="application/json", body=beds),
    )
    _nurse(page)

    plan = page.get_by_test_id("hacc-plan")
    expect(plan).to_contain_text("<script>alert(3)</script>", timeout=15_000)
    expect(page.locator("#hacc-section img, #hacc-section script, #hacc-section b")).to_have_count(
        0
    )
    assert dialogs == []


def test_hacc_unavailable_is_visible_and_keeps_the_last_plan_marked_stale(page: Page) -> None:
    _nurse(page)
    expect(page.get_by_test_id("bed-A1-05")).to_be_visible(timeout=15_000)

    page.route(
        "**/api/v1/hacc/**",
        lambda r: r.fulfill(
            status=503, content_type="application/json", body='{"detail":"hacc source unavailable"}'
        ),
    )

    expect(page.get_by_test_id("hacc-msg")).to_contain_text("indisponível", timeout=15_000)
    expect(page.get_by_test_id("bed-A1-05")).to_be_visible()
    expect(page.get_by_test_id("hacc-plan")).to_have_attribute("data-stale", "true")


def test_hacc_plan_has_no_csp_violations_and_fits_a_360px_phone(browser: Browser) -> None:
    assert BASE_URL is not None
    context = browser.new_context(viewport={"width": 360, "height": 740})
    page = context.new_page()
    messages: list[str] = []
    page.on("console", lambda m: messages.append(m.text))
    page.goto(BASE_URL + "/panel/")
    _nurse(page)
    expect(page.get_by_test_id("bed-A1-05")).to_be_visible(timeout=15_000)

    overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    context.close()

    assert overflow <= 0
    assert [m for m in messages if "Content Security Policy" in m] == []


# --- REQ-UX-003: planta 2D dos equipamentos ---------------------------------------------------------


def test_floor_plan_places_each_equipment_with_status_text_icon_and_color_attribute(
    page: Page,
) -> None:
    """REQ-UX-003: marcador por equipamento, estado em texto + icone + data-status (nunca so cor)."""
    plant = page.get_by_test_id("plant")
    critical = page.get_by_test_id("plant-EQ-001")
    expect(critical).to_have_attribute("data-status", "CRITICAL", timeout=10_000)
    expect(critical).to_contain_text("Crítico")
    expect(critical).to_contain_text("Compressor de ar 01")
    normal = page.get_by_test_id("plant-EQ-002")
    expect(normal).to_have_attribute("data-status", "NORMAL")
    expect(normal).to_contain_text("Normal")
    expect(page.locator("[data-testid^='plant-EQ-']")).to_have_count(3)
    expect(plant).to_have_attribute("data-stale", "false")
    _shot(page, "panel-floorplan.png")


def test_floor_plan_marks_silent_equipment_offline_never_normal(page: Page) -> None:
    marker = page.get_by_test_id("plant-EQ-003")

    expect(marker).to_have_attribute("data-status", "OFFLINE", timeout=60_000)
    expect(marker).to_contain_text("Offline")
    expect(marker).not_to_contain_text("Normal")


def test_clicking_or_pressing_enter_on_a_marker_goes_to_its_card(page: Page) -> None:
    expect(page.get_by_test_id("plant-EQ-002")).to_be_visible(timeout=10_000)

    page.get_by_test_id("plant-EQ-002").click()
    card = page.get_by_test_id("card-EQ-002")
    expect(card).to_have_attribute("data-selected", "true")
    expect(card).to_be_focused()

    page.get_by_test_id("plant-EQ-001").focus()
    page.keyboard.press("Enter")
    expect(page.get_by_test_id("card-EQ-001")).to_have_attribute("data-selected", "true")
    expect(page.get_by_test_id("card-EQ-002")).not_to_have_attribute("data-selected", "true")


def test_markers_are_keyboard_reachable_buttons_with_an_accessible_name(page: Page) -> None:
    marker = page.get_by_test_id("plant-EQ-001")
    expect(marker).to_be_visible(timeout=10_000)

    assert (
        marker.evaluate("node => node.tagName") == "BUTTON"
    )  # botao nativo: foco e Enter/Espaco de graca
    marker.focus()
    expect(marker).to_be_focused()
    label = marker.get_attribute("aria-label") or ""
    assert "Compressor de ar 01" in label
    assert "Crítico" in label


def test_floor_plan_follows_the_selected_organization_and_clears_on_switch(page: Page) -> None:
    expect(page.get_by_test_id("plant-EQ-001")).to_be_visible(timeout=10_000)

    page.select_option("#org", "demo-operator-b")

    expect(page.get_by_test_id("plant-EQ-B01")).to_be_visible(timeout=10_000)
    expect(page.get_by_test_id("plant-EQ-001")).to_have_count(0)
    expect(page.get_by_test_id("plant")).not_to_contain_text("Compressor")


def test_equipment_without_a_position_is_listed_aside_not_dropped(page: Page) -> None:
    with db_engine().begin() as conn:
        conn.execute(
            text(
                "INSERT INTO equipment (id, org_id, name, type, location, marker_id, "
                "offline_after_seconds) VALUES ('EQ-ZZ9', 'org-a', 'Sem posicao', 'Teste', "
                "'Galpao Z', 'QR-EQ-ZZ9', 30)"
            )
        )
    try:
        page.reload()
        unplaced = page.get_by_test_id("plant-unplaced")
        expect(unplaced).to_contain_text("EQ-ZZ9", timeout=10_000)
        expect(page.get_by_test_id("plant-EQ-ZZ9")).to_have_count(0)  # nao inventa posicao
    finally:
        with db_engine().begin() as conn:
            conn.execute(text("DELETE FROM equipment WHERE id = 'EQ-ZZ9'"))


def test_floor_plan_renders_hostile_names_as_text_and_never_executes(page: Page) -> None:
    hostile = "<img src=x onerror=window.__xss2=1>"
    with db_engine().begin() as conn:
        conn.execute(text("UPDATE equipment SET name = :n WHERE id = 'EQ-002'"), {"n": hostile})
    try:
        page.reload()
        marker = page.get_by_test_id("plant-EQ-002")
        expect(marker).to_contain_text(hostile, timeout=10_000)

        assert page.locator("[data-testid='plant'] img").count() == 0
        assert page.evaluate("window.__xss2 === undefined")
    finally:
        with db_engine().begin() as conn:
            conn.execute(
                text("UPDATE equipment SET name = 'Bomba centrifuga 02' WHERE id = 'EQ-002'")
            )


def test_floor_plan_stays_but_is_marked_stale_when_the_api_fails(page: Page) -> None:
    expect(page.get_by_test_id("plant-EQ-001")).to_be_visible(timeout=10_000)

    page.route("**/api/v1/**", lambda route: route.abort())

    expect(page.get_by_test_id("plant")).to_have_attribute("data-stale", "true", timeout=10_000)
    expect(page.get_by_test_id("plant-EQ-001")).to_be_visible()  # nao apaga o ultimo estado


def test_floor_plan_fits_a_360px_phone_without_csp_violations(browser: Browser) -> None:
    assert BASE_URL is not None
    context = browser.new_context(viewport={"width": 360, "height": 740})
    page = context.new_page()
    messages: list[str] = []
    page.on("console", lambda m: messages.append(m.text))
    page.goto(BASE_URL + "/panel/")
    expect(page.get_by_test_id("plant-EQ-001")).to_be_visible(timeout=10_000)

    overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    _shot(page, "panel-floorplan-360.png")
    context.close()

    assert overflow <= 0
    assert [m for m in messages if "Content Security Policy" in m] == []
