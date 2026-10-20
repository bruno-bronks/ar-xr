"""Gerador DETERMINISTICO de cenas sinteticas (SPEC-011, REQ-CV-001, D-033).

Cada cena tem um equipamento estilizado (compressor, bomba ou motor), um adesivo com QR (o
marker do equipamento) e uma lampada de estado (verde/ambar/vermelha) cujo estado vem da regra real
(`truth.py`). Ha DISTRATORES de proposito (lampada azul/branca, placa vermelha, folhagem verde) e
seis condicoes de degradacao. NADA disto e foto real: os numeros nao generalizam para o mundo real.
"""

from dataclasses import dataclass

import cv2
import numpy as np
import segno
from numpy.typing import NDArray
from spatial_domain.status import Status

from spatial_cv.truth import (
    EQUIPMENT_IDS,
    LAMP_CLASS,
    LAMP_STATUSES,
    Truth,
    sample_truth,
)

Image = NDArray[np.uint8]
WIDTH, HEIGHT = 640, 480
CLASSES = ("compressor", "pump", "motor", "lamp_normal", "lamp_warning", "lamp_critical")
CONDITIONS = ("clean", "blur", "lowlight", "tilt", "occlusion", "small")
_LAMP_BGR = {
    Status.NORMAL: (60, 200, 40),
    Status.WARNING: (0, 165, 255),
    Status.CRITICAL: (30, 30, 225),
}
_BODY_BGR = {
    "compressor": (150, 120, 90),  # azul acinzentado
    "pump": (130, 150, 60),  # verde-azulado
    "motor": (40, 90, 170),  # laranja queimado
}
MIN_LAMP_VISIBLE = 0.5  # fracao da lampada que precisa estar visivel para ter rotulo


@dataclass(frozen=True)
class Box:
    cls: str
    x0: float
    y0: float
    x1: float
    y1: float

    def clipped(self) -> "Box":
        return Box(
            self.cls,
            float(np.clip(self.x0, 0, WIDTH)),
            float(np.clip(self.y0, 0, HEIGHT)),
            float(np.clip(self.x1, 0, WIDTH)),
            float(np.clip(self.y1, 0, HEIGHT)),
        )

    @property
    def area(self) -> float:
        return max(0.0, self.x1 - self.x0) * max(0.0, self.y1 - self.y0)


@dataclass(frozen=True)
class Scene:
    image: Image
    boxes: tuple[Box, ...]
    seed: int
    condition: str
    truth: Truth
    lamp_visible: bool


def _background(rng: np.random.Generator) -> Image:
    base = rng.integers(95, 200, size=3).astype(np.float32)
    grad = np.linspace(rng.uniform(0.8, 1.0), rng.uniform(0.6, 0.95), HEIGHT, dtype=np.float32)
    img = np.ones((HEIGHT, WIDTH, 3), np.float32) * base * grad[:, None, None]
    noise = rng.normal(0, 1, size=(HEIGHT // 24, WIDTH // 24, 3)).astype(np.float32)
    upscaled: NDArray[np.float32] = np.asarray(
        cv2.resize(noise, (WIDTH, HEIGHT), interpolation=cv2.INTER_CUBIC), dtype=np.float32
    )
    img = np.clip(img + upscaled * 9, 0, 255).astype(np.uint8)
    floor_y = int(rng.uniform(0.68, 0.8) * HEIGHT)
    img[floor_y:] = (img[floor_y:] * rng.uniform(0.55, 0.8)).astype(np.uint8)
    for _ in range(int(rng.integers(2, 5))):  # paineis de parede
        x0, y0 = int(rng.integers(0, WIDTH - 60)), int(rng.integers(0, floor_y - 40))
        w, h = int(rng.integers(40, 160)), int(rng.integers(30, 120))
        tint = np.clip(base + rng.integers(-25, 25, size=3), 0, 255)
        cv2.rectangle(img, (x0, y0), (x0 + w, y0 + h), tuple(int(c) for c in tint), -1)
    return np.asarray(img, dtype=np.uint8)


def _jit(
    rng: np.random.Generator, color: tuple[int, int, int], amount: int = 18
) -> tuple[int, ...]:
    return tuple(int(np.clip(c + rng.integers(-amount, amount + 1), 0, 255)) for c in color)


def _draw_equipment(
    img: Image, mask: Image, rng: np.random.Generator, kind: str, cx: int, cy: int, w: int
) -> tuple[int, int, int, int]:
    """Desenha o equipamento em `img` e sua silhueta em `mask`; devolve (x0, y0, x1, y1) do corpo."""
    color = _jit(rng, _BODY_BGR[kind])
    dark = tuple(int(c * 0.55) for c in color)

    def rect(x0: int, y0: int, x1: int, y1: int, col: tuple[int, ...], radius: int = 0) -> None:
        for target, value in ((img, col), (mask, (255, 255, 255))):
            if radius:
                cv2.rectangle(target, (x0 + radius, y0), (x1 - radius, y1), value, -1)
                cv2.rectangle(target, (x0, y0 + radius), (x1, y1 - radius), value, -1)
                for px, py in ((x0 + radius, y0 + radius), (x1 - radius, y0 + radius),
                               (x0 + radius, y1 - radius), (x1 - radius, y1 - radius)):  # fmt: skip
                    cv2.circle(target, (px, py), radius, value, -1)
            else:
                cv2.rectangle(target, (x0, y0), (x1, y1), value, -1)

    def circle(px: int, py: int, r: int, col: tuple[int, ...]) -> None:
        cv2.circle(img, (px, py), r, col, -1)
        cv2.circle(mask, (px, py), r, (255, 255, 255), -1)

    if kind == "compressor":
        bh = int(w * 0.36)
        x0, y0, x1, y1 = cx - w // 2, cy - bh // 2, cx + int(w * 0.28), cy + bh // 2
        rect(x0, y0, x1, y1, color, radius=bh // 3)  # tanque
        rect(x1 - 6, cy - int(bh * 0.28), cx + w // 2, cy + int(bh * 0.28), dark)  # motor
        rect(x0 + 10, y1, x0 + 28, y1 + int(bh * 0.25), dark)  # pes
        rect(x1 - 40, y1, x1 - 22, y1 + int(bh * 0.25), dark)
        rect(cx - 12, y0 - int(bh * 0.2), cx + 12, y0, dark)  # tubo superior
        body = (x0, y0, x1, y1)
    elif kind == "pump":
        r = int(w * 0.2)
        px = cx - int(w * 0.25)
        circle(px, cy, r, color)  # voluta
        circle(px, cy, int(r * 0.45), dark)
        rect(cx - w // 2, cy - int(r * 0.25), px - r + 4, cy + int(r * 0.25), dark)  # tubo
        rect(px + r - 6, cy - int(r * 0.7), cx + w // 2, cy + int(r * 0.7), color)  # motor
        rect(cx - int(w * 0.45), cy + r, cx + w // 2, cy + r + int(w * 0.06), dark)  # base
        body = (px - r, cy - r, cx + w // 2, cy + r)
    else:  # motor
        bh = int(w * 0.34)
        x0, y0, x1, y1 = cx - int(w * 0.42), cy - bh // 2, cx + int(w * 0.42), cy + bh // 2
        rect(x0, y0, x1, y1, color, radius=bh // 6)
        for fx in range(x0 + 18, x1 - 12, 16):  # aletas
            cv2.line(img, (fx, y0 + 4), (fx, y1 - 4), dark, 3)
        rect(x1, cy - int(bh * 0.18), x1 + int(w * 0.1), cy + int(bh * 0.18), dark)  # eixo
        rect(x0 + 6, y1, x0 + 30, y1 + int(bh * 0.22), dark)
        rect(x1 - 30, y1, x1 - 6, y1 + int(bh * 0.22), dark)
        body = (x0, y0, x1, y1)
    return body


def _qr_patch(text: str, side: int) -> Image:
    matrix = segno.make(text, error="m", micro=False).matrix
    n = len(matrix)
    quiet = 4
    cells = np.ones((n + 2 * quiet, n + 2 * quiet), np.uint8) * 255
    for y, row in enumerate(matrix):
        for x, bit in enumerate(row):
            if bit:
                cells[y + quiet, x + quiet] = 0
    patch = cv2.resize(cells, (side, side), interpolation=cv2.INTER_NEAREST)
    return np.asarray(cv2.cvtColor(patch, cv2.COLOR_GRAY2BGR), dtype=np.uint8)


def _draw_lamp(
    img: Image, rng: np.random.Generator, cx: int, cy: int, r: int, status: Status
) -> Box:
    bezel = int(r * 1.35)
    cv2.circle(img, (cx, cy), bezel, (35, 35, 35), -1)
    color = _jit(rng, _LAMP_BGR[status], 12)
    cv2.circle(img, (cx, cy), r, color, -1)
    glow = tuple(min(255, int(c * 0.5 + 130)) for c in color)
    cv2.circle(img, (cx - r // 3, cy - r // 3), max(2, r // 3), glow, -1)
    return Box(LAMP_CLASS[status], cx - bezel, cy - bezel, cx + bezel, cy + bezel)


def _decoys(img: Image, rng: np.random.Generator, body: tuple[int, int, int, int]) -> None:
    """Distratores: lampada azul/branca no corpo, placa vermelha e folhagem verde no fundo."""
    x0, y0, x1, y1 = body
    if rng.random() < 0.5:
        for color in ((225, 120, 20), (235, 235, 235)):
            if rng.random() < 0.7:
                px, py = int(rng.uniform(x0 + 15, x1 - 15)), int(rng.uniform(y0 + 12, y1 - 12))
                cv2.circle(img, (px, py), int(rng.uniform(6, 10)), color, -1)
    for color, probability in (((40, 40, 200), 0.4), ((50, 160, 50), 0.4)):
        if rng.random() < probability:
            for _ in range(10):  # procura um lugar fora do equipamento
                w, h = int(rng.integers(28, 70)), int(rng.integers(28, 70))
                px, py = int(rng.integers(0, WIDTH - w)), int(rng.integers(0, HEIGHT - h))
                if px + w < x0 - 10 or px > x1 + 10 or py + h < y0 - 10 or py > y1 + 10:
                    cv2.rectangle(img, (px, py), (px + w, py + h), color, -1)
                    break


def _homography(rng: np.random.Generator) -> NDArray[np.float64]:
    angle = np.deg2rad(rng.uniform(-25, 25))
    c, s = np.cos(angle), np.sin(angle)
    center = np.array([WIDTH / 2, HEIGHT / 2])
    corners = np.array([[0, 0], [WIDTH, 0], [WIDTH, HEIGHT], [0, HEIGHT]], np.float64)
    rotated = (corners - center) @ np.array([[c, -s], [s, c]]).T + center
    jitter = rng.uniform(-0.1, 0.1, size=(4, 2)) * np.array([WIDTH, HEIGHT])
    matrix: NDArray[np.float64] = cv2.getPerspectiveTransform(
        corners.astype(np.float32), (rotated + jitter).astype(np.float32)
    ).astype(np.float64)
    return matrix


def _transform_box(box: Box, matrix: NDArray[np.float64]) -> Box:
    pts = np.array(
        [[box.x0, box.y0], [box.x1, box.y0], [box.x1, box.y1], [box.x0, box.y1]], np.float32
    )
    out = cv2.perspectiveTransform(pts[None], matrix.astype(np.float32))[0]
    return Box(
        box.cls,
        float(out[:, 0].min()),
        float(out[:, 1].min()),
        float(out[:, 0].max()),
        float(out[:, 1].max()),
    ).clipped()


def _occlude(
    img: Image, rng: np.random.Generator, body: tuple[int, int, int, int]
) -> list[tuple[int, int, int, int]]:
    x0, y0, x1, y1 = body
    rects = []
    for _ in range(int(rng.integers(1, 3))):
        w = int((x1 - x0) * rng.uniform(0.25, 0.5))
        h = int((y1 - y0) * rng.uniform(0.5, 1.1))
        px = int(rng.uniform(x0 - w * 0.2, x1 - w * 0.8))
        py = int(rng.uniform(y0 - h * 0.2, y1 - h * 0.8))
        cv2.rectangle(
            img, (px, py), (px + w, py + h), tuple(int(v) for v in rng.integers(20, 90, size=3)), -1
        )
        rects.append((px, py, px + w, py + h))
    return rects


def _covered_fraction(box: Box, rects: list[tuple[int, int, int, int]]) -> float:
    cover = np.zeros((HEIGHT, WIDTH), np.uint8)
    for rx0, ry0, rx1, ry1 in rects:
        cv2.rectangle(
            cover, (max(rx0, 0), max(ry0, 0)), (min(rx1, WIDTH - 1), min(ry1, HEIGHT - 1)), 1, -1
        )
    x0, y0, x1, y1 = (round(v) for v in (box.x0, box.y0, box.x1, box.y1))
    region = cover[max(y0, 0) : max(y1, 0), max(x0, 0) : max(x1, 0)]
    return float(region.mean()) if region.size else 0.0


def render_scene(
    seed: int, condition: str, equipment_id: str | None = None, status: Status | None = None
) -> Scene:
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition: {condition}")
    rng = np.random.default_rng(seed)
    equipment_id = equipment_id or EQUIPMENT_IDS[int(rng.integers(len(EQUIPMENT_IDS)))]
    target = status or LAMP_STATUSES[int(rng.integers(len(LAMP_STATUSES)))]
    truth = sample_truth(rng, equipment_id, target)

    img = _background(rng)
    mask = np.zeros((HEIGHT, WIDTH, 3), np.uint8)
    scale = rng.uniform(0.22, 0.3) if condition == "small" else rng.uniform(0.5, 0.6)
    w = int(WIDTH * scale)
    cx = int(WIDTH / 2 + rng.uniform(-0.12, 0.12) * WIDTH)
    cy = int(HEIGHT * rng.uniform(0.42, 0.55))
    body = _draw_equipment(img, mask, rng, truth.equipment_type, cx, cy, w)
    bx0, by0, bx1, by1 = body
    ys, xs = np.nonzero(mask[..., 0])
    equipment_box = Box(
        truth.equipment_type, float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())
    )

    # lampada (canto superior do corpo) e adesivo QR (parte central), sem sobreposicao
    r = max(4, int(w * 0.05))
    lamp_cx = int(rng.uniform(bx0 + r * 2, bx0 + (bx1 - bx0) * 0.35))
    lamp_cy = int(by0 + (by1 - by0) * rng.uniform(0.22, 0.4))
    lamp_box = _draw_lamp(img, rng, lamp_cx, lamp_cy, r, truth.status)
    side = max(12, int(w * 0.3))
    qx0 = int(
        rng.uniform(bx0 + (bx1 - bx0) * 0.45, max(bx0 + (bx1 - bx0) * 0.45 + 1, bx1 - side - 4))
    )
    qy0 = int(np.clip(by0 + (by1 - by0) * 0.5 - side / 2, 0, HEIGHT - side - 1))
    qx0 = int(np.clip(qx0, 0, WIDTH - side - 1))
    img[qy0 : qy0 + side, qx0 : qx0 + side] = _qr_patch(truth.qr_text, side)
    _decoys(img, rng, body)

    boxes = [equipment_box, lamp_box]
    covered_rects: list[tuple[int, int, int, int]] = []
    if condition == "occlusion":
        covered_rects = _occlude(img, rng, body)
    if condition == "tilt":
        matrix = _homography(rng)
        img = np.asarray(
            cv2.warpPerspective(img, matrix, (WIDTH, HEIGHT), borderMode=cv2.BORDER_REFLECT),
            dtype=np.uint8,
        )
        boxes = [_transform_box(b, matrix) for b in boxes]
    if condition == "blur":
        sigma = rng.uniform(2.5, 5.0)
        img = np.asarray(cv2.GaussianBlur(img, (0, 0), sigma), dtype=np.uint8)
        if rng.random() < 0.5:  # desfoque de movimento adicional
            length = int(rng.integers(9, 18))
            kernel = np.zeros((length, length), np.float32)
            kernel[length // 2, :] = 1.0 / length
            rot = cv2.getRotationMatrix2D(
                (length / 2 - 0.5, length / 2 - 0.5), float(rng.uniform(0, 180)), 1.0
            )
            kernel = np.asarray(cv2.warpAffine(kernel, rot, (length, length)), dtype=np.float32)
            kernel = kernel / max(float(kernel.sum()), 1e-6)
            img = np.asarray(cv2.filter2D(img, -1, kernel), dtype=np.uint8)
    if condition == "lowlight":
        gain = rng.uniform(0.12, 0.3)
        img = np.power(img.astype(np.float32) / 255.0, 1.5) * 255.0 * gain * 2.2
        img = img + rng.normal(0, rng.uniform(6, 12), size=img.shape)
        img = np.clip(img, 0, 255).astype(np.uint8)
    img = np.clip(img.astype(np.float32) + rng.normal(0, 2.0, size=img.shape), 0, 255).astype(
        np.uint8
    )

    lamp = boxes[1]
    lamp_visible = lamp.area > 4 and (
        not covered_rects or _covered_fraction(lamp, covered_rects) < (1 - MIN_LAMP_VISIBLE)
    )
    final = [boxes[0]] + ([lamp] if lamp_visible else [])
    return Scene(img, tuple(final), seed, condition, truth, lamp_visible)


def yolo_lines(boxes: tuple[Box, ...]) -> list[str]:
    lines = []
    for b in boxes:
        c = b.clipped()
        w, h = (c.x1 - c.x0) / WIDTH, (c.y1 - c.y0) / HEIGHT
        if w <= 0 or h <= 0:
            continue
        lines.append(
            f"{CLASSES.index(c.cls)} {(c.x0 + c.x1) / 2 / WIDTH:.6f} {(c.y0 + c.y1) / 2 / HEIGHT:.6f} {w:.6f} {h:.6f}"
        )
    return lines
