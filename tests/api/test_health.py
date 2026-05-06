from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_health_returns_settings(async_client):
    response = await async_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["details"]["env"] == "test"
    assert data["details"]["rpc_timeout_seconds"] == 1
    assert data["details"]["ipfs_timeout_seconds"] == 2
    assert data["details"]["max_concurrent_downloads"] == 5
