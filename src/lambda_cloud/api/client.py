"""HTTP client for the Lambda Cloud API.

Handles authentication, the documented rate limits (1 request/second in
general), retries on ``429 Too Many Requests``, and conversion of error
responses into :class:`~lambda_cloud.errors.APIError` exceptions.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from .. import __version__
from ..core.errors import APIError

DEFAULT_BASE_URL = "https://cloud.lambda.ai/api/v1"
BASE_URL_ENV_VAR = "LAMBDA_CLOUD_API_URL"
MIN_INTERVAL_ENV_VAR = "LAMBDA_CLOUD_MIN_INTERVAL"

#: Default minimum delay between two API calls, per the documented rate limit.
DEFAULT_MIN_INTERVAL_SECONDS = 1.05

#: Maximum number of retries after a 429 response.
DEFAULT_MAX_RETRIES = 3


class LambdaCloudClient:
    """Thin wrapper around :class:`httpx.Client` for the Lambda Cloud API."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        timeout: float = 30.0,
        min_interval: float | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        resolved_base_url = base_url or os.environ.get(BASE_URL_ENV_VAR) or DEFAULT_BASE_URL
        if min_interval is None:
            min_interval = float(
                os.environ.get(MIN_INTERVAL_ENV_VAR, DEFAULT_MIN_INTERVAL_SECONDS)
            )
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._last_request_at = 0.0
        self._client = httpx.Client(
            base_url=resolved_base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "User-Agent": f"lambda-cloud-cli/{__version__}",
            },
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> LambdaCloudClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> dict[str, Any]:
        """Perform one API call (with retries) and return the raw payload."""
        for attempt in range(self._max_retries + 1):
            self._throttle()
            response = self._client.request(method, path, params=params, json=json)

            if response.status_code == 429 and attempt < self._max_retries:
                time.sleep(self._retry_delay(response))
                continue

            if not response.is_success:
                raise APIError.from_response(response)

            if response.status_code == 204 or not response.content:
                return {}
            payload = response.json()
            return payload if isinstance(payload, dict) else {"data": payload}

        # Unreachable in practice: the last attempt either returns or raises.
        raise APIError(429, "global/rate-limited", "Too many requests after retries.")

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> Any:
        """Perform an API call and return the unwrapped ``data`` payload.

        Raises:
            APIError: if the API responds with a non-2xx status.
        """
        return self._request(method, path, params=params, json=json).get("data")

    def get_page(
        self, path: str, *, params: dict[str, Any] | None = None
    ) -> tuple[Any, str | None]:
        """GET an endpoint that paginates with a top-level ``page_token``."""
        payload = self._request("GET", path, params=params)
        return payload.get("data"), payload.get("page_token")

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(
        self, path: str, *, json: Any | None = None, params: dict[str, Any] | None = None
    ) -> Any:
        return self.request("POST", path, json=json, params=params)

    def patch(self, path: str, *, json: Any | None = None) -> Any:
        return self.request("PATCH", path, json=json)

    def put(self, path: str, *, json: Any | None = None) -> Any:
        return self.request("PUT", path, json=json)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)

    def _throttle(self) -> None:
        """Enforce the minimum interval between two API requests."""
        if self._min_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_at = time.monotonic()

    @staticmethod
    def _retry_delay(response: httpx.Response) -> float:
        try:
            return min(float(response.headers.get("Retry-After", "1")), 30.0)
        except ValueError:
            return 1.0
