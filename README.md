# AreaValidationAPI

Stateless FastAPI service that validates whether a new project polygon overlaps with already approved project polygons in a Web3 carbon-credit workflow.

## Problem This API Solves

In reforestation-based carbon credit systems, polygon overlap can cause double counting.
This API provides an oracle-ready validation step that:

- Reads approved project CIDs from the blockchain.
- Downloads GeoJSON polygons from IPFS (Pinata gateway).
- Reprojects geometries to a metric CRS.
- Runs topology checks to detect spatial conflicts.

The service is intentionally stateless and processes each request on the fly.

## High-Level Architecture

The API is composed of four service layers:

- Web3Service: reads approved CIDs from ProjectManager through web3.py.
- IPFSService: downloads all required GeoJSON documents concurrently with aiohttp.
- SpatialService: parses, reprojects, and evaluates geometric intersections.
- ValidationService: orchestrates the full validation pipeline and stage timings.

No external cache or database is used.

## End-to-End Validation Flow

1. Client calls POST /validate-polygon with the new cell CID.
2. API calls ProjectManager.getApprovedCellIds() via RPC.
3. API downloads GeoJSON documents for the new CID and all approved CIDs.
4. API computes a UTM EPSG from the new polygon centroid.
5. API reprojects all geometries from EPSG:4326 to the selected UTM CRS.
6. API checks the new geometry against historical geometries.
7. API returns overlap result, matching CIDs, checked count, trace_id, and timings.

## Algorithms and Technical Notes

### 1) Two-Phase Topology Validation (Shapely / GEOS)

To ensure high-performance spatial overlap detection without a database, the API evaluates geometries in memory using `Shapely` (powered by the C++ `GEOS` engine). The validation runs a highly optimized two-phase algorithm:

*   **Phase 1: Bounding Box Filter (AABB):** Before calculating complex vertices, the algorithm draws an Axis-Aligned Bounding Box (AABB) around the maximum spatial limits (North, South, East, West) of both polygons. If the rectangular boxes do not intersect, the algorithm instantly returns `false` (no overlap), saving significant computational resources.
*   **Phase 2: Exact Intersection (DE-9IM):** If the bounding boxes touch, the engine proceeds to an exact topological validation using the Dimensionally Extended nine-Intersection Model (DE-9IM). This mathematical model checks for exact line crossings, polygon containment, or boundary-touching.

*Note:* In this implementation, the `intersects()` method is strictly configured so that even a boundary-touch (sharing a border) is flagged as a spatial conflict (`true`).

### 2) CRS Transformation for Metric Precision (pyproj)

Raw coordinates from IPFS (GeoJSON) are generated and stored in geographic degrees (WGS84 / EPSG:4326). However, validating area and spatial intersections using spherical degrees causes mathematical distortions that could lead to false positives/negatives in overlap detection.

To solve this, the API dynamically identifies the correct Universal Transverse Mercator (UTM) zone based on the new polygon's centroid longitude. It then temporarily reprojects both the new and historical polygons from EPSG:4326 into this flat metric Cartesian plane. EPSG mapping follows 326xx for the northern hemisphere and 327xx for the southern hemisphere. This guarantees that the DE-9IM overlap calculation is geometrically exact.

### 3) Concurrent I/O Strategy (aiohttp + asyncio)

CID downloads are executed concurrently with asyncio.gather.
A semaphore limits fan-out to protect gateway and runtime resources.
Batch timeout bounds total wait time for the whole CID set.
HTTP 429 triggers short retries with Retry-After support when available.

### 4) RPC Resilience Strategy (web3.py)

Blockchain read uses bounded retries with exponential backoff.
The synchronous web3 call is offloaded via asyncio.to_thread to avoid blocking the event loop.
The response is validated against a max approved CID threshold for API safety.

## Configuration

Environment variables are defined in .env.example.
Key values:

- ETH_RPC_URL: RPC endpoint for the target EVM network.
- PROJECT_MANAGER_ADDRESS: deployed ProjectManager contract address.
- PROJECT_MANAGER_ABI: JSON ABI string including getApprovedCellIds.
- PINATA_GATEWAY_BASE_URL and PINATA_JWT: authenticated IPFS gateway access.
- RPC and IPFS timeout values plus max concurrent downloads.

## Run Locally

1. Create and activate a Python virtual environment.
2. Install dependencies.
3. Copy .env.example to .env and set real values.
4. Start the API with uvicorn.

Example:

```bash
python -m pip install -e .[dev]
cp .env.example .env
uvicorn app.main:app --reload
```

## Run with Docker Compose

1. Copy `.env.example` to `.env` and set real values (at minimum `ETH_RPC_URL`, `PROJECT_MANAGER_ADDRESS`, `PROJECT_MANAGER_ABI`, `PINATA_JWT`).
2. Build and start the API.
3. Verify `/health`.

Example:

```bash
cp .env.example .env
docker compose up --build
```

Verify:

```bash
curl http://localhost:8000/health
```

Stop:

```bash
docker compose down
```

Notes:

- `docker-compose.yml` injects env vars via `env_file: .env` and also mounts the `.env` file into the container (`/app/.env`) to match `pydantic-settings` `env_file=".env"` behavior.
- The container listens on `0.0.0.0:8000` and is exposed to your host as `localhost:8000`.

## Limitations and Current Scope

- FeatureCollection inputs are normalized to the first feature.
- No external cache is used; every request performs fresh RPC and IPFS reads.
- intersects treats boundary-touch as a conflict.
- The service currently focuses on read/validation; on-chain write-back is out of scope.

## Testing

Run tests with:

```bash
python -m pytest -q
```

Run tests with coverage:

```bash
python -m pytest --cov=app --cov-report=term-missing
```

## API Endpoints

FastAPI exposes interactive API documentation at:
- `/docs` (Swagger UI)
- `/redoc` (ReDoc)

### POST /validate-polygon

Request body:

```json
{
	"cell_id": "bafy..."
}
```

Response body:

```json
{
	"overlap": true,
	"matched_cell_ids": ["bafyapproved1", "bafyapproved2"],
	"checked_count": 42,
	"trace_id": "2a8a0d75-a95f-4c31-8d3f-84d2f17dc932",
	"timings": {
		"blockchain_ms": 120.15,
		"ipfs_ms": 480.33,
		"spatial_ms": 31.04,
		"total_ms": 633.14
	},
	"inconclusive": false,
	"reason": null
}
```

### GET /health

Response body:

```json
{
	"status": "ok",
	"details": {
		"env": "dev",
		"rpc_timeout_seconds": 10,
		"ipfs_timeout_seconds": 20,
		"max_concurrent_downloads": 25
	}
}
```