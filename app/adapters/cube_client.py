"""HTTP adapter for the Cube semantic-layer API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from app.domain.exceptions import (
    CubeConnectionError,
    CubeResponseError,
    CubeTimeoutError,
)


class CubeClient:
    """Execute analytical queries exclusively through Cube."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        token: str | None = None,
    ) -> None:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if token:
            headers["Authorization"] = token

        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers=headers,
        )

    def load(self, query: Mapping[str, Any]) -> list[dict[str, Any]]:
        """Run a validated Cube query and return its data rows."""
        try:
            response = self._client.post(
                "/load",
                json={"query": dict(query)},
            )
            response.raise_for_status()
        except httpx.TimeoutException as error:
            raise CubeTimeoutError(
                "Cube exceeded the configured timeout."
            ) from error
        except httpx.HTTPStatusError as error:
            detail = self._extract_error(error.response)
            raise CubeResponseError(
                f"Cube rejected the query: {detail}"
            ) from error
        except httpx.RequestError as error:
            raise CubeConnectionError("Cube could not be reached.") from error

        try:
            payload = response.json()
        except ValueError as error:
            raise CubeResponseError(
                "Cube returned a non-JSON response."
            ) from error

        data = payload.get("data")

        if not isinstance(data, list):
            raise CubeResponseError(
                "Cube response does not contain a data list."
            )

        if not all(isinstance(row, dict) for row in data):
            raise CubeResponseError(
                "Cube returned an invalid row structure."
            )

        return data

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self) -> CubeClient:
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()

    @staticmethod
    def _extract_error(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text or f"HTTP {response.status_code}"

        message = payload.get("error")

        if isinstance(message, str) and message:
            return message

        return f"HTTP {response.status_code}"
