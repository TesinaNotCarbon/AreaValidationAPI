from __future__ import annotations

import asyncio

import pytest

from app.core.config import Settings
from app.core.exceptions import IPFSDownloadError
from app.services.ipfs_service import IPFSService


class FakeResponse:
    def __init__(self, status: int, headers: dict[str, str] | None = None, json_data=None, text_data: str = ""):
        self.status = status
        self.headers = headers or {}
        self._json_data = json_data
        self._text_data = text_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self._json_data

    async def text(self):
        return self._text_data


class FakeSession:
    def __init__(self, responses: list[FakeResponse]):
        self._responses = iter(responses)
        self.closed = False

    def get(self, url: str) -> FakeResponse:
        return next(self._responses)

    async def close(self) -> None:
        self.closed = True


def _build_settings() -> Settings:
    return Settings(
        **{
            "APP_NAME": "AreaValidationAPI",
            "APP_ENV": "test",
            "LOG_LEVEL": "INFO",
            "HOST": "127.0.0.1",
            "PORT": 8001,
            "ETH_RPC_URL": "https://rpc.example.invalid",
            "PROJECT_MANAGER_ADDRESS": "0x1111111111111111111111111111111111111111",
            "PROJECT_MANAGER_ABI": "[]",
            "PINATA_GATEWAY_BASE_URL": "https://gateway.example.invalid/ipfs",
            "PINATA_JWT": "test-jwt",
            "RPC_TIMEOUT_SECONDS": 1,
            "IPFS_TIMEOUT_SECONDS": 2,
            "BATCH_TIMEOUT_SECONDS": 3,
            "MAX_CONCURRENT_DOWNLOADS": 5,
            "MAX_APPROVED_CELLS": 10,
        }
    )


@pytest.mark.anyio
async def test_download_geojson_batch_empty_returns_empty():
    service = IPFSService(settings=_build_settings())
    assert await service.download_geojson_batch([]) == {}


@pytest.mark.anyio
async def test_download_geojson_batch_aggregates_failures():
    service = IPFSService(settings=_build_settings())

    async def fake_download(cell_id: str) -> dict:
        if cell_id == "bad":
            raise IPFSDownloadError("boom")
        return {"type": "Polygon", "coordinates": []}

    service._download_geojson = fake_download  # type: ignore[assignment]

    with pytest.raises(IPFSDownloadError, match="Failed to download GeoJSON"):
        await service.download_geojson_batch(["ok", "bad"])


@pytest.mark.anyio
async def test_download_geojson_batch_returns_map():
    service = IPFSService(settings=_build_settings())

    async def fake_download(cell_id: str) -> dict:
        return {"id": cell_id}

    service._download_geojson = fake_download  # type: ignore[assignment]

    result = await service.download_geojson_batch(["a", "b", "a"])

    assert result == {"a": {"id": "a"}, "b": {"id": "b"}}


@pytest.mark.anyio
async def test_startup_initializes_session_with_auth_header():
    service = IPFSService(settings=_build_settings())

    await service.startup()

    assert service._session is not None
    assert service._session.headers.get("Authorization") == "Bearer test-jwt"

    await service.shutdown()


@pytest.mark.anyio
async def test_shutdown_closes_session():
    service = IPFSService(settings=_build_settings())
    fake_session = FakeSession([])
    service._session = fake_session

    await service.shutdown()

    assert fake_session.closed is True
    assert service._session is None


@pytest.mark.anyio
async def test_download_geojson_success_json():
    service = IPFSService(settings=_build_settings())
    service._session = FakeSession(
        [
            FakeResponse(
                status=200,
                headers={"Content-Type": "application/json"},
                json_data={"type": "Polygon", "coordinates": []},
            )
        ]
    )

    result = await service._download_geojson("cid-1")

    assert result == {"type": "Polygon", "coordinates": []}


@pytest.mark.anyio
async def test_download_geojson_retries_after_rate_limit(monkeypatch: pytest.MonkeyPatch):
    service = IPFSService(settings=_build_settings())
    service._session = FakeSession(
        [
            FakeResponse(status=429, headers={"Retry-After": "1"}, text_data="rate limit"),
            FakeResponse(status=200, headers={"Content-Type": "application/json"}, json_data={"ok": True}),
        ]
    )

    async def fake_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    result = await service._download_geojson("cid-1")

    assert result == {"ok": True}


@pytest.mark.anyio
async def test_download_geojson_rejects_non_json():
    service = IPFSService(settings=_build_settings())
    service._session = FakeSession(
        [FakeResponse(status=200, headers={"Content-Type": "text/plain"}, text_data="nope")]
    )

    with pytest.raises(IPFSDownloadError, match="non-JSON content-type"):
        await service._download_geojson("cid-1")


@pytest.mark.anyio
async def test_download_geojson_raises_on_error_status():
    service = IPFSService(settings=_build_settings())
    service._session = FakeSession(
        [FakeResponse(status=500, headers={"Content-Type": "text/plain"}, text_data="boom")]
    )

    with pytest.raises(IPFSDownloadError, match="Failed to fetch CID"):
        await service._download_geojson("cid-1")


@pytest.mark.anyio
async def test_download_geojson_batch_reports_failed_cids():
    service = IPFSService(settings=_build_settings())

    async def fake_download(cell_id: str) -> dict:
        if cell_id == "bad":
            raise IPFSDownloadError("boom")
        return {"ok": True}

    service._download_geojson = fake_download  # type: ignore[assignment]

    with pytest.raises(IPFSDownloadError, match="\['bad'\]"):
        await service.download_geojson_batch(["ok", "bad"])


@pytest.mark.anyio
async def test_download_geojson_exceeded_retries():
    service = IPFSService(settings=_build_settings())
    service._session = FakeSession(
        [
            FakeResponse(status=429, headers={}, text_data="rate limit"),
            FakeResponse(status=429, headers={}, text_data="rate limit"),
            FakeResponse(status=429, headers={}, text_data="rate limit"),
        ]
    )

    with pytest.raises(IPFSDownloadError, match="Exceeded retries"):
        await service._download_geojson("cid-1")
