from __future__ import annotations

import importlib.util
from pathlib import Path
from urllib.error import HTTPError


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_apple_create_readiness.py"
SPEC = importlib.util.spec_from_file_location("check_apple_create_readiness", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def test_counts_backend_visible_sources() -> None:
    assert module.count_epubs(
        {
            "ebooks": [
                {"type": "file", "path": "/books/current.epub"},
                {"type": "directory", "path": "/books"},
                {"type": "file", "path": ""},
            ]
        }
    ) == 1
    assert module.count_subtitle_sources(
        {
            "sources": [
                {"format": "srt", "path": "/subs/demo.srt"},
                {"format": "vtt", "path": "/subs/demo.vtt"},
                {"format": "pgs", "path": "/subs/demo.sup"},
            ]
        }
    ) == 2
    assert module.count_youtube_pairs(
        {
            "videos": [
                {
                    "path": "/nas/video.mp4",
                    "subtitles": [
                        {"format": "srt", "path": "/nas/video.en.srt"},
                        {"format": "pgs", "path": "/nas/video.sup"},
                    ],
                },
                {"path": "/nas/no-subtitles.mp4", "subtitles": []},
            ]
        }
    ) == (1, 1)


def test_language_inventory_requires_broad_book_options() -> None:
    broad_languages = [f"Language {index}" for index in range(60)]
    for sentinel in module.REQUIRED_BOOK_LANGUAGE_SENTINELS:
        broad_languages.append(sentinel)

    assert module.language_inventory(
        {
            "supported_input_languages": broad_languages,
            "supported_output_languages": broad_languages,
        }
    ) == {
        "book_input_languages": 65,
        "book_output_languages": 65,
        "missing_book_input_languages": [],
        "missing_book_output_languages": [],
    }

    limited_inventory = module.language_inventory(
        {
            "supported_input_languages": ["English", "Arabic", "Slovak", "Spanish", "French", "German"],
            "supported_output_languages": ["English", "Arabic", "Slovak", "Spanish", "French", "German"],
        }
    )

    assert limited_inventory["book_input_languages"] == 6
    assert limited_inventory["book_output_languages"] == 6
    assert limited_inventory["missing_book_input_languages"] == [
        "chinese (traditional)",
        "hindi",
        "persian",
    ]
    assert limited_inventory["missing_book_output_languages"] == [
        "chinese (traditional)",
        "hindi",
        "persian",
    ]


def test_validate_summary_reports_missing_create_sources() -> None:
    assert module.validate_summary(
        {
            "epubs": 1,
            "subtitle_sources": 1,
            "youtube_videos": 1,
            "youtube_subtitles": 1,
            "book_input_languages": 65,
            "book_output_languages": 65,
            "missing_book_input_languages": [],
            "missing_book_output_languages": [],
        }
    ) == []
    assert module.validate_summary(
        {
            "epubs": 0,
            "subtitle_sources": 0,
            "youtube_videos": 1,
            "youtube_subtitles": 0,
            "book_input_languages": 6,
            "book_output_languages": 6,
            "missing_book_input_languages": ["hindi"],
            "missing_book_output_languages": ["persian"],
        }
    ) == [
        "backend-visible EPUBs",
        "backend-visible subtitle sources",
        "YouTube/NAS videos with playable subtitles",
        "broad book input language options",
        "broad book output language options",
        "book input language sentinels: hindi",
        "book output language sentinels: persian",
    ]


def test_runtime_create_contract_validation() -> None:
    assert module.validate_runtime_create_contract(
        {"creation": dict(module.EXPECTED_CREATE_PATHS)}
    ) == []

    assert module.validate_runtime_create_contract({}) == [
        "runtime descriptor is missing creation metadata"
    ]

    assert module.validate_runtime_create_contract(
        {
            "creation": {
                "bookOptionsPath": "/old/books/options",
                "bookJobsPath": "",
            }
        }
    ) == [
        "bookOptionsPath=/old/books/options expected /api/books/options",
        "bookJobsPath=<missing> expected /api/books/jobs",
        "pipelineFilesPath=<missing> expected /api/pipelines/files",
        "pipelineContentIndexPath=<missing> expected /api/pipelines/files/content-index",
        "pipelineUploadPath=<missing> expected /api/pipelines/files/upload",
        "pipelineJobsPath=<missing> expected /api/pipelines",
        "pipelineIntakeStatusPath=<missing> expected /api/pipelines/intake/status",
        "subtitleSourcesPath=<missing> expected /api/subtitles/sources",
        "subtitleModelsPath=<missing> expected /api/subtitles/models",
        "subtitleJobsPath=<missing> expected /api/subtitles/jobs",
        "youtubeLibraryPath=<missing> expected /api/subtitles/youtube/library",
        "youtubeSubtitleStreamsPath=<missing> expected /api/subtitles/youtube/subtitle-streams",
        "youtubeExtractSubtitlesPath=<missing> expected /api/subtitles/youtube/extract-subtitles",
        "subtitleTvMetadataPreviewPath=<missing> expected /api/subtitles/metadata/tv/lookup",
        "youtubeMetadataPreviewPath=<missing> expected /api/subtitles/metadata/youtube/lookup",
        "youtubeDubPath=<missing> expected /api/subtitles/youtube/dub",
    ]


def test_fetch_readiness_checks_runtime_before_inventory(monkeypatch) -> None:
    paths: list[str] = []

    def fake_json_request(api_base_url: str, path: str, **kwargs):
        paths.append(path)
        return {"status": "ok"}

    monkeypatch.setattr(module, "json_request", fake_json_request)

    try:
        module.fetch_readiness("https://api.example.test", "token", 1.0)
    except RuntimeError as exc:
        assert str(exc) == (
            "Backend runtime Create contract is not ready: "
            "runtime descriptor is missing creation metadata"
        )
    else:
        raise AssertionError("fetch_readiness should fail on missing runtime Create contract")

    assert paths == ["/api/system/runtime"]


def test_env_file_parsing_does_not_require_dotenv(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "# comment",
                "E2E_USERNAME='alice'",
                'E2E_PASSWORD="secret"',
                "E2E_API_BASE_URL=https://example.test/",
            ]
        ),
        encoding="utf-8",
    )
    assert module.load_env_file(env_file) == {
        "E2E_USERNAME": "alice",
        "E2E_PASSWORD": "secret",
        "E2E_API_BASE_URL": "https://example.test/",
    }


def test_http_error_description_includes_endpoint_path() -> None:
    exc = HTTPError(
        "https://api.example.test/api/books/options",
        404,
        "Not Found",
        hdrs=None,
        fp=None,
    )

    assert module.describe_http_error(exc) == "API request to /api/books/options returned HTTP 404"
