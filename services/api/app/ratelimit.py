"""Limitador de janela fixa em memoria, por chave (REQ-SEC-004). Processo unico (ver SPEC-006)."""

import math
import threading
from collections.abc import Callable
from datetime import datetime


class FixedWindowLimiter:
    def __init__(self, limit: int, window_s: float, clock: Callable[[], datetime]) -> None:
        self._limit = limit
        self._window = window_s
        self._clock = clock
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[float, int]] = {}

    def hit(self, key: str) -> int | None:
        """Registra uma tentativa. Retorna None se permitida, ou segundos ate liberar."""
        now = self._clock().timestamp()
        with self._lock:
            start, count = self._windows.get(key, (now, 0))
            if now - start >= self._window:
                start, count = now, 0
            if count >= self._limit:
                return max(1, math.ceil(start + self._window - now))
            self._windows[key] = (start, count + 1)
            if len(self._windows) > 10_000:  # evita crescimento ilimitado
                self._windows = {
                    k: v for k, v in self._windows.items() if now - v[0] < self._window
                }
            return None
