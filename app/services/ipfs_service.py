from __future__ import annotations

import asyncio

import aiohttp

from app.core.config import Settings
from app.core.exceptions import IPFSDownloadError


class IPFSService:
    """Download GeoJSON objects from Pinata with bounded concurrency and retries."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._session: aiohttp.ClientSession | None = None
        # Semaphore prevents burst fan-out when historical CID lists become large.
        self._sem = asyncio.Semaphore(settings.max_concurrent_downloads)

    async def startup(self) -> None:
        timeout = aiohttp.ClientTimeout(total=self.settings.ipfs_timeout_seconds)
        headers = {"Authorization": f"Bearer {self.settings.pinata_jwt}"}
        self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)

    async def shutdown(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def download_geojson_batch(self, cell_ids: list[str]) -> dict[str, dict]:
        """Fetch all CID documents concurrently and fail if any CID cannot be retrieved."""
        unique_cell_ids = list(dict.fromkeys(cell_ids))
        if not unique_cell_ids:
            return {}

        tasks = [self._download_geojson(cid) for cid in unique_cell_ids]
        # Batch timeout bounds total waiting time for the whole CID set.
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=self.settings.batch_timeout_seconds,
        )

        output: dict[str, dict] = {}
        failed: list[str] = []
        for idx, result in enumerate(results):
            cid = unique_cell_ids[idx]
            if isinstance(result, Exception):
                failed.append(cid)
                continue
            output[cid] = result

        if failed:
            raise IPFSDownloadError(f"Failed to download GeoJSON for CIDs: {failed}")

        return output

    async def _download_geojson(self, cell_id: str) -> dict:
        """Download one CID and apply a short retry policy on rate limiting."""
        if self._session is None:
            raise IPFSDownloadError("IPFS HTTP session is not initialized")

        url = f"{self.settings.pinata_gateway_base_url.rstrip('/')}/{cell_id}"

        async with self._sem:
            for attempt in range(3):
                async with self._session.get(url) as response:
                    if response.status == 200:
                        content_type = response.headers.get("Content-Type", "")
                        if "json" not in content_type and content_type:
                            raise IPFSDownloadError(
                                f"CID {cell_id} returned non-JSON content-type: {content_type}"
                            )
                        return await response.json()

                    if response.status == 429:
                        if attempt < 2:
                            # Respect Retry-After when present, otherwise use a small fallback delay.
                            retry_after = response.headers.get("Retry-After")
                            sleep_seconds = float(retry_after) if retry_after and retry_after.isdigit() else 1.0
                            await asyncio.sleep(max(0.5, sleep_seconds))
                            continue
                        break

                    text = await response.text()
                    raise IPFSDownloadError(
                        f"Failed to fetch CID {cell_id}. Status {response.status}. Body: {text[:300]}"
                    )

        raise IPFSDownloadError(f"Exceeded retries for CID {cell_id}")
