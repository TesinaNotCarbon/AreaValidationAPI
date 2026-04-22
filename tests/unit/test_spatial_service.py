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
