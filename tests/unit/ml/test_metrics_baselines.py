"""SPEC-011 · REQ-CV-003: estatistica da comparacao e baselines sem aprendizado."""

import math

import numpy as np
import pytest
from spatial_cv.baselines import decode_qr, lamp_state_by_color
from spatial_cv.metrics import Rate, mcnemar_exact, paired_verdict, wilson_interval
from spatial_cv.scene import render_scene
from spatial_cv.truth import EQUIPMENT_IDS, LAMP_CLASS, LAMP_STATUSES
from spatial_domain.status import Status


def test_wilson_matches_known_values() -> None:
    lo, hi = wilson_interval(5, 10)
    assert (lo, hi) == pytest.approx((0.2366, 0.7634), abs=1e-3)
    lo, hi = wilson_interval(0, 10)
    assert lo == 0.0
    assert hi == pytest.approx(0.2775, abs=1e-3)
    lo, hi = wilson_interval(10, 10)
    assert hi == pytest.approx(1.0)
    assert lo == pytest.approx(0.7225, abs=1e-3)


def test_wilson_edge_cases_and_validation() -> None:
    assert wilson_interval(0, 0) == (0.0, 1.0)
    with pytest.raises(ValueError, match="successes"):
        wilson_interval(11, 10)
    with pytest.raises(ValueError, match="successes"):
        wilson_interval(-1, 10)


def test_wilson_interval_narrows_with_more_data_and_contains_the_estimate() -> None:
    small = wilson_interval(8, 10)
    large = wilson_interval(80, 100)

    assert large[1] - large[0] < small[1] - small[0]
    for (lo, hi), p in ((small, 0.8), (large, 0.8)):
        assert lo <= p <= hi


def test_mcnemar_exact_known_values() -> None:
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(5, 5) == 1.0
    assert mcnemar_exact(3, 0) == pytest.approx(0.25)
    assert mcnemar_exact(0, 10) == pytest.approx(2 / 1024)
    assert mcnemar_exact(1, 9) == pytest.approx(2 * 11 / 1024)
    assert mcnemar_exact(9, 1) == mcnemar_exact(1, 9)  # simetrico
    with pytest.raises(ValueError, match="non-negative"):
        mcnemar_exact(-1, 2)


def test_mcnemar_p_is_never_above_one_and_matches_the_binomial_tail() -> None:
    for a in range(0, 12):
        for b in range(0, 12):
            p = mcnemar_exact(a, b)
            assert 0.0 <= p <= 1.0
            n = a + b
            if n:
                tail = sum(math.comb(n, i) for i in range(min(a, b) + 1)) / 2**n
                assert p == pytest.approx(min(1.0, 2 * tail))


def test_verdict_only_claims_superiority_with_significance() -> None:
    assert "sem diferença detectável" in paired_verdict(4, 2, "QR", "YOLO")
    assert "sem diferença detectável" in paired_verdict(0, 0, "QR", "YOLO")
    verdict = paired_verdict(1, 20, "QR", "YOLO")
    assert verdict.startswith("YOLO é melhor")
    assert paired_verdict(20, 1, "QR", "YOLO").startswith("QR é melhor")


def test_rate_text_and_nan_for_empty() -> None:
    assert Rate(27, 30).text().startswith("90% (27/30; IC95 ")
    assert Rate(0, 0).text() == "—"
    assert math.isnan(Rate(0, 0).value)


# --- baselines ---------------------------------------------------------------------------------


def test_decode_qr_returns_none_for_images_without_a_code() -> None:
    blank = np.full((480, 640, 3), 127, np.uint8)
    noise = np.random.default_rng(0).integers(0, 255, size=(480, 640, 3), dtype=np.uint8)

    assert decode_qr(blank) is None
    assert decode_qr(noise) is None


def test_decode_qr_reads_the_marker_on_a_clean_scene() -> None:
    hits = 0
    for k in range(9):
        scene = render_scene(5000 + k, "clean", EQUIPMENT_IDS[k % 3], LAMP_STATUSES[k % 3])
        hits += decode_qr(scene.image) == scene.truth.qr_text

    assert hits >= 6


def test_color_baseline_finds_a_lamp_on_plain_backgrounds() -> None:
    for status, cls in LAMP_CLASS.items():
        image = np.full((480, 640, 3), 140, np.uint8)
        bgr = {
            Status.NORMAL: (60, 200, 40),
            Status.WARNING: (0, 165, 255),
            Status.CRITICAL: (30, 30, 225),
        }[status]
        import cv2

        cv2.circle(image, (300, 200), 14, bgr, -1)

        assert lamp_state_by_color(image) == cls


def test_color_baseline_ignores_non_circular_and_tiny_or_huge_blobs() -> None:
    import cv2

    image = np.full((480, 640, 3), 140, np.uint8)
    cv2.rectangle(image, (50, 50), (250, 70), (30, 30, 225), -1)  # faixa vermelha: aspecto ruim
    cv2.circle(image, (400, 300), 2, (30, 30, 225), -1)  # pequena demais
    cv2.circle(image, (500, 100), 80, (60, 200, 40), -1)  # grande demais

    assert lamp_state_by_color(image) is None


def test_color_baseline_is_fooled_by_a_bigger_decoy_which_is_why_it_is_only_a_baseline() -> None:
    import cv2

    image = np.full((480, 640, 3), 140, np.uint8)
    cv2.circle(image, (300, 200), 12, (30, 30, 225), -1)  # lampada vermelha real (critica)
    cv2.circle(image, (100, 400), 20, (60, 200, 40), -1)  # bolha verde maior (distrator)

    assert lamp_state_by_color(image) == "lamp_normal"
