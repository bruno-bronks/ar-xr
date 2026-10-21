"""Execucao de comandos externos (docker/compose) com injecao para testes (SPEC-012). So stdlib."""

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class Result:
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class Runner(Protocol):
    def run(
        self,
        args: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        stdout_path: Path | None = None,
        stdin_path: Path | None = None,
    ) -> Result: ...


class SubprocessRunner:
    """Roda o comando SEM shell. `env` e somado ao ambiente atual; nunca e registrado."""

    def run(
        self,
        args: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        stdout_path: Path | None = None,
        stdin_path: Path | None = None,
    ) -> Result:
        merged = {**os.environ, **(env or {})}
        stdin = stdin_path.open("rb") if stdin_path else None
        stdout = stdout_path.open("wb") if stdout_path else subprocess.PIPE
        try:
            try:
                done = subprocess.run(  # noqa: S603
                    list(args),
                    env=merged,
                    timeout=timeout,
                    stdin=stdin,
                    stdout=stdout,
                    stderr=subprocess.PIPE,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return Result(124, "", "timeout")
            except FileNotFoundError:
                return Result(127, "", f"command not found: {args[0]}")
        finally:
            if stdin:
                stdin.close()
            if stdout_path and not isinstance(stdout, int):
                stdout.close()
        out = "" if stdout_path else done.stdout.decode("utf-8", "replace")
        return Result(done.returncode, out, done.stderr.decode("utf-8", "replace"))
