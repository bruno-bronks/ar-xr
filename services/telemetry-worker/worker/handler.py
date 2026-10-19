"""Pipeline de validacao e gravacao de uma mensagem (SPEC-005; REQ-MNT-003, REQ-MNT-004)."""

import logging
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from spatial_domain.telemetry import (
    RejectReason,
    TelemetryRejected,
    equipment_id_from_topic,
    parse_payload,
    reject_future,
)
from spatial_storage.repository import RecordOutcome, Repository, UnknownEquipmentError

logger = logging.getLogger("worker.handler")

_MAX_LOGGED = 80


class Disposition(StrEnum):
    ACCEPTED = "ACCEPTED"
    ACCEPTED_HISTORY_ONLY = "ACCEPTED_HISTORY_ONLY"
    DUPLICATE = "DUPLICATE"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class HandleResult:
    disposition: Disposition
    reason: RejectReason | None = None


@dataclass
class Stats:
    counts: Counter[str] = field(default_factory=Counter)

    def record(self, result: HandleResult) -> None:
        if result.disposition is Disposition.REJECTED:
            self.counts[f"rejected:{result.reason}"] += 1
        else:
            self.counts[result.disposition.value.lower()] += 1


class MessageHandler:
    def __init__(self, repo: Repository, clock: Callable[[], datetime], stats: Stats) -> None:
        self._repo = repo
        self._clock = clock
        self.stats = stats

    def handle(self, topic: str, payload: bytes) -> HandleResult:
        """Rejeicoes sao resultados finais (retornam); falhas de infraestrutura PROPAGAM."""
        try:
            result = self._process(topic, payload)
        except TelemetryRejected as rejected:
            result = HandleResult(Disposition.REJECTED, rejected.reason)
            logger.warning(
                "message rejected: %s",
                rejected.reason,
                extra={
                    "reason": str(rejected.reason),
                    "topic": topic[:_MAX_LOGGED],
                    "detail": rejected.detail[:_MAX_LOGGED],
                    "payload_bytes": len(payload),
                },
            )
        self.stats.record(result)
        return result

    def _process(self, topic: str, payload: bytes) -> HandleResult:
        received_at = self._clock()
        event = parse_payload(payload)

        topic_equipment = equipment_id_from_topic(topic)
        if topic_equipment is None or topic_equipment != event.equipment_id:
            raise TelemetryRejected(RejectReason.TOPIC_MISMATCH)

        profile = self._repo.get_profile(event.equipment_id)
        if profile is None:
            raise TelemetryRejected(RejectReason.UNKNOWN_EQUIPMENT)
        if event.sensor_type not in profile:
            raise TelemetryRejected(RejectReason.UNKNOWN_SENSOR)

        reject_future(event, received_at)

        try:
            outcome = self._repo.record(event, received_at)
        except UnknownEquipmentError as exc:  # removido entre a checagem e a gravacao
            raise TelemetryRejected(RejectReason.UNKNOWN_EQUIPMENT) from exc
        return HandleResult(Disposition(outcome.value))


__all__ = ["Disposition", "HandleResult", "MessageHandler", "RecordOutcome", "Stats"]
