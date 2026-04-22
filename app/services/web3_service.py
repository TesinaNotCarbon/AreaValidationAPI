from __future__ import annotations

import asyncio
import json

from web3 import Web3

from app.core.config import Settings
from app.core.exceptions import BlockchainReadError


class Web3Service:
    """Read approved project CIDs from ProjectManager with bounded retry/backoff."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        provider = Web3.HTTPProvider(
            endpoint_uri=settings.eth_rpc_url,
            request_kwargs={"timeout": settings.rpc_timeout_seconds},
        )
        self.w3 = Web3(provider)
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(settings.project_manager_address),
            abi=json.loads(settings.project_manager_abi),
        )

    async def get_approved_cell_ids(self) -> list[str]:
        """Return approved CIDs and enforce an upper bound for API safety."""
        result = await self._read_approved_cell_ids_with_retry()

        if len(result) > self.settings.max_approved_cells:
            raise BlockchainReadError("Approved cell list is too large for this API configuration")
        return result

    async def _read_approved_cell_ids_with_retry(self) -> list[str]:
        """Retry transient RPC failures with exponential backoff."""
        retries = 3
        backoff = [0.5, 1.0, 2.0]

        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                # web3.py call() is synchronous, so it is offloaded to a worker thread.
                raw_result = await asyncio.to_thread(self._sync_get_approved_cell_ids)
                return [str(item) for item in raw_result]
            except Exception as exc:
                last_exc = exc
                if attempt < retries - 1:
                    await asyncio.sleep(backoff[attempt])

        raise BlockchainReadError(f"Failed reading approved cell ids: {last_exc}") from last_exc

    def _sync_get_approved_cell_ids(self) -> list[str]:
        return self.contract.functions.getApprovedCellIds().call()
