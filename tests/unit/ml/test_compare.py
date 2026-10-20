"""SPEC-011 · REQ-CV-003 (e REQ-CV-002, tabelas do relatorio): agregacao da comparacao (QR x YOLO x baseline x simulador)."""

import pytest
from spatial_cv.compare import (
    ImageResult,
    by_condition,
    confusion,
    paired,
    qr_ok,
    qr_wrong,
    render_comparison,
    yolo_id_ok,
    yolo_state_ok,
)


def _r(
    condition: str = "clean",
    *,
    qr: str | None = "QR-EQ-001",
    yolo_type: str | None = "compressor",
    yolo_state: str | None = "lamp_normal",
    hsv: str | None = "lamp_normal",
    visible: bool = True,
) -> ImageResult:
    return ImageResult(
        condition, "compressor", "QR-EQ-001", "lamp_normal", visible, qr, yolo_type, yolo_state, hsv
    )


def test_paired_counts_partition_the_images() -> None:
    rows = [
        _r(),  # ambos
        _r(qr=None),  # so YOLO
        _r(yolo_type="pump"),  # so QR
        _r(qr="X", yolo_type=None),  # nenhum
    ]

    p = paired(rows, qr_ok, yolo_id_ok)

    assert (p.both, p.only_a, p.only_b, p.neither) == (1, 1, 1, 1)
    assert p.a.successes == 2
    assert p.b.successes == 2
    assert p.either.successes == 3
    assert p.both + p.only_a + p.only_b + p.neither == len(rows)


def test_wrong_qr_reads_are_counted_apart_from_misses() -> None:
    assert qr_wrong(_r(qr="QR-EQ-002"))
    assert not qr_wrong(_r(qr=None))
    assert not qr_wrong(_r())


def test_missing_prediction_is_a_failure_not_a_skip() -> None:
    assert not yolo_state_ok(_r(yolo_state=None))
    assert not yolo_id_ok(_r(yolo_type=None))


def test_by_condition_keeps_canonical_order_and_skips_absent_conditions() -> None:
    rows = [_r("tilt"), _r("clean"), _r("small")]

    assert list(by_condition(rows)) == ["clean", "tilt", "small"]


def test_confusion_matrix_counts_every_image_once() -> None:
    rows = [_r(), _r(yolo_state="lamp_critical"), _r(yolo_state=None)]

    matrix = confusion(rows, lambda r: r.yolo_state)

    assert matrix["lamp_normal"] == {
        "lamp_normal": 1,
        "lamp_warning": 0,
        "lamp_critical": 1,
        "(nada)": 1,
    }
    assert sum(sum(row.values()) for row in matrix.values()) == len(rows)


def test_rendered_tables_include_every_condition_total_and_honest_verdicts() -> None:
    rows = [_r("clean") for _ in range(30)] + [_r("blur", qr=None) for _ in range(30)]

    text = "\n".join(render_comparison(rows))

    assert "| clean |" in text
    assert "| blur |" in text
    assert "| TOTAL |" in text
    assert "IC95" in text
    assert "QR **ou** YOLO" in text
    # blur: so o YOLO acerta => diferenca detectavel a favor do YOLO
    blur_line = next(line for line in text.splitlines() if line.startswith("| blur | 30 |"))
    assert "YOLO é melhor" in blur_line
    clean_line = next(line for line in text.splitlines() if line.startswith("| clean | 30 |"))
    assert "sem diferença detectável" in clean_line


@pytest.mark.parametrize("n", [0, 1])
def test_paired_handles_tiny_and_empty_groups(n: int) -> None:
    p = paired([_r()] * n, qr_ok, yolo_id_ok)

    assert p.p_value == 1.0
    assert p.a.total == n
