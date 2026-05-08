import pytest
from shapely.geometry import Polygon

from app.core.exceptions import GeometryValidationError
from app.services import spatial_service
from app.services.spatial_service import SpatialService


def test_validate_overlap_detects_intersection():
    service = SpatialService()

    new_cid = "new-cell"
    approved = ["old-cell"]

    geojson_map = {
        new_cid: {
            "type": "Polygon",
            "coordinates": [[
                [-74.0000, 40.0000],
                [-73.9990, 40.0000],
                [-73.9990, 40.0010],
                [-74.0000, 40.0010],
                [-74.0000, 40.0000],
            ]],
        },
        "old-cell": {
            "type": "Polygon",
            "coordinates": [[
                [-73.9995, 40.0005],
                [-73.9985, 40.0005],
                [-73.9985, 40.0015],
                [-73.9995, 40.0015],
                [-73.9995, 40.0005],
            ]],
        },
    }

    result = service.validate_overlap(
        new_cell_id=new_cid,
        geojson_map=geojson_map,
        approved_cell_ids=approved,
    )

    assert result.overlap is True
    assert result.matched_cell_ids == ["old-cell"]
    assert result.checked_count == 1


def test_validate_overlap_detects_no_intersection():
    service = SpatialService()

    new_cid = "new-cell"
    approved = ["old-cell"]

    geojson_map = {
        new_cid: {
            "type": "Polygon",
            "coordinates": [[
                [-74.0000, 40.0000],
                [-73.9990, 40.0000],
                [-73.9990, 40.0010],
                [-74.0000, 40.0010],
                [-74.0000, 40.0000],
            ]],
        },
        "old-cell": {
            "type": "Polygon",
            "coordinates": [[
                [-73.9000, 40.1000],
                [-73.8990, 40.1000],
                [-73.8990, 40.1010],
                [-73.9000, 40.1010],
                [-73.9000, 40.1000],
            ]],
        },
    }

    result = service.validate_overlap(
        new_cell_id=new_cid,
        geojson_map=geojson_map,
        approved_cell_ids=approved,
    )

    assert result.overlap is False
    assert result.matched_cell_ids == []
    assert result.checked_count == 1


def test_validate_overlap_missing_new_cell_id_raises():
    service = SpatialService()

    with pytest.raises(GeometryValidationError, match="New cell GeoJSON not available"):
        service.validate_overlap(
            new_cell_id="missing",
            geojson_map={},
            approved_cell_ids=[],
        )


def test_validate_overlap_reprojected_geom_invalid_raises(monkeypatch: pytest.MonkeyPatch):
    service = SpatialService()

    geojson_map = {
        "new-cell": {
            "type": "Polygon",
            "coordinates": [[
                [-74.0000, 40.0000],
                [-73.9990, 40.0000],
                [-73.9990, 40.0010],
                [-74.0000, 40.0010],
                [-74.0000, 40.0000],
            ]],
        }
    }

    class InvalidGeom:
        is_valid = False

    def fake_transform(project, geom):
        return InvalidGeom()

    monkeypatch.setattr(spatial_service, "transform", fake_transform)

    with pytest.raises(GeometryValidationError, match="Reprojected new geometry is invalid"):
        service.validate_overlap(
            new_cell_id="new-cell",
            geojson_map=geojson_map,
            approved_cell_ids=[],
        )


def test_validate_overlap_skips_self_and_missing_history():
    service = SpatialService()

    geojson_map = {
        "new-cell": {
            "type": "Polygon",
            "coordinates": [[
                [-74.0000, 40.0000],
                [-73.9990, 40.0000],
                [-73.9990, 40.0010],
                [-74.0000, 40.0010],
                [-74.0000, 40.0000],
            ]],
        }
    }

    result = service.validate_overlap(
        new_cell_id="new-cell",
        geojson_map=geojson_map,
        approved_cell_ids=["new-cell", "missing-cell"],
    )

    assert result.overlap is False
    assert result.matched_cell_ids == []
    assert result.checked_count == 0


def test_parse_geojson_feature_polygon():
    service = SpatialService()

    geojson = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-74.0000, 40.0000],
                [-73.9990, 40.0000],
                [-73.9990, 40.0010],
                [-74.0000, 40.0010],
                [-74.0000, 40.0000],
            ]],
        },
    }

    geom = service._parse_geojson_polygon(geojson, label="cid-1")

    assert geom.geom_type == "Polygon"


def test_parse_geojson_feature_collection_first_feature():
    service = SpatialService()

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-74.0000, 40.0000],
                        [-73.9990, 40.0000],
                        [-73.9990, 40.0010],
                        [-74.0000, 40.0010],
                        [-74.0000, 40.0000],
                    ]],
                },
            }
        ],
    }

    geom = service._parse_geojson_polygon(geojson, label="cid-2")

    assert geom.geom_type == "Polygon"


def test_parse_geojson_feature_collection_empty_raises():
    service = SpatialService()

    geojson = {
        "type": "FeatureCollection",
        "features": [],
    }

    with pytest.raises(GeometryValidationError, match="empty FeatureCollection"):
        service._parse_geojson_polygon(geojson, label="cid-3")


def test_parse_geojson_shape_exception_raises():
    service = SpatialService()

    geojson = {
        "type": "Polygon",
        "coordinates": "no-list",
    }

    with pytest.raises(GeometryValidationError, match="invalid GeoJSON geometry"):
        service._parse_geojson_polygon(geojson, label="cid-4")


def test_parse_geojson_rejects_non_polygon():
    service = SpatialService()

    geojson = {
        "type": "Point",
        "coordinates": [0, 0],
    }

    with pytest.raises(GeometryValidationError, match="must be Polygon or MultiPolygon"):
        service._parse_geojson_polygon(geojson, label="cid-5")


def test_parse_geojson_rejects_empty_geometry():
    service = SpatialService()

    geojson = {
        "type": "Polygon",
        "coordinates": [],
    }

    with pytest.raises(GeometryValidationError, match="empty or invalid"):
        service._parse_geojson_polygon(geojson, label="cid-6")


def test_epsg_for_geom_southern_hemisphere():
    service = SpatialService()

    geom = Polygon(
        [
            (-60.0, -10.0),
            (-59.0, -10.0),
            (-59.0, -9.0),
            (-60.0, -9.0),
            (-60.0, -10.0),
        ]
    )

    epsg = service._epsg_for_geom(geom)

    assert epsg == 32721
