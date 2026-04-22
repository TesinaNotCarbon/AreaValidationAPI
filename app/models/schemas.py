from typing import Any

from pydantic import BaseModel, Field, field_validator


class ValidatePolygonRequest(BaseModel):
    cell_id: str = Field(min_length=10, max_length=200, description="CID of the new project GeoJSON")

    @field_validator("cell_id")
    @classmethod
    def validate_cid(cls, value: str) -> str:
        if " " in value:
            raise ValueError("cell_id must not contain spaces")
        return value.strip()


class ValidationTimings(BaseModel):
    blockchain_ms: float
    ipfs_ms: float
    spatial_ms: float
    total_ms: float


class ValidatePolygonResponse(BaseModel):
    overlap: bool
    matched_cell_ids: list[str] = Field(default_factory=list)
    checked_count: int
    trace_id: str
    timings: ValidationTimings
    inconclusive: bool = False
    reason: str | None = None


class HealthResponse(BaseModel):
    status: str
    details: dict[str, Any]
