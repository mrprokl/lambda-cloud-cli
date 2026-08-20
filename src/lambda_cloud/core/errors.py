"""Exceptions raised by lambda-cloud."""

from __future__ import annotations

import httpx


class LambdaCloudError(Exception):
    """Base class for all lambda-cloud errors."""


class ConfigError(LambdaCloudError):
    """Local configuration is missing or invalid."""


class APIError(LambdaCloudError):
    """The Lambda Cloud API returned an error response.

    Attributes:
        status_code: HTTP status code of the response.
        code: Machine-readable error code returned by the API
            (e.g. ``global/invalid-api-key``).
        message: Human-readable explanation returned by the API.
        suggestion: Optional hint returned by the API on how to fix the error.
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(f"{code}: {message}")
        self.status_code = status_code
        self.code = code
        self.message = message
        self.suggestion = suggestion

    @classmethod
    def from_response(cls, response: httpx.Response) -> APIError:
        """Build an :class:`APIError` from a failed API response."""
        try:
            payload = response.json()
        except ValueError:
            return cls(
                response.status_code,
                "http/unexpected-response",
                f"HTTP {response.status_code}: non-JSON response body",
            )

        error = payload.get("error") or {}
        return cls(
            status_code=response.status_code,
            code=error.get("code", "unknown"),
            message=error.get("message", response.text or "Unknown error"),
            suggestion=error.get("suggestion"),
        )
