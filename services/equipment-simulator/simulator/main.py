"""Entrypoint do simulador: publica via MQTT (QoS 1) sem nunca encerrar por erro de rede."""

import logging
import signal
import threading
import time
from datetime import UTC, datetime
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from spatial_common.logging_json import configure_logging

from simulator.scenarios import SimConfig, Simulation

logger = logging.getLogger("simulator.main")


class SimulatorSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    mqtt_host: str = "localhost"
    mqtt_port: int = Field(default=1883, ge=1, le=65535)
    sim_interval_seconds: float = Field(default=2.0, gt=0)
    sim_cycle_ticks: int = Field(default=120, gt=0)
    sim_seed: int = 42
    sim_duplicate_every: int = Field(default=7, ge=0)
    sim_late_every: int = Field(default=0, ge=0)
    sim_run_id: str = ""
    log_level: str = "INFO"


def main() -> None:
    settings = SimulatorSettings()
    configure_logging(settings.log_level)
    run_id = settings.sim_run_id or format(int(time.time()), "x")
    simulation = Simulation(
        SimConfig(
            interval_s=settings.sim_interval_seconds,
            cycle_ticks=settings.sim_cycle_ticks,
            seed=settings.sim_seed,
            duplicate_every=settings.sim_duplicate_every,
            late_every=settings.sim_late_every,
            run_id=run_id,
        )
    )

    connected = threading.Event()
    stop = threading.Event()

    client = mqtt.Client(CallbackAPIVersion.VERSION2, client_id=f"equipment-simulator-{run_id}")
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    def on_connect(_c: Any, _u: Any, _f: Any, reason_code: Any, _p: Any) -> None:
        if not reason_code.is_failure:
            connected.set()
            logger.info("connected", extra={"run_id": run_id})

    def on_disconnect(*_: Any) -> None:
        connected.clear()
        logger.warning("disconnected; paho will retry with backoff")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())

    client.connect_async(settings.mqtt_host, settings.mqtt_port, keepalive=30)
    client.loop_start()
    published = 0
    while not stop.wait(settings.sim_interval_seconds):
        messages = simulation.step(datetime.now(UTC))
        if not connected.is_set():
            logger.warning("broker unavailable; tick skipped", extra={"skipped": len(messages)})
            continue
        for message in messages:
            client.publish(message.topic, message.payload, qos=1, retain=False)
        published += len(messages)
        if published and published % 200 < len(messages):
            logger.info("published", extra={"total": published})
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
