"""SPEC-007 · REQ-UX-004: vista 3D do painel no navegador REAL (Playwright + Edge/Chrome com WebGL por software).

Valida geometria, cor, estado, interacao, CSP e degradacao. O WebGL roda por SOFTWARE (SwiftShader): nao mede
desempenho em GPU real nem em celular. `prefers-reduced-motion` e usado de proposito (a renderizacao por
software nao sustenta o pulso continuo do alerta critico); o caminho sem animacao e parte do requisito.
Evidencias (capturas) sao gravadas em docs/evidence/phase-1/.
"""

import os
import time
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np
import pytest
from playwright.sync_api import Browser, BrowserContext, Page, expect, sync_playwright
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
GL_ARGS = [
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
    "--ignore-gpu-blocklist",
    "--enable-webgl",
]
SLOW = 180_000  # ms: renderizacao por software e lenta


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    with sync_playwright() as p:
        instance = p.chromium.launch(channel=CHANNEL, headless=True, args=GL_ARGS)
        yield instance
        instance.close()


@pytest.fixture(scope="module", autouse=True)
def quiet_simulator() -> Iterator[None]:
    compose("stop", "simulator")
    yield
    compose("start", "simulator")


@pytest.fixture(autouse=True)
def controlled_data(quiet_simulator: None) -> None:
    """EQ-001 critico e EQ-002 normal, frescos; EQ-003 nunca recebe dado novo (vira OFFLINE)."""
    feed_equipment("EQ-001", temperature=101.0, vibration=1.0)
    feed_equipment("EQ-002", temperature=40.0, vibration=1.0)
    wait_until(lambda: equipment_status("EQ-001") == "CRITICAL", 20, what="EQ-001 critico")
    wait_until(lambda: equipment_status("EQ-002") == "NORMAL", 20, what="EQ-002 normal")


def _open(
    browser: Browser, quality: str = "baixa", width: int = 1100, height: int = 800
) -> tuple[BrowserContext, Page]:
    context = browser.new_context(
        viewport={"width": width, "height": height}, locale="pt-BR", reduced_motion="reduce"
    )
    page = context.new_page()
    assert BASE_URL is not None
    page.goto(f"{BASE_URL}/panel/?q3d={quality}", wait_until="commit", timeout=SLOW)
    expect(page.get_by_test_id("viewer3d")).to_have_attribute("data-ready", "true", timeout=SLOW)
    # a vista pausa fora da tela (IntersectionObserver): rola ate ela, como o usuario faria
    page.locator(".v3d-stage").scroll_into_view_if_needed(timeout=SLOW)
    expect(page.get_by_test_id("label3d-EQ-001")).to_be_visible(timeout=SLOW)
    # a renderizacao por software pode demorar mais que a janela de frescor (30 s): reaplica os dados
    feed_equipment("EQ-001", temperature=101.0, vibration=1.0)
    feed_equipment("EQ-002", temperature=40.0, vibration=1.0)
    return context, page


@pytest.fixture(scope="module")
def shared(browser: Browser) -> Iterator[Page]:
    """Uma pagina so para os testes que nao alteram dados (cada carga custa alguns segundos)."""
    context, page = _open(browser)
    yield page
    context.close()


@pytest.fixture
def viewer(shared: Page) -> Page:
    before = _frames(shared)
    shared.get_by_test_id("viewer3d-reset").click()
    _wait_new_frame(shared, before)  # a cena ja esta na visao geral quando o teste comeca
    return shared


def _frames(page: Page) -> int:
    return int(page.get_by_test_id("viewer3d").get_attribute("data-frames") or "0")


def _wait_new_frame(page: Page, since: int | None = None) -> None:
    """Espera um quadro NOVO. Passe `since` lido ANTES da acao (o quadro pode sair logo apos o clique)."""
    before = _frames(page) if since is None else since
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline and _frames(page) <= before:
        time.sleep(0.5)
    assert _frames(page) > before, "nenhum quadro novo foi renderizado"


def _stage_image(page: Page, hide_labels: bool = False) -> np.ndarray:
    if hide_labels:
        page.evaluate("document.querySelector('.v3d-labels').style.visibility = 'hidden'")
    try:
        png = page.locator(".v3d-stage").screenshot(timeout=SLOW)
    finally:
        if hide_labels:
            page.evaluate("document.querySelector('.v3d-labels').style.visibility = ''")
    image = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
    assert image is not None
    return image


def _count(image: np.ndarray, predicate: "np.ndarray") -> int:
    return int(np.count_nonzero(predicate))


def test_viewer_renders_one_labelled_machine_per_equipment_with_status_in_text(
    viewer: Page,
) -> None:
    """REQ-UX-004: cena pronta, um rotulo por equipamento, estado em TEXTO e leituras."""
    box = viewer.get_by_test_id("viewer3d")
    expect(box).to_have_attribute("data-machines", "3")
    critical = viewer.get_by_test_id("label3d-EQ-001")
    expect(critical).to_have_attribute("data-status", "CRITICAL", timeout=15_000)
    expect(critical).to_contain_text("Crítico")
    expect(critical).to_contain_text("Compressor de ar 01")
    expect(critical).to_contain_text("Temperatura 101.0 °C")
    expect(viewer.get_by_test_id("label3d-EQ-002")).to_have_attribute("data-status", "NORMAL")
    expect(viewer.get_by_test_id("label3d-EQ-002")).to_contain_text("Normal")
    assert _frames(viewer) >= 1


def test_the_canvas_is_really_rendered_and_status_colors_appear_in_the_scene(viewer: Page) -> None:
    """Pixels reais: cena nao vazia, com variedade, vermelho no critico (EQ-001) e verde no normal (EQ-002)."""
    box = viewer.get_by_test_id("viewer3d")
    expect(viewer.get_by_test_id("label3d-EQ-001")).to_have_attribute(
        "data-status", "CRITICAL", timeout=30_000
    )
    expect(viewer.get_by_test_id("label3d-EQ-002")).to_have_attribute(
        "data-status", "NORMAL", timeout=30_000
    )

    before = _frames(viewer)
    viewer.get_by_test_id("viewer3d-focus-EQ-001").click()
    expect(box).to_have_attribute("data-camera-target", "EQ-001")
    _wait_new_frame(viewer, before)
    image = _stage_image(viewer, hide_labels=True)
    blue, green, red = (
        image[..., 0].astype(int),
        image[..., 1].astype(int),
        image[..., 2].astype(int),
    )
    assert float(image.std()) > 12  # nao e uma tela lisa
    assert len(np.unique(image.reshape(-1, 3), axis=0)) > 2000
    assert (
        _count(image, (red > 190) & (green < 110) & (blue < 110)) >= 30
    )  # sinalizador/anel vermelhos

    before = _frames(viewer)
    viewer.get_by_test_id("viewer3d-focus-EQ-002").click()
    expect(box).to_have_attribute("data-camera-target", "EQ-002")
    _wait_new_frame(viewer, before)
    image = _stage_image(viewer, hide_labels=True)
    blue, green, red = (
        image[..., 0].astype(int),
        image[..., 1].astype(int),
        image[..., 2].astype(int),
    )
    assert (
        _count(image, (green > 150) & (red < 140) & (green - red > 40)) >= 30
    )  # sinalizador/anel verdes


def test_clicking_a_label_focuses_the_camera_and_selects_the_card(viewer: Page) -> None:
    box = viewer.get_by_test_id("viewer3d")
    overview = float(box.get_attribute("data-camera-distance") or "0")
    before = _frames(viewer)

    viewer.get_by_test_id("label3d-EQ-002").click()

    expect(box).to_have_attribute("data-selected", "EQ-002")
    expect(box).to_have_attribute("data-camera-target", "EQ-002")
    card = viewer.get_by_test_id("card-EQ-002")
    expect(card).to_have_attribute("data-selected", "true")
    expect(card).to_be_focused()
    _wait_new_frame(viewer, before)
    assert float(box.get_attribute("data-camera-distance") or "99") < overview  # aproximou


def test_labels_are_native_buttons_reachable_and_activatable_by_keyboard(viewer: Page) -> None:
    label = viewer.get_by_test_id("label3d-EQ-001")
    assert label.evaluate("node => node.tagName") == "BUTTON"

    label.focus()
    expect(label).to_be_focused()
    viewer.keyboard.press("Enter")

    expect(viewer.get_by_test_id("viewer3d")).to_have_attribute("data-selected", "EQ-001")
    expect(viewer.get_by_test_id("card-EQ-001")).to_have_attribute("data-selected", "true")


def test_plan_marker_click_also_focuses_the_3d_camera(viewer: Page) -> None:
    viewer.get_by_test_id("plant-EQ-002").click()

    expect(viewer.get_by_test_id("viewer3d")).to_have_attribute("data-camera-target", "EQ-002")


def test_focus_buttons_and_overview_move_the_camera(viewer: Page) -> None:
    box = viewer.get_by_test_id("viewer3d")
    before = _frames(viewer)
    viewer.get_by_test_id("viewer3d-focus-EQ-003").click()
    expect(box).to_have_attribute("data-camera-target", "EQ-003")
    _wait_new_frame(viewer, before)
    focused = float(box.get_attribute("data-camera-distance") or "99")
    before = _frames(viewer)

    viewer.get_by_test_id("viewer3d-reset").click()

    expect(box).to_have_attribute("data-camera-target", "overview")
    _wait_new_frame(viewer, before)
    assert float(box.get_attribute("data-camera-distance") or "0") > focused


def test_pointer_drag_orbits_the_camera_without_selecting_a_machine(viewer: Page) -> None:
    box = viewer.get_by_test_id("viewer3d")
    stage = viewer.locator(".v3d-stage").bounding_box()
    assert stage is not None
    before = _frames(viewer)

    viewer.mouse.move(stage["x"] + stage["width"] * 0.5, stage["y"] + stage["height"] * 0.85)
    viewer.mouse.down()
    viewer.mouse.move(
        stage["x"] + stage["width"] * 0.62, stage["y"] + stage["height"] * 0.8, steps=6
    )
    viewer.mouse.up()

    deadline = time.monotonic() + 120
    while time.monotonic() < deadline and _frames(viewer) <= before:
        time.sleep(0.5)
    assert _frames(viewer) > before  # a cena foi redesenhada com a nova orbita
    expect(box).to_have_attribute("data-selected", "")  # arrastar nao e clicar


def test_switching_organization_replaces_the_3d_machines(browser: Browser) -> None:
    context, page = _open(browser)
    try:
        page.select_option("#org", "demo-operator-b")

        expect(page.get_by_test_id("label3d-EQ-B01")).to_be_visible(timeout=SLOW)
        expect(page.get_by_test_id("label3d-EQ-001")).to_have_count(0)
        expect(page.get_by_test_id("viewer3d")).to_have_attribute("data-machines", "1")
        expect(page.get_by_test_id("label3d-EQ-B01")).to_contain_text("Equipamento sentinela B01")
    finally:
        context.close()


def test_hostile_equipment_name_is_text_in_the_3d_label_and_never_executes(
    browser: Browser,
) -> None:
    hostile = "<img src=x onerror=window.__xss3=1>"
    with db_engine().begin() as conn:
        conn.execute(text("UPDATE equipment SET name = :n WHERE id = 'EQ-002'"), {"n": hostile})
    context, page = _open(browser)
    try:
        expect(page.get_by_test_id("label3d-EQ-002")).to_contain_text(hostile, timeout=SLOW)

        assert page.locator(".v3d-labels img").count() == 0
        assert page.evaluate("window.__xss3 === undefined")
    finally:
        context.close()
        with db_engine().begin() as conn:
            conn.execute(
                text("UPDATE equipment SET name = 'Bomba centrifuga 02' WHERE id = 'EQ-002'")
            )


def test_viewer_is_marked_stale_but_keeps_the_scene_when_the_api_fails(browser: Browser) -> None:
    context, page = _open(browser)
    try:
        page.route("**/api/v1/**", lambda route: route.abort())

        expect(page.get_by_test_id("viewer3d")).to_have_attribute(
            "data-stale", "true", timeout=30_000
        )
        expect(page.get_by_test_id("label3d-EQ-001")).to_be_visible()  # nao apaga o ultimo estado
    finally:
        context.close()


def test_without_webgl_the_viewer_explains_and_the_rest_of_the_panel_keeps_working(
    browser: Browser,
) -> None:
    context = browser.new_context(viewport={"width": 1100, "height": 800}, reduced_motion="reduce")
    context.add_init_script(
        """
        const original = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function (type, ...rest) {
          if (String(type).startsWith('webgl') || type === 'experimental-webgl') return null;
          return original.call(this, type, ...rest);
        };
        """
    )
    page = context.new_page()
    try:
        assert BASE_URL is not None
        page.goto(BASE_URL + "/panel/", wait_until="commit", timeout=SLOW)

        note = page.get_by_test_id("viewer3d-note")
        expect(note).to_contain_text("WebGL", timeout=30_000)
        expect(page.get_by_test_id("viewer3d")).to_have_attribute("data-unavailable", "true")
        expect(page.get_by_test_id("card-EQ-001")).to_have_attribute(
            "data-status", "CRITICAL", timeout=15_000
        )
        expect(page.get_by_test_id("plant-EQ-001")).to_be_visible()  # planta 2D segue
    finally:
        context.close()


def test_quality_selector_rebuilds_the_scene_with_the_chosen_level(browser: Browser) -> None:
    context, page = _open(browser, quality="baixa")
    try:
        box = page.get_by_test_id("viewer3d")
        expect(box).to_have_attribute("data-quality", "baixa")

        page.get_by_test_id("viewer3d-quality").select_option("media")

        expect(box).to_have_attribute("data-quality", "media", timeout=SLOW)
        expect(page.get_by_test_id("label3d-EQ-001")).to_be_visible(timeout=SLOW)
        expect(box).to_have_attribute("data-machines", "3")
    finally:
        context.close()


def test_no_external_requests_and_no_csp_violations(browser: Browser) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = context.new_page()
    urls: list[str] = []
    messages: list[str] = []
    page.on("request", lambda request: urls.append(request.url))
    page.on("console", lambda message: messages.append(message.text))
    try:
        assert BASE_URL is not None
        page.goto(f"{BASE_URL}/panel/?q3d=baixa", wait_until="commit", timeout=SLOW)
        expect(page.get_by_test_id("label3d-EQ-001")).to_be_visible(timeout=SLOW)
    finally:
        context.close()

    external = [u for u in urls if not u.startswith((BASE_URL or "", "data:", "blob:"))]
    assert external == []
    assert any(u.endswith("/panel/vendor/viewer3d.js") for u in urls)
    assert [m for m in messages if "Content Security Policy" in m] == []


def test_viewer_fits_a_360px_phone_without_horizontal_scroll(browser: Browser) -> None:
    context, page = _open(browser, width=360, height=740)
    try:
        overflow = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        width = page.locator(".v3d-stage").bounding_box()
        assert width is not None
        page.locator(".v3d-stage").scroll_into_view_if_needed()
        page.screenshot(path=str(EVIDENCE / "panel-3d-360.png"))
    finally:
        context.close()

    assert overflow <= 0
    assert width["width"] <= 360


def test_high_quality_evidence_overview_and_close_ups(browser: Browser) -> None:
    """Qualidade ALTA (MSAA 4x, GTAO, bloom, sombras 2048): capturas de evidencia da cena e de cada maquina."""
    context, page = _open(browser, quality="alta", width=1280, height=900)
    try:
        box = page.get_by_test_id("viewer3d")
        expect(box).to_have_attribute("data-quality", "alta")
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        _wait_new_frame(page)
        page.locator(".v3d-stage").screenshot(
            path=str(EVIDENCE / "panel-3d-overview.png"), timeout=SLOW
        )
        for name, equipment in (("compressor", "EQ-001"), ("pump", "EQ-002"), ("motor", "EQ-003")):
            before = _frames(page)
            page.get_by_test_id(f"viewer3d-focus-{equipment}").click()
            expect(box).to_have_attribute("data-camera-target", equipment)
            _wait_new_frame(page, before)
            page.locator(".v3d-stage").screenshot(
                path=str(EVIDENCE / f"panel-3d-{name}.png"), timeout=SLOW
            )
    finally:
        context.close()
