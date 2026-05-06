from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.core.exceptions import BlockchainReadError
from app.services.web3_service import Web3Service


def _build_settings(max_approved_cells: int = 10) -> Settings:
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
            "MAX_APPROVED_CELLS": max_approved_cells,
        }
    )


@pytest.mark.anyio
async def test_get_approved_cell_ids_enforces_max():
    service = Web3Service(settings=_build_settings(max_approved_cells=2))
    service.settings.max_approved_cells = 2
    service._read_approved_cell_ids_with_retry = AsyncMock(return_value=["a", "b", "c"])  # type: ignore[assignment]

    with pytest.raises(BlockchainReadError, match="too large"):
        await service.get_approved_cell_ids()


@pytest.mark.anyio
async def test_read_approved_cell_ids_with_retry_succeeds_after_retry(monkeypatch: pytest.MonkeyPatch):
    service = Web3Service(settings=_build_settings())

    calls = {"count": 0}

    async def fake_to_thread(func):
        calls["count"] += 1
        if calls["count"] < 2:
            raise RuntimeError("boom")
        return ["cid-1", "cid-2"]

    async def fake_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    result = await service._read_approved_cell_ids_with_retry()

    assert result == ["cid-1", "cid-2"]
    assert calls["count"] == 2


@pytest.mark.anyio
async def test_read_approved_cell_ids_with_retry_raises_after_retries(monkeypatch: pytest.MonkeyPatch):
    service = Web3Service(settings=_build_settings())

    async def fake_to_thread(func):
        raise RuntimeError("boom")

    async def fake_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    with pytest.raises(BlockchainReadError, match="Failed reading approved cell ids"):
        await service._read_approved_cell_ids_with_retry()
