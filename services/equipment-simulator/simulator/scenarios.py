"""Cenarios deterministicos do simulador (SPEC-007; REQ-SIM-001). Logica pura: sem I/O nem relogio."""

import json
import random
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from spatial_storage.seed_data import SEED

SOURCE = "equipment-simulator"
NOISE = 0.005  # amplitude do ruido, fracao do limite `warn`
LATE_BY = timedelta(seconds=60)

SCENARIOS = {"EQ-001": "steady", "EQ-002": "ramp", "EQ-003": "dropout"}  # demais: steady
_PROFILES = {
    e.id: {p.sensor_type: p for p in e.profile} for e in SEED.equipment
}  # limites vem do seed: uma unica fonte de verdade
_ID_SAFE = re.compile(r"[^A-Za-z0-9._:-]")


@dataclass(frozen=True)
class SimConfig:
    interval_s: float = 2.0
    cycle_ticks: int = 120
    seed: int = 42
    duplicate_every: int = 7  # 0 = desligado
    late_every: int = 0  # 0 = desligado
    run_id: str = "r0"

    def __post_init__(self) -> None:
        if self.interval_s <= 0:
            raise ValueError("interval_s must be positive")
        if self.cycle_ticks <= 0:
            raise ValueError("cycle_ticks must be positive")
        if self.duplicate_every < 0 or self.late_every < 0:
            raise ValueError("duplicate_every/late_every must be >= 0")


@dataclass(frozen=True)
class Message:
    topic: str
    payload: bytes


def _noise(cfg: SimConfig, equipment_id: str, sensor: str, tick: int) -> float:
    rng = random.Random(f"{cfg.seed}:{equipment_id}:{sensor}:{tick}")  # noqa: S311 - nao e cripto
    return rng.uniform(-1.0, 1.0) * NOISE


def sensor_value(equipment_id: str, sensor: str, tick: int, cfg: SimConfig) -> float | None:
    """Valor do sensor no `tick`, ou None se o equipamento esta em silencio (dropout)."""
    profile = _PROFILES[equipment_id][sensor]
    scenario = SCENARIOS.get(equipment_id, "steady")
    phase = (tick % cfg.cycle_ticks) / cfg.cycle_ticks
    base_low = 0.55 if sensor == "temperature" else 0.5
    low = base_low * profile.warn
    value = low

    if scenario == "ramp" and sensor == "temperature":
        peak = 1.1 * profile.crit
        if 0.2 <= phase < 0.5:
            value = low + (peak - low) * (phase - 0.2) / 0.3
        elif 0.5 <= phase < 0.7:
            value = peak
        elif 0.7 <= phase < 0.9:
            value = peak - (peak - low) * (phase - 0.7) / 0.2
    elif scenario == "dropout" and 0.5 <= phase < 0.9:
        return None

    return round(value + profile.warn * _noise(cfg, equipment_id, sensor, tick), 3)


class Simulation:
    def __init__(self, cfg: SimConfig) -> None:
        self._cfg = cfg
        self._tick = 0
        self._count = 0
        self._run = _ID_SAFE.sub("-", cfg.run_id)

    def _message(
        self, equipment_id: str, sensor: str, value: float, observed_at: datetime, event_id: str
    ) -> Message:
        profile = _PROFILES[equipment_id][sensor]
        event = {
            "schema_version": 1,
            "event_id": event_id,
            "source": SOURCE,
            "equipment_id": equipment_id,
            "sensor_type": sensor,
            "value": value,
            "unit": profile.unit,
            "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
            "quality": "GOOD",
        }
        return Message(
            topic=f"spatial/v1/equipment/{equipment_id}/telemetry",
            payload=json.dumps(event, sort_keys=True, separators=(",", ":")).encode(),
        )

    def step(self, now: datetime) -> list[Message]:
        """Mensagens do proximo tick. `now` (aware, UTC) vira o `observed_at`."""
        cfg, tick = self._cfg, self._tick
        self._tick += 1
        out: list[Message] = []
        for equipment_id in _PROFILES:
            for sensor in _PROFILES[equipment_id]:
                value = sensor_value(equipment_id, sensor, tick, cfg)
                if value is None:
                    continue
                event_id = f"{equipment_id}-{sensor}-{self._run}-{tick}"
                message = self._message(equipment_id, sensor, value, now, event_id)
                out.append(message)
                self._count += 1
                if cfg.duplicate_every and self._count % cfg.duplicate_every == 0:
                    out.append(message)  # reenvio identico (QoS 1 at-least-once)
                if cfg.late_every and self._count % cfg.late_every == 0:
                    out.append(
                        self._message(
                            equipment_id,
                            sensor,
                            value,
                            now - LATE_BY,
                            f"{event_id}-late{self._count}",
                        )
                    )
        return out
