from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
TESTING_DOC = ROOT / "docs" / "testing.md"


def _target_block(makefile: str, target: str) -> str:
    return makefile.split(f"{target}:", 1)[1].split("\n\n", 1)[0]


def test_library_search_source_isbn_backend_target_covers_pipeline_slice() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-backend-library-search-source-isbn" in makefile
    block = _target_block(makefile, "test-backend-library-search-source-isbn")
    assert "$(PYTHON) -m pytest" in block
    assert "tests/modules/webapi/test_library_items_route.py" in block
    assert "tests/modules/webapi/test_search_routes.py" in block
    assert "tests/test_library_source_and_isbn_metadata.py" in block


def test_backend_pipeline_targets_cover_single_slice_checks() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    expected = {
        "test-backend-auth-session": ("tests/modules/webapi/test_auth_routes.py",),
        "test-backend-admin-system-status": ("tests/modules/webapi/test_system_routes.py",),
        "test-backend-create-book": ("tests/test_create_book.py",),
        "test-backend-creation-templates": (
            "tests/modules/webapi/test_creation_template_routes.py",
        ),
        "test-backend-pipeline-sources": (
            "tests/test_create_book.py::test_pipeline_file_picker_records_safe_timing",
            "tests/test_create_book.py::test_delete_pipeline_ebook_is_idempotent_for_missing_in_scope_file",
            "tests/test_create_book.py::test_delete_pipeline_ebook_rejects_missing_file_outside_books_root",
            "tests/test_create_book.py::test_upload_pipeline_ebook_persists_file_in_books_root",
        ),
        "test-backend-audio-routes": ("tests/modules/webapi/test_audio_routes.py",),
        "test-backend-reading-beds": (
            "tests/modules/webapi/test_reading_bed_routes.py",
        ),
        "test-backend-notifications": (
            "tests/modules/webapi/test_notification_routes.py",
        ),
        "test-backend-subtitle-router": ("tests/webapi/test_subtitles_router.py",),
        "test-backend-playback-state": (
            "tests/modules/webapi/test_resume_routes.py",
            "tests/modules/webapi/test_bookmark_routes.py",
            "tests/modules/test_resume_service.py",
        ),
        "test-backend-playback-media": (
            "tests/modules/webapi/test_job_media_routes.py",
            "tests/modules/webapi/test_library_media_route.py",
            "tests/modules/webapi/test_library_media_file_download.py",
        ),
        "test-backend-offline-export": (
            "tests/modules/webapi/test_export_routes.py",
        ),
        "test-backend-youtube-dubbing-service": (
            "tests/modules/webapi/test_youtube_library_route.py",
            "tests/modules/services/test_youtube_dubbing_subtitles.py",
            "tests/modules/services/test_youtube_subtitles.py",
        ),
    }

    for target, paths in expected.items():
        assert target in makefile
        block = _target_block(makefile, target)
        assert "$(PYTHON) -m pytest" in block
        for path in paths:
            assert path in block


def test_docs_publish_backend_pipeline_targets() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")

    for command in [
        "make test-backend-auth-session",
        "make test-backend-library-search-source-isbn",
        "make test-backend-admin-system-status",
        "make test-backend-create-book",
        "make test-backend-creation-templates",
        "make test-backend-pipeline-sources",
        "make test-backend-audio-routes",
        "make test-backend-reading-beds",
        "make test-backend-notifications",
        "make test-backend-subtitle-router",
        "make test-backend-playback-state",
        "make test-backend-playback-media",
        "make test-backend-offline-export",
        "make test-backend-youtube-dubbing-service",
    ]:
        assert command in docs
