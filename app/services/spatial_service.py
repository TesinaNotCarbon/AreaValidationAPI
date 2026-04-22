from __future__ import annotations

from dataclasses import dataclass

from pyproj import CRS, Transformer
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import transform

from app.core.exceptions import GeometryValidationError


@dataclass
class SpatialValidationResult:
    overlap: bool
    matched_cell_ids: list[str]
    checked_count: int


class SpatialService:
    """Validate polygon overlap after projecting all geometries to one metric CRS."""

    def validate_overlap(
        self,
        new_cell_id: str,
        geojson_map: dict[str, dict],
        approved_cell_ids: list[str],
    ) -> SpatialValidationResult:
        """Parse, reproject, and compare the new polygon against approved polygons."""
        if new_cell_id not in geojson_map:
            raise GeometryValidationError("New cell GeoJSON not available for spatial validation")

        # WGS84 (EPSG:4326) is a global geographic CRS in longitude/latitude degrees.
        new_geom_wgs84 = self._parse_geojson_polygon(geojson_map[new_cell_id], label=new_cell_id)
        target_epsg = self._epsg_for_geom(new_geom_wgs84)

        # CRS means Coordinate Reference System: it defines how coordinates map to Earth.
        transformer = Transformer.from_crs(
            CRS.from_epsg(4326),
            CRS.from_epsg(target_epsg),
            always_xy=True,
        )
        project = transformer.transform

        # UTM is a projected CRS in meters, better suited for local geometric predicates.
        new_geom_utm = transform(project, new_geom_wgs84)
        if not new_geom_utm.is_valid:
            raise GeometryValidationError("Reprojected new geometry is invalid")

        matched: list[str] = []
        checked = 0
        for historical_cell_id in approved_cell_ids:
            if historical_cell_id == new_cell_id:
                continue

            historical_geojson = geojson_map.get(historical_cell_id)
            if historical_geojson is None:
                continue

            historical_geom = self._parse_geojson_polygon(historical_geojson, label=historical_cell_id)
            historical_geom_utm = transform(project, historical_geom)
            checked += 1

            # Shapely delegates topology predicates to GEOS; intersects follows DE-9IM semantics.
            # It returns true for overlap, containment, and boundary-touch cases.
            if new_geom_utm.intersects(historical_geom_utm):
                matched.append(historical_cell_id)

        return SpatialValidationResult(
            overlap=bool(matched),
            matched_cell_ids=matched,
            checked_count=checked,
        )

    def _parse_geojson_polygon(self, geojson_doc: dict, label: str) -> Polygon | MultiPolygon:
        """Normalize GeoJSON into Polygon/MultiPolygon and enforce geometry validity."""
        geometry = geojson_doc
        # FeatureCollection is normalized to its first feature for this MVP flow.
        if geojson_doc.get("type") == "Feature":
            geometry = geojson_doc.get("geometry", {})
        elif geojson_doc.get("type") == "FeatureCollection":
            features = geojson_doc.get("features", [])
            if not features:
                raise GeometryValidationError(f"CID {label} is an empty FeatureCollection")
            geometry = features[0].get("geometry", {})

        try:
            geom = shape(geometry)
        except Exception as exc:
            raise GeometryValidationError(f"CID {label} has invalid GeoJSON geometry") from exc

        if not isinstance(geom, (Polygon, MultiPolygon)):
            raise GeometryValidationError(f"CID {label} must be Polygon or MultiPolygon")

        if geom.is_empty or not geom.is_valid:
            raise GeometryValidationError(f"CID {label} geometry is empty or invalid")

        return geom

    def _epsg_for_geom(self, geom_wgs84: Polygon | MultiPolygon) -> int:
        """Select a UTM EPSG code from centroid longitude/latitude."""
        centroid = geom_wgs84.centroid
        lon = centroid.x
        lat = centroid.y

        # UTM zone formula over longitude range [-180, 180].
        zone = int((lon + 180) / 6) + 1
        zone = min(60, max(1, zone))

        # EPSG 326xx for north hemisphere, 327xx for south hemisphere.
        if lat >= 0:
            return 32600 + zone
        return 32700 + zone
