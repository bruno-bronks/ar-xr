"""Fabrica de apps de teste: repositorio em memoria, relogio controlavel, verificacoes injetadas."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from app.main import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient
from spatial_domain.status import Quality
from spatial_domain.telemetry import TelemetryEvent
from spatial_storage.memory import InMemoryRepository
from spatial_storage.repository import Repository
from spatial_storage.seed_data import SEED

_backend: Callable[[], Repository] = lambda: InMemoryRepository(SEED)  # noqa: E731


def set_backend(factory: Callable[[], Repository]) -> None:
    """Troca o repositorio usado pelos testes (memoria x PostgreSQL real)."""
    global _backend
    _backend = factory


def new_repo() -> Repository:
    return _backend()


NOW = datetime(2026, 10, 19, 12, 0, 30, tzinfo=UTC)
TOKEN_A = "demo-operator-a"
TOKEN_B = "demo-operator-b"


@dataclass
class Clock:
    now: datetime = NOW

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


def ok() -> bool:
    return True


def make_app(
    *,
    repo: Repository | None = None,
    clock: Clock | None = None,
    checks: Mapping[str, Callable[[], bool]] | None = None,
    **options: Any,
) -> FastAPI:
    return create_app(
        checks=checks if checks is not None else {"database": ok, "broker": ok},
        repo=repo if repo is not None else new_repo(),
        clock=clock if clock is not None else Clock(),
        **options,
    )


def make_client(**kwargs: Any) -> TestClient:
    return TestClient(make_app(**kwargs), raise_server_exceptions=False)


def auth(token: str = TOKEN_A) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def reading(
    equipment_id: str,
    sensor: str,
    value: float,
    *,
    age_s: float = 1.0,
    quality: Quality = Quality.GOOD,
    event_id: str | None = None,
    now: datetime = NOW,
) -> TelemetryEvent:
    return TelemetryEvent(
        event_id=event_id or f"{equipment_id}-{sensor}-{value}-{age_s}",
        source="test",
        equipment_id=equipment_id,
        sensor_type=sensor,
        value=value,
        unit="celsius" if sensor == "temperature" else "mm/s",
        observed_at=now - timedelta(seconds=age_s),
        quality=quality,
    )


def feed(repo: Repository, *events: TelemetryEvent) -> None:
    for event in events:
        repo.record(event, NOW)
