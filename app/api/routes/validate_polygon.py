from fastapi import APIRouter, HTTPException, Request, status

from app.core.exceptions import BlockchainReadError, GeometryValidationError, IPFSDownloadError
from app.models.schemas import ValidatePolygonRequest, ValidatePolygonResponse

router = APIRouter(tags=["validation"])


@router.post("/validate-polygon", response_model=ValidatePolygonResponse)
async def validate_polygon(payload: ValidatePolygonRequest, request: Request) -> ValidatePolygonResponse:
    validation_service = request.app.state.validation_service

    try:
        return await validation_service.validate_polygon(payload.cell_id)
    except BlockchainReadError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Blockchain read error: {exc}",
        ) from exc
    except IPFSDownloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"IPFS download error: {exc}",
        ) from exc
    except GeometryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Geometry validation error: {exc}",
        ) from exc
