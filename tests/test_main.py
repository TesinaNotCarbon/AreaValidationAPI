from __future__ import annotations

from fastapi import FastAPI
import pytest

import app.main as main_module


class FakeWeb3Service:
    def __init__(self, settings):
        self.settings = settings


class FakeIPFSService:
    def __init__(self, settings):
        self.settings = settings
        self.startup_called = False
        self.shutdown_called = False

    async def startup(self):
        self.startup_called = True

    async def shutdown(self):
        self.shutdown_called = True


class FakeSpatialService:
    pass


class FakeValidationService:
    def __init__(self, web3_service, ipfs_service, spatial_service):
        self.web3_service = web3_service
        self.ipfs_service = ipfs_service
        self.spatial_service = spatial_service


@pytest.mark.anyio
async def test_lifespan_initializes_and_shuts_down_services(monkeypatch, settings):
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "Web3Service", FakeWeb3Service)
    monkeypatch.setattr(main_module, "IPFSService", FakeIPFSService)
    monkeypatch.setattr(main_module, "SpatialService", FakeSpatialService)
    monkeypatch.setattr(main_module, "ValidationService", FakeValidationService)

    app = FastAPI()

    async with main_module.lifespan(app):
        assert app.state.settings is settings
        assert isinstance(app.state.web3_service, FakeWeb3Service)
        assert isinstance(app.state.ipfs_service, FakeIPFSService)
        assert isinstance(app.state.spatial_service, FakeSpatialService)
        assert isinstance(app.state.validation_service, FakeValidationService)
        assert app.state.web3_service.settings is settings
        assert app.state.ipfs_service.settings is settings
        assert app.state.validation_service.web3_service is app.state.web3_service
        assert app.state.validation_service.ipfs_service is app.state.ipfs_service
        assert app.state.validation_service.spatial_service is app.state.spatial_service
        assert app.state.ipfs_service.startup_called is True
        assert app.state.ipfs_service.shutdown_called is False

    assert app.state.ipfs_service.shutdown_called is True


def test_app_metadata_and_routes_are_registered():
    paths = {route.path for route in main_module.app.routes}

    assert main_module.app.title == "Area Validation API"
    assert main_module.app.version == "0.1.0"
    assert "/health" in paths
    assert "/validate-polygon" in paths
