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


def test_youtube_sub_sidecars_count_as_playable_defaults() -> None:
    youtube = {
        "videos": [
            {
                "path": "/nas/movie.mp4",
                "modified_at": "2026-06-24T00:00:00Z",
                "subtitles": [
                    {"format": "sub", "path": "/nas/movie.en.sub", "language": "en"},
                    {"format": "pgs", "path": "/nas/movie.sup", "language": "en"},
                ],
            }
        ]
    }

    assert module.count_youtube_pairs(youtube) == (1, 1)
    selected_video, selected_subtitle = module.preferred_youtube_selection(youtube)
    assert selected_video["path"] == "/nas/movie.mp4"
    assert selected_subtitle["path"] == "/nas/movie.en.sub"


def test_resolves_default_create_sources_without_paths_in_summary() -> None:
    files = {
        "ebooks": [
            {"type": "file", "path": "/books/z-old.epub", "modified_at": "2026-01-01T00:00:00Z"},
            {"type": "file", "path": "/books/a-new.epub", "modified_at": "2026-06-24T00:00:00Z"},
            {"type": "directory", "path": "/books/folder"},
        ]
    }
    subtitles = {
        "sources": [
            {"format": "ass", "path": "/subs/newer.ass", "modified_at": "2026-06-24T00:00:00Z"},
            {"format": "srt", "path": "/subs/older.srt", "modified_at": "2026-01-01T00:00:00Z"},
            {"format": "pgs", "path": "/subs/newer.sup", "modified_at": "2026-06-25T00:00:00Z"},
        ]
    }
    youtube = {
        "videos": [
            {"path": "/nas/no-playable.mp4", "subtitles": []},
            {
                "path": "/nas/has-playable.mp4",
                "subtitles": [
                    {"format": "vtt", "path": "/nas/has-playable.fr.vtt", "language": "fr"},
                    {"format": "srt", "path": "/nas/has-playable.en.srt", "language": "en-US"},
                ],
            },
        ]
    }

    assert module.preferred_epub(files)["path"] == "/books/a-new.epub"
    assert module.preferred_subtitle_source(subtitles)["path"] == "/subs/older.srt"
    selected_video, selected_subtitle = module.preferred_youtube_selection(youtube)
    assert selected_video["path"] == "/nas/has-playable.mp4"
    assert selected_subtitle["path"] == "/nas/has-playable.en.srt"


def test_default_subtitle_source_uses_ass_only_as_fallback() -> None:
    assert module.preferred_subtitle_source(
        {
            "sources": [
                {"format": "ass", "path": "/subs/only.ass", "modified_at": "2026-06-24T00:00:00Z"},
                {"format": "pgs", "path": "/subs/ignored.sup", "modified_at": "2026-06-25T00:00:00Z"},
            ]
        }
    )["path"] == "/subs/only.ass"


def test_default_youtube_selection_uses_newest_playable_video() -> None:
    selected_video, selected_subtitle = module.preferred_youtube_selection(
        {
            "videos": [
                {
                    "path": "/nas/older-playable.mp4",
                    "modified_at": "2026-01-01T00:00:00Z",
                    "subtitles": [
                        {"format": "srt", "path": "/nas/older-playable.en.srt", "language": "en"},
                    ],
                },
                {
                    "path": "/nas/newest-no-subtitles.mp4",
                    "modified_at": "2026-06-25T00:00:00Z",
                    "subtitles": [],
                },
                {
                    "path": "/nas/newer-playable.mp4",
                    "modified_at": "2026-06-24T00:00:00Z",
                    "subtitles": [
                        {"format": "vtt", "path": "/nas/newer-playable.fr.vtt", "language": "fr"},
                    ],
                },
            ]
        }
    )

    assert selected_video["path"] == "/nas/newer-playable.mp4"
    assert selected_subtitle["path"] == "/nas/newer-playable.fr.vtt"


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


def test_media_job_defaults_inventory_requires_cross_surface_defaults() -> None:
    assert module.media_job_defaults_inventory(
        {
            "sentence_bounds": {"min": 1, "max": 500, "default": 30},
            "defaults": {
                "author": "Me",
                "input_language": "English",
                "output_language": "Arabic",
                "voice": "DemoVoice",
            },
            "pipeline_defaults": {
                "audio_mode": "4",
                "written_mode": "4",
                "selected_voice": "DemoVoice",
                "stitch_full": False,
            },
            "subtitle_defaults": {
                "worker_count": 12,
                "batch_size": 22,
                "translation_batch_size": 8,
                "ass_font_size": 64,
                "ass_emphasis_scale": 1.6,
            },
            "youtube_dub_defaults": {
                "original_mix_percent": 20,
                "flush_sentences": 18,
                "translation_batch_size": 6,
                "split_batches": True,
                "stitch_batches": False,
                "target_height": 720,
                "preserve_aspect_ratio": True,
            },
        }
    ) == {
        "generated_book_defaults_ready": True,
        "subtitle_job_defaults_ready": True,
        "youtube_dub_defaults_ready": True,
        "generated_book_defaults_errors": [],
        "subtitle_job_defaults_errors": [],
        "youtube_dub_defaults_errors": [],
    }

    assert module.media_job_defaults_inventory(
        {
            "sentence_bounds": {"min": 10, "max": 5, "default": 30},
            "defaults": {
                "author": "",
                "input_language": "English",
                "output_language": "",
                "voice": "",
            },
            "pipeline_defaults": {
                "audio_mode": "",
                "written_mode": "4",
                "selected_voice": "",
                "stitch_full": "no",
            },
            "subtitle_defaults": {
                "worker_count": 0,
                "batch_size": "many",
                "translation_batch_size": 51,
                "ass_font_size": 8,
                "ass_emphasis_scale": 3.1,
            },
            "youtube_dub_defaults": {
                "original_mix_percent": -1,
                "flush_sentences": 0,
                "translation_batch_size": 0,
                "split_batches": "yes",
                "stitch_batches": True,
                "target_height": 1080,
                "preserve_aspect_ratio": None,
            },
        }
    ) == {
        "generated_book_defaults_ready": False,
        "subtitle_job_defaults_ready": False,
        "youtube_dub_defaults_ready": False,
        "generated_book_defaults_errors": [
            "sentence_bounds.default_range",
            "defaults.author",
            "defaults.output_language",
            "defaults.voice",
            "pipeline_defaults.audio_mode",
            "pipeline_defaults.selected_voice",
            "pipeline_defaults.stitch_full",
        ],
        "subtitle_job_defaults_errors": [
            "worker_count",
            "batch_size",
            "translation_batch_size",
            "ass_font_size",
            "ass_emphasis_scale",
        ],
        "youtube_dub_defaults_errors": [
            "original_mix_percent",
            "flush_sentences",
            "translation_batch_size",
            "split_batches",
            "preserve_aspect_ratio",
            "target_height",
        ],
    }


def test_validate_summary_reports_missing_create_sources() -> None:
    assert module.validate_summary(
        {
            "epubs": 1,
            "subtitle_sources": 1,
            "youtube_videos": 1,
            "youtube_subtitles": 1,
            "default_epub_ready": True,
            "default_subtitle_source_ready": True,
            "default_youtube_video_ready": True,
            "default_youtube_subtitle_ready": True,
            "book_input_languages": 65,
            "book_output_languages": 65,
            "missing_book_input_languages": [],
            "missing_book_output_languages": [],
            "generated_book_defaults_ready": True,
            "subtitle_job_defaults_ready": True,
            "youtube_dub_defaults_ready": True,
            "generated_book_defaults_errors": [],
            "subtitle_job_defaults_errors": [],
            "youtube_dub_defaults_errors": [],
        }
    ) == []
    assert module.validate_summary(
        {
            "epubs": 0,
            "subtitle_sources": 0,
            "youtube_videos": 1,
            "youtube_subtitles": 0,
            "default_epub_ready": False,
            "default_subtitle_source_ready": False,
            "default_youtube_video_ready": True,
            "default_youtube_subtitle_ready": False,
            "book_input_languages": 6,
            "book_output_languages": 6,
            "missing_book_input_languages": ["hindi"],
            "missing_book_output_languages": ["persian"],
            "generated_book_defaults_ready": False,
            "subtitle_job_defaults_ready": False,
            "youtube_dub_defaults_ready": False,
            "generated_book_defaults_errors": ["defaults.voice"],
            "subtitle_job_defaults_errors": ["batch_size"],
            "youtube_dub_defaults_errors": ["target_height"],
        }
    ) == [
        "backend-visible EPUBs",
        "backend-visible subtitle sources",
        "YouTube/NAS videos with playable subtitles",
        "default Narrate EPUB source",
        "default subtitle source",
        "default YouTube/NAS video+subtitle selection",
        "broad book input language options",
        "broad book output language options",
        "book input language sentinels: hindi",
        "book output language sentinels: persian",
        "generated book defaults: defaults.voice",
        "subtitle job processing defaults: batch_size",
        "YouTube dubbing processing defaults: target_height",
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
        "subtitleDeleteSourcePath=<missing> expected /api/subtitles/delete-source",
        "subtitleModelsPath=<missing> expected /api/subtitles/models",
        "subtitleJobsPath=<missing> expected /api/subtitles/jobs",
        "youtubeLibraryPath=<missing> expected /api/subtitles/youtube/library",
        "youtubeSubtitleStreamsPath=<missing> expected /api/subtitles/youtube/subtitle-streams",
        "youtubeExtractSubtitlesPath=<missing> expected /api/subtitles/youtube/extract-subtitles",
        "subtitleTvMetadataPreviewPath=<missing> expected /api/subtitles/metadata/tv/lookup",
        "subtitleTvMetadataCacheClearPath=<missing> expected /api/subtitles/metadata/tv/cache/clear",
        "youtubeMetadataPreviewPath=<missing> expected /api/subtitles/metadata/youtube/lookup",
        "youtubeMetadataCacheClearPath=<missing> expected /api/subtitles/metadata/youtube/cache/clear",
        "youtubeDubPath=<missing> expected /api/subtitles/youtube/dub",
        "templateListPath=<missing> expected /api/creation/templates",
        "templatePathTemplate=<missing> expected /api/creation/templates/{template_id}",
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


def test_fetch_readiness_includes_creation_option_default_contract(monkeypatch) -> None:
    paths: list[str] = []

    def fake_json_request(api_base_url: str, path: str, **kwargs):
        paths.append(path)
        if path == "/api/system/runtime":
            return {"creation": dict(module.EXPECTED_CREATE_PATHS)}
        if path == "/api/pipelines/files":
            return {"ebooks": [{"type": "file", "path": "/books/current.epub"}]}
        if path == "/api/subtitles/sources":
            return {"sources": [{"format": "srt", "path": "/subs/current.srt"}]}
        if path == "/api/subtitles/youtube/library":
            return {
                "videos": [
                    {
                        "path": "/nas/video.mp4",
                        "subtitles": [{"format": "srt", "path": "/nas/video.en.srt"}],
                    }
                ]
            }
        if path == module.EXPECTED_BOOK_OPTIONS_PATH:
            broad_languages = [f"Language {index}" for index in range(60)]
            broad_languages.extend(module.REQUIRED_BOOK_LANGUAGE_SENTINELS)
            return {
                "sentence_bounds": {"min": 1, "max": 500, "default": 30},
                "defaults": {
                    "author": "Me",
                    "input_language": "English",
                    "output_language": "Arabic",
                    "voice": "DemoVoice",
                },
                "pipeline_defaults": {
                    "audio_mode": "4",
                    "written_mode": "4",
                    "selected_voice": "DemoVoice",
                    "stitch_full": False,
                },
                "supported_input_languages": broad_languages,
                "supported_output_languages": broad_languages,
                "subtitle_defaults": {
                    "worker_count": 10,
                    "batch_size": 20,
                    "translation_batch_size": 10,
                    "ass_font_size": 56,
                    "ass_emphasis_scale": 1.3,
                },
                "youtube_dub_defaults": {
                    "original_mix_percent": 5,
                    "flush_sentences": 10,
                    "translation_batch_size": 10,
                    "split_batches": True,
                    "stitch_batches": True,
                    "target_height": 480,
                    "preserve_aspect_ratio": True,
                },
            }
        raise AssertionError(f"unexpected path {path}")

    monkeypatch.setattr(module, "json_request", fake_json_request)

    summary = module.fetch_readiness("https://api.example.test", "token", 1.0)

    assert paths == [
        "/api/system/runtime",
        "/api/pipelines/files",
        "/api/subtitles/sources",
        "/api/subtitles/youtube/library",
        "/api/books/options",
    ]
    assert summary["generated_book_defaults_ready"] is True
    assert summary["subtitle_job_defaults_ready"] is True
    assert summary["youtube_dub_defaults_ready"] is True


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
