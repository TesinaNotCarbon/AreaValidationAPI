from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routes.health import router as health_router
from app.api.routes.validate_polygon import router as validate_router
from app.core.config import Settings


@pytest.fixture()
def settings() -> Settings:
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


@pytest.fixture()
def mock_validation_service() -> AsyncMock:
    service = AsyncMock()
    service.validate_polygon = AsyncMock()
    return service


@pytest.fixture()
def test_app(settings: Settings, mock_validation_service: AsyncMock) -> FastAPI:
    app = FastAPI()
    app.include_router(health_router)
    app.include_router(validate_router)

    app.state.settings = settings
    app.state.validation_service = mock_validation_service
    return app


@pytest.fixture()
async def async_client(test_app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
