"""SPEC-007/SPEC-010 · REQ-UX-005: vista 3D das alas (UTI e enfermaria) no navegador REAL (Playwright + Edge/Chrome).

Dados SIMULADOS do HACC (relogio-dependentes: alarmes giram a cada 15 s), por isso os testes afirmam so o que e
ESTAVEL: U-03 sempre OFFLINE (mudo), A1-06 sempre UNKNOWN (sem leitura), U-02 sempre NORMAL. WebGL por SOFTWARE
(SwiftShader): valida geometria, cor e comportamento, nao desempenho em GPU real. Capturas de evidencia em
docs/evidence/phase-4/.
"""

import json
import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest
from playwright.sync_api import Browser, BrowserContext, Page, expect, sync_playwright

from tests.integration._stack import BASE_URL, requires_stack

pytestmark = [pytest.mark.e2e, requires_stack]

EVIDENCE = Path(__file__).resolve().parents[2] / "docs/evidence/phase-4"
CHANNEL = os.environ.get("E2E_BROWSER_CHANNEL", "msedge")
GL_ARGS = [
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
    "--ignore-gpu-blocklist",
    "--enable-webgl",
]
SLOW = 180_000
NURSE_A = "demo-nurse-a"
NURSE_B = "demo-nurse-b"
OPERATOR_A = "demo-operator-a"


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    with sync_playwright() as p:
        instance = p.chromium.launch(channel=CHANNEL, headless=True, args=GL_ARGS)
        yield instance
        instance.close()


def _open(
    browser: Browser, token: str = NURSE_A, width: int = 1100, height: int = 800
) -> tuple[BrowserContext, Page]:
    context = browser.new_context(
        viewport={"width": width, "height": height}, locale="pt-BR", reduced_motion="reduce"
    )
    page = context.new_page()
    assert BASE_URL is not None
    page.goto(f"{BASE_URL}/panel/?q3d=baixa", wait_until="commit", timeout=SLOW)
    page.select_option("#org", token, timeout=SLOW)
    return context, page


def _go_to_ward(page: Page, ward: str) -> None:
    expect(page.locator(f'#hacc-ward option[value="{ward}"]')).to_have_count(1, timeout=SLOW)
    page.select_option("#hacc-ward", ward, timeout=SLOW)
    expect(page.get_by_test_id("ward3d")).to_have_attribute("data-ward", ward, timeout=SLOW)
    page.locator("#ward3d .v3d-stage").scroll_into_view_if_needed(
        timeout=SLOW
    )  # a vista pausa fora da tela


@pytest.fixture(scope="module")
def shared(browser: Browser) -> Iterator[Page]:
    context, page = _open(browser)
    _go_to_ward(page, "WARD-UTI")
    expect(page.get_by_test_id("label-ward3d-U-02")).to_be_visible(timeout=SLOW)
    yield page
    context.close()


@pytest.fixture
def ward(shared: Page) -> Page:
    before = _frames(shared)
    shared.get_by_test_id("ward3d-reset").click()
    expect(shared.get_by_test_id("ward3d")).to_have_attribute("data-camera-target", "overview")
    _wait_new_frame(shared, before)
    time.sleep(1.5)  # deixa a camera assentar na visao geral
    return shared


def _frames(page: Page) -> int:
    return int(page.get_by_test_id("ward3d").get_attribute("data-frames") or "0")


def _wait_new_frame(page: Page, since: int | None = None) -> None:
    before = _frames(page) if since is None else since
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline and _frames(page) <= before:
        time.sleep(0.5)
    assert _frames(page) > before, "nenhum quadro novo foi renderizado"


def _distance(page: Page) -> float:
    return float(page.get_by_test_id("ward3d").get_attribute("data-camera-distance") or "0")


def _wait_distance_change(page: Page, previous: float) -> float:
    """Espera a DISTANCIA da camera mudar (um quadro do refresh de 2 s nao prova que a camera andou)."""
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline and abs(_distance(page) - previous) < 0.3:
        time.sleep(0.5)
    assert abs(_distance(page) - previous) >= 0.3, "a camera nao se moveu"
    return _distance(page)


def _stage_image(page: Page, hide_labels: bool = True) -> np.ndarray:
    if hide_labels:
        page.evaluate("document.querySelector('#ward3d .v3d-labels').style.visibility = 'hidden'")
    try:
        png = page.locator("#ward3d .v3d-stage").screenshot(timeout=SLOW)
    finally:
        if hide_labels:
            page.evaluate("document.querySelector('#ward3d .v3d-labels').style.visibility = ''")
    image = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
    assert image is not None
    return image


def test_the_icu_has_one_labelled_bed_per_grid_cell_with_status_in_text(ward: Page) -> None:
    box = ward.get_by_test_id("ward3d")
    expect(box).to_have_attribute("data-machines", "4")
    expect(ward.locator("[data-testid^='label-ward3d-']")).to_have_count(4)
    offline = ward.get_by_test_id("label-ward3d-U-03")  # leito mudo: SEMPRE offline, nunca normal
    expect(offline).to_have_attribute("data-status", "OFFLINE", timeout=15_000)
    expect(offline).to_contain_text("Offline")
    expect(offline).to_contain_text("Ocupado")
    expect(offline).to_contain_text("Sem dados recentes")
    expect(offline).not_to_contain_text("Normal")
    normal = ward.get_by_test_id("label-ward3d-U-02")
    expect(normal).to_have_attribute("data-status", "NORMAL")
    expect(normal).to_contain_text("Normal")


def test_the_scene_is_really_rendered_with_status_colors_and_no_people_labels(ward: Page) -> None:
    """Pixels: cena nao vazia e o anel verde do leito normal aparece; o texto da cena nao cita pessoas."""
    _wait_new_frame(ward)
    image = _stage_image(ward)
    _blue, green, red = (
        image[..., 0].astype(int),
        image[..., 1].astype(int),
        image[..., 2].astype(int),
    )

    assert float(image.std()) > 12
    assert len(np.unique(image.reshape(-1, 3), axis=0)) > 2000
    assert int(np.count_nonzero((green > 150) & (red < 150) & (green - red > 40))) >= 30
    scene_text = ward.locator("#ward3d").inner_text().lower()
    for word in ("paciente", "nome", "cpf", "prontu"):
        assert word not in scene_text


def test_clicking_a_bed_label_focuses_the_camera_and_highlights_the_2d_bed(ward: Page) -> None:
    box = ward.get_by_test_id("ward3d")
    overview = _distance(ward)

    ward.get_by_test_id("label-ward3d-U-02").click()

    expect(box).to_have_attribute("data-selected", "U-02")
    expect(box).to_have_attribute("data-camera-target", "U-02")
    expect(ward.get_by_test_id("bed-U-02")).to_have_attribute("data-selected", "true")
    assert _wait_distance_change(ward, overview) < overview


def test_bed_labels_are_native_buttons_operable_by_keyboard(ward: Page) -> None:
    label = ward.get_by_test_id("label-ward3d-U-04")
    assert label.evaluate("node => node.tagName") == "BUTTON"

    label.focus()
    expect(label).to_be_focused()
    ward.keyboard.press("Enter")

    expect(ward.get_by_test_id("ward3d")).to_have_attribute("data-selected", "U-04")
    assert "UTI 04" in (label.get_attribute("aria-label") or "")


def test_focus_buttons_and_overview_move_the_camera(ward: Page) -> None:
    box = ward.get_by_test_id("ward3d")
    overview = _distance(ward)
    ward.get_by_test_id("ward3d-focus-U-01").click()
    expect(box).to_have_attribute("data-camera-target", "U-01")
    focused = _wait_distance_change(ward, overview)
    assert focused < overview

    ward.get_by_test_id("ward3d-reset").click()

    expect(box).to_have_attribute("data-camera-target", "overview")
    assert _wait_distance_change(ward, focused) > focused


def test_switching_to_the_infirmary_rebuilds_the_room_with_six_beds(browser: Browser) -> None:
    context, page = _open(browser)
    try:
        _go_to_ward(page, "WARD-A1")
        box = page.get_by_test_id("ward3d")
        expect(box).to_have_attribute("data-machines", "6", timeout=SLOW)
        expect(page.get_by_test_id("label-ward3d-A1-06")).to_have_attribute(
            "data-status", "UNKNOWN", timeout=SLOW
        )
        expect(page.get_by_test_id("label-ward3d-A1-06")).to_contain_text("sem leitura")
        expect(page.get_by_test_id("label-ward3d-A1-06")).not_to_contain_text("Normal")

        page.select_option("#hacc-ward", "WARD-UTI")

        expect(box).to_have_attribute("data-ward", "WARD-UTI", timeout=SLOW)
        expect(box).to_have_attribute("data-machines", "4", timeout=SLOW)
        expect(page.get_by_test_id("label-ward3d-A1-06")).to_have_count(0)
    finally:
        context.close()


def test_other_organization_only_sees_its_own_ward_in_3d(browser: Browser) -> None:
    context, page = _open(browser)
    try:
        _go_to_ward(page, "WARD-UTI")
        page.select_option("#org", NURSE_B)

        expect(page.get_by_test_id("ward3d")).to_have_attribute(
            "data-ward", "WARD-B1", timeout=SLOW
        )
        expect(page.get_by_test_id("label-ward3d-B-01")).to_be_visible(timeout=SLOW)
        expect(page.get_by_test_id("label-ward3d-U-01")).to_have_count(0)
        expect(page.get_by_test_id("ward3d")).to_have_attribute("data-machines", "2")
    finally:
        context.close()


def test_a_user_without_hacc_scope_gets_no_3d_ward_and_no_second_webgl_context(
    browser: Browser,
) -> None:
    context, page = _open(browser, OPERATOR_A)
    try:
        expect(page.get_by_test_id("hacc-msg")).to_contain_text("hacc:read", timeout=SLOW)

        expect(page.locator("#ward3d-section")).to_be_hidden()
        expect(page.locator("#ward3d canvas")).to_have_count(0)
        assert page.locator("canvas").count() == 1  # so a vista dos equipamentos
    finally:
        context.close()


def test_hostile_text_in_the_ward_data_is_rendered_as_text_in_the_3d_labels(
    browser: Browser,
) -> None:
    dialogs: list[str] = []
    ward = '[{"ward_id":"W","name":"W","bed_count":1,"status":"ALERT","alert_count":1}]'
    beds = (
        '{"ward":{"ward_id":"W","name":"<img src=x onerror=alert(2)>","width":1,"height":1},'
        '"evaluated_at":"2026-10-20T12:00:00Z","status":"ALERT","beds":[{"bed_id":"B",'
        '"label":"<script>alert(3)</script>","x":1,"y":1,"occupied":true,"status":"ALERT",'
        '"observed_at":"2026-10-20T12:00:00Z","alerts":[{"severity":"ALERT","rule":"<b>x</b>"}]}]}'
    )
    context = browser.new_context(viewport={"width": 1100, "height": 800}, reduced_motion="reduce")
    page = context.new_page()
    page.on("dialog", lambda d: dialogs.append(d.message))
    page.route(
        "**/api/v1/hacc/wards",
        lambda r: r.fulfill(status=200, content_type="application/json", body=ward),
    )
    page.route(
        "**/api/v1/hacc/wards/W/beds",
        lambda r: r.fulfill(status=200, content_type="application/json", body=beds),
    )
    try:
        assert BASE_URL is not None
        page.goto(f"{BASE_URL}/panel/?q3d=baixa", wait_until="commit", timeout=SLOW)
        page.select_option("#org", NURSE_A, timeout=SLOW)

        label = page.get_by_test_id("label-ward3d-B")
        expect(label).to_contain_text("<script>alert(3)</script>", timeout=SLOW)
        expect(label).to_contain_text(
            "<b>x</b>"
        )  # regra desconhecida: mostrada literalmente, como texto
        assert page.locator("#ward3d img, #ward3d script, #ward3d b").count() == 0
        assert dialogs == []
    finally:
        context.close()


def test_the_3d_ward_stays_but_is_marked_stale_when_hacc_is_unavailable(browser: Browser) -> None:
    context, page = _open(browser)
    try:
        _go_to_ward(page, "WARD-UTI")
        expect(page.get_by_test_id("label-ward3d-U-02")).to_be_visible(timeout=SLOW)

        page.route(
            "**/api/v1/hacc/**",
            lambda r: r.fulfill(status=503, content_type="application/json", body='{"detail":"x"}'),
        )

        expect(page.get_by_test_id("ward3d")).to_have_attribute("data-stale", "true", timeout=SLOW)
        expect(
            page.get_by_test_id("label-ward3d-U-02")
        ).to_be_visible()  # nao apaga o ultimo estado
    finally:
        context.close()


def test_without_webgl_the_ward_explains_and_the_2d_plan_keeps_working(browser: Browser) -> None:
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
        page.select_option("#org", NURSE_A, timeout=SLOW)

        expect(page.get_by_test_id("ward3d-note")).to_contain_text("WebGL", timeout=SLOW)
        expect(page.get_by_test_id("ward3d")).to_have_attribute("data-unavailable", "true")
        expect(page.get_by_test_id("bed-A1-05")).to_be_visible(
            timeout=SLOW
        )  # planta 2D dos leitos segue
    finally:
        context.close()


def test_no_external_requests_no_csp_violations_and_fits_a_360px_phone(browser: Browser) -> None:
    context = browser.new_context(viewport={"width": 360, "height": 740}, reduced_motion="reduce")
    page = context.new_page()
    urls: list[str] = []
    messages: list[str] = []
    page.on("request", lambda request: urls.append(request.url))
    page.on("console", lambda message: messages.append(message.text))
    try:
        assert BASE_URL is not None
        page.goto(f"{BASE_URL}/panel/?q3d=baixa", wait_until="commit", timeout=SLOW)
        page.select_option("#org", NURSE_A, timeout=SLOW)
        _go_to_ward(page, "WARD-UTI")
        expect(page.get_by_test_id("label-ward3d-U-02")).to_be_visible(timeout=SLOW)
        overflow = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(EVIDENCE / "panel-3d-ward-360.png"))
    finally:
        context.close()

    assert overflow <= 0
    assert [u for u in urls if not u.startswith((BASE_URL or "", "data:", "blob:"))] == []
    assert [m for m in messages if "Content Security Policy" in m] == []


def test_high_quality_evidence_of_the_icu_and_the_infirmary(browser: Browser) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = context.new_page()
    try:
        assert BASE_URL is not None
        page.goto(f"{BASE_URL}/panel/?q3d=alta", wait_until="commit", timeout=SLOW)
        page.select_option("#org", NURSE_A, timeout=SLOW)
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        for name, ward_id in (("uti", "WARD-UTI"), ("enfermaria", "WARD-A1")):
            _go_to_ward(page, ward_id)
            box = page.get_by_test_id("ward3d")
            expect(box).to_have_attribute("data-quality", "alta")
            expect(box).to_have_attribute(
                "data-machines", "4" if name == "uti" else "6", timeout=SLOW
            )
            _wait_new_frame(page)
            page.locator("#ward3d .v3d-stage").screenshot(
                path=str(EVIDENCE / f"panel-3d-{name}.png"), timeout=SLOW
            )
        before = _frames(page)
        page.get_by_test_id("ward3d-focus-A1-05").click()
        expect(page.get_by_test_id("ward3d")).to_have_attribute("data-camera-target", "A1-05")
        _wait_new_frame(page, before)
        page.locator("#ward3d .v3d-stage").screenshot(
            path=str(EVIDENCE / "panel-3d-leito.png"), timeout=SLOW
        )
    finally:
        context.close()


# --- REQ-HACC-007 (D-054): leito BLOQUEADO (HACC real: `unavailable`) ----------------------------------


def _mock_hacc_with_blocked(page: Page, count: int = 12) -> None:
    wards = [
        {"ward_id": "W", "name": "Ala W", "bed_count": count, "status": "NORMAL", "alert_count": 0}
    ]
    beds: list[dict[str, Any]] = [
        {
            "bed_id": f"B{i:02d}", "label": f"B{i:02d}", "x": (i - 1) % 5 + 1, "y": (i - 1) // 5 + 1,
            "occupied": True, "status": "BLOCKED" if i == 3 else "NORMAL",
            "observed_at": "2026-10-26T12:00:00Z", "alerts": [],
        }
        for i in range(1, count + 1)
    ]  # fmt: skip
    detail = {
        "ward": {"ward_id": "W", "name": "Ala W", "width": 5, "height": 3},
        "evaluated_at": "2026-10-26T12:00:00Z",
        "status": "NORMAL",
        "beds": beds,
    }
    page.route(
        "**/api/v1/hacc/wards",
        lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(wards)),
    )
    page.route(
        "**/api/v1/hacc/wards/W/beds",
        lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(detail)),
    )


def test_a_blocked_bed_is_shown_as_blocked_in_text_in_2d_and_3d_and_never_as_normal(
    browser: Browser,
) -> None:
    context = browser.new_context(viewport={"width": 1100, "height": 800}, reduced_motion="reduce")
    page = context.new_page()
    _mock_hacc_with_blocked(page)
    try:
        assert BASE_URL is not None
        page.goto(f"{BASE_URL}/panel/?q3d=baixa", wait_until="commit", timeout=SLOW)
        page.select_option("#org", NURSE_A, timeout=SLOW)

        card = page.get_by_test_id("bed-B03")  # planta 2D
        expect(card).to_have_attribute("data-status", "BLOCKED", timeout=SLOW)
        expect(card).to_contain_text("Bloqueado")
        expect(card).not_to_contain_text("Normal")
        expect(page.get_by_test_id("hacc-summary")).to_contain_text("Normal")  # ala nao piora

        page.locator("#ward3d .v3d-stage").scroll_into_view_if_needed(timeout=SLOW)
        label = page.get_by_test_id("label-ward3d-B03")  # vista 3D
        expect(label).to_have_attribute("data-status", "BLOCKED", timeout=SLOW)
        expect(label).to_contain_text("Bloqueado")
        expect(label).not_to_contain_text("Normal")
        expect(page.get_by_test_id("label-ward3d-B04")).to_have_attribute("data-status", "NORMAL")
        expect(page.get_by_test_id("ward3d")).to_have_attribute("data-dense", "true")  # 12 leitos
    finally:
        context.close()
