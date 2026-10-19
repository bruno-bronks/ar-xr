"""Callbacks MQTT com ack manual (REQ-MNT-005).

Regra: o ack so e enviado depois de a mensagem ter desfecho FINAL (gravada, duplicada ou
rejeitada). Qualquer falha de infraestrutura => sem ack + desconexao => o broker reentrega apos a
reconexao (sessao persistente) e a gravacao idempotente absorve o reenvio.
"""

import logging
from typing import Any, Protocol

from worker.handler import MessageHandler

logger = logging.getLogger("worker.consumer")

SUBSCRIPTION = "spatial/v1/equipment/+/telemetry"


def next_backoff(current: float, *, failed: bool, cap: float = 30.0) -> float:
    """Backoff de reconexao: dobra a cada falha consecutiva (ate `cap`); volta a 1 s apos sucesso."""
    return min(current * 2, cap) if failed else 1.0


class MqttClient(Protocol):
    def ack(self, mid: int, qos: int) -> object: ...

    def disconnect(self) -> object: ...

    def subscribe(self, topic: str, qos: int = 0) -> object: ...


class Consumer:
    def __init__(self, handler: MessageHandler) -> None:
        self.handler = handler
        self.failed = False
        self.connected = False

    def on_connect(
        self, client: MqttClient, userdata: Any, flags: Any, reason_code: Any, properties: Any
    ) -> None:
        refused = getattr(reason_code, "is_failure", reason_code != 0)
        if refused:
            logger.error("broker refused connection: %s", reason_code)
            return
        self.failed = False
        self.connected = True
        client.subscribe(SUBSCRIPTION, qos=1)
        logger.info("connected and subscribed", extra={"subscription": SUBSCRIPTION})

    def on_disconnect(self, client: Any, userdata: Any, *args: Any) -> None:
        self.connected = False
        logger.warning("disconnected from broker")

    def on_message(self, client: MqttClient, userdata: Any, message: Any) -> None:
        if self.failed:
            return  # sem ack: sera reentregue depois da reconexao
        try:
            self.handler.handle(message.topic, bytes(message.payload))
        except Exception:
            logger.exception("infrastructure failure while handling message; will not ack")
            self.failed = True
            client.disconnect()
            return
        client.ack(message.mid, message.qos)
