from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.validate_polygon import router as validate_router
from app.core.config import get_settings
from app.services.ipfs_service import IPFSService
from app.services.spatial_service import SpatialService
from app.services.validation_service import ValidationService
from app.services.web3_service import Web3Service


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    web3_service = Web3Service(settings=settings)
    ipfs_service = IPFSService(settings=settings)
    spatial_service = SpatialService()
    validation_service = ValidationService(
        web3_service=web3_service,
        ipfs_service=ipfs_service,
        spatial_service=spatial_service,
    )

    await ipfs_service.startup()

    app.state.settings = settings
    app.state.web3_service = web3_service
    app.state.ipfs_service = ipfs_service
    app.state.spatial_service = spatial_service
    app.state.validation_service = validation_service

    yield

    await ipfs_service.shutdown()


app = FastAPI(title="Area Validation API", version="0.1.0", lifespan=lifespan)

app.include_router(health_router)
app.include_router(validate_router)
