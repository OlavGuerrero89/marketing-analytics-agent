"""Unit tests for the Cube HTTP adapter."""
from __future__ import annotations

import httpx
import pytest
import respx

from app.adapters.cube_client import CubeClient
from app.domain.exceptions import CubeResponseError, CubeTimeoutError

BASE_URL = "http://cube:4000/cubejs-api/v1"
LOAD_URL = f"{BASE_URL}/load"
SAMPLE_QUERY = {
    "measures": ["marketing_performance.spend"],
    "dimensions": ["marketing_performance.channel"],
}


@respx.mock
def test_load_returns_rows_and_sends_expected_query() -> None:
    """A successful response returns rows without leaking transport details."""
    route = respx.post(LOAD_URL).mock(
        return_value=httpx.Response(
            200,
            json={"data": [{"marketing_performance.spend": "125.50"}]},
        )
    )

    with CubeClient(BASE_URL, timeout_seconds=5.0) as client:
        rows = client.load(SAMPLE_QUERY)

    assert rows == [{"marketing_performance.spend": "125.50"}]
    assert route.called
    assert route.calls.last.request.read()
    assert route.calls.last.request.headers["content-type"] == "application/json"
    assert route.calls.last.request.url == httpx.URL(LOAD_URL)
    assert route.calls.last.request.content == (
        b'{"query":{"measures":["marketing_performance.spend"],'
        b'"dimensions":["marketing_performance.channel"]}}'
    )


@respx.mock
def test_load_translates_timeout() -> None:
    """Transport timeouts become a domain-specific exception."""
    respx.post(LOAD_URL).mock(
        side_effect=httpx.ReadTimeout("timed out")
    )

    with CubeClient(BASE_URL, timeout_seconds=0.1) as client:
        with pytest.raises(
            CubeTimeoutError,
            match="configured timeout",
        ):
            client.load(SAMPLE_QUERY)


@respx.mock
def test_load_preserves_cube_error_message() -> None:
    """Cube validation errors are exposed without returning raw HTTP errors."""
    respx.post(LOAD_URL).mock(
        return_value=httpx.Response(
            400,
            json={"error": "Unknown measure"},
        )
    )

    with CubeClient(BASE_URL, timeout_seconds=5.0) as client:
        with pytest.raises(
            CubeResponseError,
            match="Cube rejected the query: Unknown measure",
        ):
            client.load(SAMPLE_QUERY)


@respx.mock
def test_load_rejects_non_json_response() -> None:
    """A successful status with a malformed body is not accepted as data."""
    respx.post(LOAD_URL).mock(
        return_value=httpx.Response(
            200,
            content=b"not-json",
            headers={"Content-Type": "text/plain"},
        )
    )

    with CubeClient(BASE_URL, timeout_seconds=5.0) as client:
        with pytest.raises(
            CubeResponseError,
            match="non-JSON response",
        ):
            client.load(SAMPLE_QUERY)


@respx.mock
def test_load_rejects_response_without_data_list() -> None:
    """The adapter enforces Cube's expected data-list contract."""
    respx.post(LOAD_URL).mock(
        return_value=httpx.Response(200, json={"query": SAMPLE_QUERY})
    )

    with CubeClient(BASE_URL, timeout_seconds=5.0) as client:
        with pytest.raises(
            CubeResponseError,
            match="does not contain a data list",
        ):
            client.load(SAMPLE_QUERY)
