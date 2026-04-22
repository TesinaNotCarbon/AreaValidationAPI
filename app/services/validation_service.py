from __future__ import annotations

import time
import uuid

from app.models.schemas import ValidatePolygonResponse, ValidationTimings
from app.services.ipfs_service import IPFSService
from app.services.spatial_service import SpatialService
from app.services.web3_service import Web3Service


class ValidationService:
    """Orchestrates on-chain lookup, IPFS fetch, and spatial overlap validation."""

    def __init__(
        self,
        web3_service: Web3Service,
        ipfs_service: IPFSService,
        spatial_service: SpatialService,
    ) -> None:
        self.web3_service = web3_service
        self.ipfs_service = ipfs_service
        self.spatial_service = spatial_service

    async def validate_polygon(self, new_cell_id: str) -> ValidatePolygonResponse:
        """Run the full validation pipeline and return overlap plus stage timings."""
        trace_id = str(uuid.uuid4())
        start_total = time.perf_counter()

        # Stage 1: read the approved CID list from ProjectManager.
        start_blockchain = time.perf_counter()
        approved_cell_ids = await self.web3_service.get_approved_cell_ids()
        blockchain_ms = (time.perf_counter() - start_blockchain) * 1000

        # Deduplicate while preserving order to avoid repeated IPFS downloads.
        to_download = list(dict.fromkeys([new_cell_id, *approved_cell_ids]))

        # Stage 2: fetch all required GeoJSON documents concurrently from Pinata.
        start_ipfs = time.perf_counter()
        geojson_map = await self.ipfs_service.download_geojson_batch(to_download)
        ipfs_ms = (time.perf_counter() - start_ipfs) * 1000

        # Stage 3: run geometric overlap checks in a single UTM CRS.
        start_spatial = time.perf_counter()
        spatial_result = self.spatial_service.validate_overlap(
            new_cell_id=new_cell_id,
            geojson_map=geojson_map,
            approved_cell_ids=approved_cell_ids,
        )
        spatial_ms = (time.perf_counter() - start_spatial) * 1000

        total_ms = (time.perf_counter() - start_total) * 1000

        # Output keeps matched CID list and per-stage latency for oracle observability.
        response = ValidatePolygonResponse(
            overlap=spatial_result.overlap,
            matched_cell_ids=spatial_result.matched_cell_ids,
            checked_count=spatial_result.checked_count,
            trace_id=trace_id,
            timings=ValidationTimings(
                blockchain_ms=round(blockchain_ms, 2),
                ipfs_ms=round(ipfs_ms, 2),
                spatial_ms=round(spatial_ms, 2),
                total_ms=round(total_ms, 2),
            ),
            inconclusive=False,
            reason=None,
        )
        return response
