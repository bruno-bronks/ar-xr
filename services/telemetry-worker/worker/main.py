"""Entrypoint do worker: conexao MQTT resiliente + heartbeat para o healthcheck."""

import logging
import signal
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from spatial_common.logging_json import configure_logging
from spatial_storage.postgres import PostgresRepository
from sqlalchemy import create_engine

from worker.consumer import Consumer, next_backoff
from worker.handler import MessageHandler, Stats

logger = logging.getLogger("worker.main")


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: SecretStr
    mqtt_host: str = "localhost"
    mqtt_port: int = Field(default=1883, ge=1, le=65535)
    mqtt_client_id: str = "telemetry-worker-1"
    heartbeat_file: str = "/tmp/worker-heartbeat"  # noqa: S108
    log_level: str = "INFO"
    stats_interval_seconds: float = 30.0


def _heartbeat_loop(
    consumer: Consumer, stats: Stats, path: Path, stats_interval: float, stop: threading.Event
) -> None:
    last_stats = time.monotonic()
    while not stop.wait(5.0):
        if consumer.connected and not consumer.failed:
            path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
        if time.monotonic() - last_stats >= stats_interval:
            last_stats = time.monotonic()
            logger.info("stats", extra={"counts": dict(stats.counts)})


def main() -> None:
    settings = WorkerSettings()
    configure_logging(settings.log_level)

    engine = create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)
    stats = Stats()
    consumer = Consumer(
        MessageHandler(PostgresRepository(engine), lambda: datetime.now(UTC), stats)
    )

    client = mqtt.Client(
        CallbackAPIVersion.VERSION2,
        client_id=settings.mqtt_client_id,
        clean_session=False,  # sessao persistente => redelivery de QoS 1 nao confirmado
        manual_ack=True,
    )
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.on_connect = consumer.on_connect
    client.on_disconnect = consumer.on_disconnect
    client.on_message = consumer.on_message

    stop = threading.Event()

    def shutdown(*_: Any) -> None:
        stop.set()
        client.disconnect()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    heartbeat = threading.Thread(
        target=_heartbeat_loop,
        args=(
            consumer,
            stats,
            Path(settings.heartbeat_file),
            settings.stats_interval_seconds,
            stop,
        ),
        daemon=True,
    )
    heartbeat.start()

    backoff = 1.0
    while not stop.is_set():
        failed = False
        try:
            client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=30)
            client.loop_forever(retry_first_connection=True)  # reconecta sozinho em quedas de rede
            failed = consumer.failed  # saiu por falha de infraestrutura (sem ack) ou por shutdown
        except OSError:
            failed = True
            logger.exception("cannot reach broker; retrying", extra={"backoff_s": backoff})
        if stop.is_set():
            break
        backoff = next_backoff(backoff, failed=failed)
        stop.wait(backoff)
    logger.info("worker stopped", extra={"counts": dict(stats.counts)})


if __name__ == "__main__":
    main()
