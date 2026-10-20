"""Adaptador da API Messages da Anthropic (SPEC-009, D-018). OPCIONAL e desligado por padrao.

NAO foi exercitado contra a API real (sem chave/aprovacao): so testado com transporte simulado.
Sem SDK (uma chamada HTTPS via urllib). Timeout, disjuntor e erros sem detalhes do provedor.
"""

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping

from spatial_assistant.llm import LlmUnavailable

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
FAILURES_TO_OPEN = 3
OPEN_SECONDS = 30.0
MAX_TOKENS = 600

type HttpPost = Callable[[str, Mapping[str, str], bytes, float], tuple[int, bytes]]


def urllib_post(
    url: str, headers: Mapping[str, str], body: bytes, timeout: float
) -> tuple[int, bytes]:
    if not url.startswith("https://"):
        raise ValueError("only https is allowed")
    request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return int(response.status), bytes(response.read(1_000_000))
    except urllib.error.HTTPError as error:
        return error.code, b""


class AnthropicProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        post: HttpPost | None = None,
        clock: Callable[[], float] = time.monotonic,
        timeout_s: float = 10.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._post: HttpPost = post or urllib_post
        self._clock = clock
        self._timeout_s = timeout_s
        self._failures = 0
        self._open_until = 0.0

    def __repr__(self) -> str:
        return f"AnthropicProvider(model={self._model!r})"

    def complete(self, system: str, user: str) -> str:
        now = self._clock()
        if now < self._open_until:
            raise LlmUnavailable("circuit open")
        body = json.dumps(
            {
                "model": self._model,
                "max_tokens": MAX_TOKENS,
                "temperature": 0,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            }
        ).encode()
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }
        try:
            status, payload = self._post(API_URL, headers, body, self._timeout_s)
            text = _extract_text(status, payload)
        except LlmUnavailable:
            self._record_failure(now)
            raise
        except (OSError, TimeoutError, ValueError):
            self._record_failure(now)
            raise LlmUnavailable("transport error") from None
        self._failures = 0
        return text

    def _record_failure(self, now: float) -> None:
        self._failures += 1
        if self._failures >= FAILURES_TO_OPEN:
            self._open_until = now + OPEN_SECONDS


def _extract_text(status: int, payload: bytes) -> str:
    if status != 200:
        raise LlmUnavailable(f"http status {status}")
    try:
        data = json.loads(payload)
    except ValueError:
        raise LlmUnavailable("invalid response") from None
    blocks = data.get("content") if isinstance(data, dict) else None
    if isinstance(blocks, list):
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str):
                    return text
    raise LlmUnavailable("unexpected response shape")
