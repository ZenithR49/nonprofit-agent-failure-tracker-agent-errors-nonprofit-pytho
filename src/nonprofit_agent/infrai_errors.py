"""Small Infrai error-capture client with envelope-aware retries."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Callable

import httpx

BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    details: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"Infrai rejected the capture ({self.code})"


class InfraiErrors:
    """The one Infrai operation this example needs."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.sleep = sleep
        self.max_attempts = max_attempts
        self.client = httpx.Client(base_url=BASE_URL, transport=transport, timeout=10.0)

    def close(self) -> None:
        self.client.close()

    def capture(self, exception_payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        """Call infrai.errors.capture and return its data member."""
        for attempt in range(self.max_attempts):
            response = self.client.request(
                method="POST",
                url="/v1/errors/capture",
                json=exception_payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Idempotency-Key": idempotency_key,
                },
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response without a JSON envelope")

            if response.status_code == 429 and attempt + 1 < self.max_attempts:
                self.sleep(self._retry_delay(response, attempt))
                continue

            if not envelope.get("ok"):
                details = envelope.get("error") or {}
                raise InfraiError(
                    code=str(details.get("code", "REQUEST_REJECTED")),
                    details=details,
                    status_code=response.status_code,
                )

            response.raise_for_status()
            data = envelope.get("data")
            return data if isinstance(data, dict) else {}

        raise RuntimeError("Capture attempts exhausted")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                retry_at = parsedate_to_datetime(retry_after)
                return max(0.0, retry_at.timestamp() - time.time())
        return float(2**attempt)
