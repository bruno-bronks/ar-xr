"""Estado de deploy por ambiente (REQ-OPS-001): tag atual, anterior e historico. Gravacao atomica."""

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

_TAG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
MAX_HISTORY = 100


def validate_tag(tag: str) -> str:
    if not _TAG.fullmatch(tag):
        raise ValueError("invalid image tag")
    return tag


@dataclass
class Event:
    tag: str
    at: str
    result: str  # deployed | failed | rolled_back | rollback_failed | rollback
    detail: str = ""


@dataclass
class State:
    current: str | None = None
    previous: str | None = None
    history: list[Event] = field(default_factory=list)


class Store(Protocol):
    def load(self) -> State: ...

    def save(self, state: State) -> None: ...


class MemoryStore:
    """Armazenamento em memoria (testes de logica); mesma regra de historico limitado."""

    def __init__(self) -> None:
        self._state = State()

    def load(self) -> State:
        return State(
            self._state.current,
            self._state.previous,
            [Event(**vars(e)) for e in self._state.history],
        )

    def save(self, state: State) -> None:
        state.history = state.history[-MAX_HISTORY:]
        self._state = State(
            state.current, state.previous, [Event(**vars(e)) for e in state.history]
        )


class StateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> State:
        if not self._path.is_file():
            return State()
        data = json.loads(self._path.read_text("utf-8"))
        return State(
            current=data.get("current"),
            previous=data.get("previous"),
            history=[Event(**e) for e in data.get("history", [])],
        )

    def save(self, state: State) -> None:
        state.history = state.history[-MAX_HISTORY:]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(asdict(state), indent=2) + "\n", "utf-8")
        os.replace(tmp, self._path)  # atomico: nunca deixa o arquivo pela metade
