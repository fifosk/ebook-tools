from modules.webapi.route_ids import normalize_route_id


def test_normalize_route_id_trims_route_parameters() -> None:
    assert normalize_route_id("  job-1  ") == "job-1"
    assert normalize_route_id("   ") == ""
