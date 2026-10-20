"""Comparacao QR x YOLO (identificacao) e YOLO x baseline x simulador (estado) — SPEC-011, REQ-CV-003.

Logica pura (sem ultralytics): recebe um resultado por imagem e produz taxas com IC de Wilson 95 % e
veredito pareado de McNemar. So afirma superioridade com p < 0,05.
"""

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from spatial_cv.metrics import Rate, mcnemar_exact, paired_verdict
from spatial_cv.scene import CONDITIONS

STATE_CLASSES = ("lamp_normal", "lamp_warning", "lamp_critical")


@dataclass(frozen=True)
class ImageResult:
    condition: str
    truth_type: str
    truth_qr: str
    truth_state: str  # lamp_normal | lamp_warning | lamp_critical (da regra real do simulador)
    lamp_visible: bool
    qr_text: str | None  # None = o decodificador nao leu nada
    yolo_type: str | None  # None = nenhuma deteccao de equipamento
    yolo_state: str | None
    hsv_state: str | None


@dataclass(frozen=True)
class Paired:
    a: Rate
    b: Rate
    only_a: int
    only_b: int
    both: int
    neither: int
    either: Rate

    def verdict(self, name_a: str, name_b: str) -> str:
        return paired_verdict(self.only_a, self.only_b, name_a, name_b)

    @property
    def p_value(self) -> float:
        return mcnemar_exact(self.only_a, self.only_b)


def paired(
    results: Sequence[ImageResult],
    ok_a: Callable[[ImageResult], bool],
    ok_b: Callable[[ImageResult], bool],
) -> Paired:
    only_a = only_b = both = neither = 0
    for r in results:
        a, b = ok_a(r), ok_b(r)
        both += a and b
        only_a += a and not b
        only_b += b and not a
        neither += not a and not b
    n = len(results)
    return Paired(
        Rate(both + only_a, n), Rate(both + only_b, n), only_a, only_b, both, neither,
        Rate(both + only_a + only_b, n),
    )  # fmt: skip


def qr_ok(r: ImageResult) -> bool:
    return r.qr_text == r.truth_qr


def qr_wrong(r: ImageResult) -> bool:
    """Leu algo, mas o texto nao e o marker verdadeiro (erro silencioso)."""
    return r.qr_text is not None and r.qr_text != r.truth_qr


def yolo_id_ok(r: ImageResult) -> bool:
    return r.yolo_type == r.truth_type


def yolo_state_ok(r: ImageResult) -> bool:
    return r.yolo_state == r.truth_state


def hsv_state_ok(r: ImageResult) -> bool:
    return r.hsv_state == r.truth_state


def by_condition(results: Sequence[ImageResult]) -> dict[str, list[ImageResult]]:
    grouped: dict[str, list[ImageResult]] = defaultdict(list)
    for r in results:
        grouped[r.condition].append(r)
    return {c: grouped[c] for c in CONDITIONS if c in grouped}


def confusion(
    results: Sequence[ImageResult], pick: Callable[[ImageResult], str | None]
) -> dict[str, dict[str, int]]:
    matrix = {t: {**dict.fromkeys(STATE_CLASSES, 0), "(nada)": 0} for t in STATE_CLASSES}
    for r in results:
        matrix[r.truth_state][pick(r) or "(nada)"] += 1
    return matrix


def render_comparison(results: Sequence[ImageResult]) -> list[str]:
    """Tabelas em Markdown da comparacao, por condicao e total."""
    groups = [*by_condition(results).items(), ("TOTAL", list(results))]
    lines = [
        "### Identificação do equipamento: QR vs YOLO (verdade = marker/tipo do seed)",
        "",
        "| Condição | n | QR leu o marker certo | YOLO acertou o tipo | QR **ou** YOLO | QR leu errado (silencioso) | Veredito pareado |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, rows in groups:
        p = paired(rows, qr_ok, yolo_id_ok)
        wrong = Rate(sum(qr_wrong(r) for r in rows), len(rows))
        lines.append(
            f"| {name} | {len(rows)} | {p.a.text()} | {p.b.text()} | {p.either.text()} | {wrong.successes}/{wrong.total} | {p.verdict('QR', 'YOLO')} |"
        )
    lines += [
        "",
        "### Estado indicado pela lâmpada: YOLO vs baseline de cor vs simulador (verdade = regra real `evaluate_status`)",
        "",
        "| Condição | n | lâmpada visível | YOLO acertou | baseline HSV acertou | YOLO **ou** HSV | Veredito pareado |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, rows in groups:
        p = paired(rows, yolo_state_ok, hsv_state_ok)
        visible = sum(r.lamp_visible for r in rows)
        lines.append(
            f"| {name} | {len(rows)} | {visible}/{len(rows)} | {p.a.text()} | {p.b.text()} | {p.either.text()} | {p.verdict('YOLO', 'baseline HSV')} |"
        )
    return lines
