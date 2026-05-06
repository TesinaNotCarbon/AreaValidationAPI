from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import BlockchainReadError, GeometryValidationError, IPFSDownloadError
from app.models.schemas import ValidatePolygonResponse, ValidationTimings


@pytest.mark.anyio
async def test_validate_polygon_success(async_client, test_app):
    response_payload = ValidatePolygonResponse(
        overlap=False,
        matched_cell_ids=[],
        checked_count=3,
        trace_id="trace-1",
        timings=ValidationTimings(
            blockchain_ms=1.0,
            ipfs_ms=2.0,
            spatial_ms=3.0,
            total_ms=6.0,
        ),
        inconclusive=False,
        reason=None,
    )

    test_app.state.validation_service.validate_polygon = AsyncMock(return_value=response_payload)

    response = await async_client.post("/validate-polygon", json={"cell_id": "valid-cell-id"})

    assert response.status_code == 200
    data = response.json()
    assert data["overlap"] is False
    assert data["checked_count"] == 3
    assert data["trace_id"] == "trace-1"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "exc,status_code,detail_prefix",
    [
        (BlockchainReadError("boom"), 503, "Blockchain read error"),
        (IPFSDownloadError("boom"), 503, "IPFS download error"),
        (GeometryValidationError("boom"), 422, "Geometry validation error"),
    ],
)
async def test_validate_polygon_error_mapping(async_client, test_app, exc, status_code, detail_prefix):
    test_app.state.validation_service.validate_polygon = AsyncMock(side_effect=exc)

    response = await async_client.post("/validate-polygon", json={"cell_id": "valid-cell-id"})

    assert response.status_code == status_code
    data = response.json()
    assert data["detail"].startswith(detail_prefix)
