from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.models.schemas import ValidatePolygonResponse
from app.services.validation_service import ValidationService


@pytest.mark.anyio
async def test_validate_polygon_orchestrates_and_deduplicates():
    web3_service = AsyncMock()
    web3_service.get_approved_cell_ids = AsyncMock(return_value=["old-1", "old-2", "old-1"])

    ipfs_service = AsyncMock()
    ipfs_service.download_geojson_batch = AsyncMock(
        return_value={
            "new-1": {"type": "Polygon", "coordinates": []},
            "old-1": {"type": "Polygon", "coordinates": []},
            "old-2": {"type": "Polygon", "coordinates": []},
        }
    )

    spatial_service = Mock()
    spatial_service.validate_overlap = Mock(
        return_value=SimpleNamespace(
            overlap=True,
            matched_cell_ids=["old-2"],
            checked_count=2,
        )
    )

    service = ValidationService(
        web3_service=web3_service,
        ipfs_service=ipfs_service,
        spatial_service=spatial_service,
    )

    response = await service.validate_polygon("new-1")

    assert isinstance(response, ValidatePolygonResponse)
    assert response.overlap is True
    assert response.matched_cell_ids == ["old-2"]
    assert response.checked_count == 2
    assert response.trace_id
    assert response.timings.blockchain_ms >= 0
    assert response.timings.ipfs_ms >= 0
    assert response.timings.spatial_ms >= 0
    assert response.timings.total_ms >= 0

    ipfs_service.download_geojson_batch.assert_called_once_with(["new-1", "old-1", "old-2"])
    spatial_service.validate_overlap.assert_called_once()
