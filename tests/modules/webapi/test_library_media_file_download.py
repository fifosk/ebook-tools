from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from modules.webapi.application import create_app
from modules.webapi.dependencies import get_library_sync


class _StubLibrarySync:
    def __init__(self, resolved_path: Path) -> None:
        self._resolved_path = resolved_path

    def resolve_media_file(self, job_id: str, relative_path: str) -> Path:
        assert job_id == "library-job"
        assert relative_path == "dubbed.mp4"
        return self._resolved_path


def test_library_media_file_supports_range_with_inline_disposition(tmp_path: Path) -> None:
    media_path = tmp_path / "dubbed.mp4"
    media_path.write_bytes(b"0123456789")

    app = create_app()
    app.dependency_overrides[get_library_sync] = lambda: _StubLibrarySync(media_path)

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/library/media/library-job/file/dubbed.mp4",
                headers={"Range": "bytes=1-4"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 206
    assert response.content == b"1234"
    assert response.headers["Accept-Ranges"] == "bytes"
    assert response.headers["Content-Range"] == "bytes 1-4/10"
    assert response.headers["Content-Type"].startswith("video/mp4")
    assert response.headers["Content-Disposition"].startswith("inline;")

