"""Metodos de comparacao SEM aprendizado (SPEC-011, D-036): decodificador de QR e lampada por cor.

- `decode_qr`: `cv2.QRCodeDetector` (tenta a imagem original e uma ampliada 2x; politica unica para
  todas as condicoes). O QR e lido como o app AR le: o texto e o marker opaco.
- `lamp_state_by_color`: baseline de limiar HSV — maior bolha circular de cor de lampada
  (verde/ambar/vermelho) com area plausivel. E de proposito simples: serve para medir se o YOLO
  acrescenta algo alem de uma regra de cor.
"""

import cv2
import numpy as np
from numpy.typing import NDArray

Image = NDArray[np.uint8]

_MIN_AREA, _MAX_AREA, _MIN_CIRCULARITY = 40.0, 1500.0, 0.6
_HUE_RANGES = {
    "lamp_critical": ((0, 9), (170, 179)),
    "lamp_warning": ((10, 28),),
    "lamp_normal": ((40, 85),),
}


def decode_qr(image: Image) -> str | None:
    detector = cv2.QRCodeDetector()
    for candidate in (
        image,
        cv2.resize(image, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC),
    ):
        try:
            text, _, _ = detector.detectAndDecode(candidate)
        except cv2.error:
            continue
        if text:
            return str(text)
    return None


def lamp_state_by_color(image: Image) -> str | None:
    """Classe `lamp_*` da melhor bolha de cor, ou None se nao houver candidata."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    saturated = (hsv[..., 1] >= 110) & (hsv[..., 2] >= 70)
    best: tuple[float, str] | None = None
    for cls, ranges in _HUE_RANGES.items():
        mask = np.zeros(hsv.shape[:2], np.uint8)
        for lo, hi in ranges:
            mask |= (((hsv[..., 0] >= lo) & (hsv[..., 0] <= hi)) & saturated).astype(np.uint8)
        count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        for i in range(1, count):
            area = float(stats[i, cv2.CC_STAT_AREA])
            if not _MIN_AREA <= area <= _MAX_AREA:
                continue
            w, h = float(stats[i, cv2.CC_STAT_WIDTH]), float(stats[i, cv2.CC_STAT_HEIGHT])
            circularity = (
                area / (w * h) * (4 / np.pi) if w and h else 0.0
            )  # preenchimento do retangulo
            aspect = min(w, h) / max(w, h)
            if circularity < _MIN_CIRCULARITY or aspect < 0.6:
                continue
            if best is None or area > best[0]:
                best = (area, cls)
    return best[1] if best else None
