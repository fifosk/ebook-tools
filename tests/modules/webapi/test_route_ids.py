import inspect

from modules.webapi.route_ids import normalize_route_id
from modules.webapi.routes.media import common, media_list, storage, timing


def test_normalize_route_id_trims_route_parameters() -> None:
    assert normalize_route_id("  job-1  ") == "job-1"
    assert normalize_route_id("   ") == ""


def test_playback_media_routes_use_shared_route_id_normalizer() -> None:
    for module in (common, media_list, storage, timing):
        source = inspect.getsource(module)
        assert "from ...route_ids import normalize_route_id" in source
        assert "def _normalize_route_id" not in source
