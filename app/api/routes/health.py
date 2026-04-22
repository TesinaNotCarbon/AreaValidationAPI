from fastapi import APIRouter, Request

from app.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings

    return HealthResponse(
        status="ok",
        details={
            "env": settings.app_env,
            "rpc_timeout_seconds": settings.rpc_timeout_seconds,
            "ipfs_timeout_seconds": settings.ipfs_timeout_seconds,
            "max_concurrent_downloads": settings.max_concurrent_downloads,
        },
    )
