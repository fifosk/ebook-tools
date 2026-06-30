from __future__ import annotations

import importlib.util
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_apple_create_readiness.py"
SPEC = importlib.util.spec_from_file_location("check_apple_create_readiness", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def parse_query_value(path: str, name: str) -> str:
    values = parse_qs(urlsplit(path).query).get(name)
    assert values
    return values[0]


def add_source_label(provider: dict[str, object], provider_id: str) -> dict[str, object]:
    labels = {
        "local_epub": "Books root",
        "manual_downloads": "Manual download folders",
        "nas_video": "NAS video root",
    }
    if provider_id in labels:
        provider["source_label"] = labels[provider_id]
    return provider


def build_runtime_payload() -> dict[str, object]:
    return {
        "auth": dict(module.EXPECTED_RUNTIME_SECTIONS["auth"]),
        "creation": dict(module.EXPECTED_CREATE_PATHS),
        "libraryActions": dict(module.EXPECTED_RUNTIME_SECTIONS["libraryActions"]),
        "pipelineJobs": dict(module.EXPECTED_RUNTIME_SECTIONS["pipelineJobs"]),
        "pipelineMedia": dict(module.EXPECTED_RUNTIME_SECTIONS["pipelineMedia"]),
        "linguist": dict(module.EXPECTED_RUNTIME_SECTIONS["linguist"]),
        "offlineExports": dict(module.EXPECTED_RUNTIME_SECTIONS["offlineExports"]),
        "playbackState": dict(module.EXPECTED_RUNTIME_SECTIONS["playbackState"]),
        "notifications": dict(module.EXPECTED_RUNTIME_SECTIONS["notifications"]),
    }


def build_sentence_splitter_capabilities() -> dict[str, object]:
    return {
        "default_mode": "regex",
        "supported_modes": [
            {
                "id": "regex",
                "label": "Regex (stable)",
                "cache_version": "regex-v9",
                "stable": True,
            },
            {
                "id": "modern",
                "label": "Modern (opt-in)",
                "cache_version": "modern-syntok-v2+regex-v9-fallback",
                "stable": False,
            },
        ],
        "comparison_metric_fields": [
            "normalized_text_preserved",
            "contiguous_text_preserved",
            "matched_sentence_count",
            "unmatched_sentence_count",
            "unmatched_sentence_indices",
            "skipped_text_character_count",
            "trailing_text_character_count",
            "tiny_fragment_count",
            "max_words_per_segment",
        ],
    }


def test_counts_backend_visible_sources() -> None:
    assert module.count_epubs(
        {
            "ebooks": [
                {"type": "file", "path": "/books/current.epub"},
                {"path": "/books/backend-scoped-book"},
                {"type": "directory", "path": "/books"},
                {"type": "file", "path": ""},
            ]
        }
    ) == 2
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


def test_acquisition_job_status_inventory_uses_non_mutating_poll_sentinel(monkeypatch) -> None:
    paths: list[str] = []

    def fake_json_request(api_base_url: str, path: str, **kwargs):
        paths.append(path)
        assert "token" in kwargs
        return {
            "provider": "download_station",
            "task_id": "download_station:submitted",
            "status": "submitted",
            "progress": None,
            "message": "Use manual downloads discovery after completion.",
            "external_task_id": None,
            "raw_status": None,
            "started_at": None,
            "updated_at": "2026-06-27T00:00:00Z",
            "completed_files": [],
            "next_actions": ["discover_manual_downloads", "import_local"],
            "metadata": {"source_kind": "download_station"},
        }

    monkeypatch.setattr(module, "json_request", fake_json_request)

    inventory = module.acquisition_job_status_inventory(
        "https://api.example.test",
        "token",
        1.0,
    )

    assert paths == [
        "/api/acquisition/jobs/download_station%3Asubmitted?provider=download_station"
    ]
    assert inventory == {
        "acquisition_job_status_route_ready": True,
        "acquisition_job_status_issues": [],
    }


def test_acquisition_job_status_inventory_reports_payload_shape_issues(monkeypatch) -> None:
    def fake_json_request(api_base_url: str, path: str, **kwargs):
        return {
            "provider": "other",
            "task_id": "",
            "status": "",
            "progress": "half",
            "updated_at": None,
            "completed_files": ["ready.mp4", 42],
            "next_actions": "poll",
            "metadata": [],
        }

    monkeypatch.setattr(module, "json_request", fake_json_request)

    inventory = module.acquisition_job_status_inventory(
        "https://api.example.test",
        "token",
        1.0,
    )

    assert inventory["acquisition_job_status_route_ready"] is False
    assert inventory["acquisition_job_status_issues"] == [
        "completed_files.items",
        "metadata",
        "next_actions",
        "progress",
        "provider:download_station",
        "status.empty",
        "task_id.empty",
        "updated_at",
    ]


def test_resolves_default_create_sources_without_paths_in_summary() -> None:
    files = {
        "ebooks": [
            {"type": "file", "path": "/books/z-old.epub", "modified_at": "2026-01-01T00:00:00Z"},
            {"type": "file", "path": "/books/a-new.epub", "modified_at": "2026-06-24T00:00:00Z"},
            {"path": "/books/backend-scoped-book", "modified_at": "2026-06-25T00:00:00Z"},
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

    assert module.preferred_epub(files)["path"] == "/books/backend-scoped-book"
    assert module.preferred_subtitle_source(subtitles)["path"] == "/subs/older.srt"
    selected_video, selected_subtitle = module.preferred_youtube_selection(youtube)
    assert selected_video["path"] == "/nas/has-playable.mp4"
    assert selected_subtitle["path"] == "/nas/has-playable.en.srt"


def test_content_index_chapter_count_requires_chapter_list() -> None:
    assert module.content_index_chapter_count(
        {"content_index": {"chapters": [{"title": "One"}, {"title": "Two"}]}}
    ) == 2
    assert module.content_index_chapter_count({"content_index": {"chapters": []}}) == 0
    assert module.content_index_chapter_count({"content_index": None}) == 0


def test_content_index_range_coverage_requires_contiguous_unique_ordered_ranges() -> None:
    assert (
        module.content_index_range_coverage_ready(
            {
                "content_index": {
                    "alignment": {
                        "chapter_range_coverage": {
                            "contiguous_unique_ranges": True,
                        },
                    },
                },
            }
        )
        is True
    )
    assert (
        module.content_index_range_coverage_ready(
            {
                "content_index": {
                    "alignment": {
                        "chapter_range_coverage": {
                            "contiguous_unique_ranges": True,
                            "ordered_adjacent_ranges": True,
                        },
                    },
                },
            }
        )
        is True
    )
    assert (
        module.content_index_range_coverage_ready(
            {
                "content_index": {
                    "alignment": {
                        "chapter_range_coverage": {
                            "contiguous_unique_ranges": False,
                        },
                    },
                },
            }
        )
        is False
    )
    assert (
        module.content_index_range_coverage_ready(
            {
                "content_index": {
                    "alignment": {
                        "chapter_range_coverage": {
                            "contiguous_unique_ranges": True,
                            "ordered_adjacent_ranges": False,
                        },
                    },
                },
            }
        )
        is False
    )
    assert module.content_index_range_coverage_ready({"content_index": {"chapters": []}}) is False


def test_preferred_epub_chapter_inventory_queries_content_index(monkeypatch) -> None:
    paths: list[str] = []

    def fake_json_request(api_base_url: str, path: str, **kwargs):
        paths.append(path)
        assert "token" in kwargs
        return {
            "content_index": {
                "chapters": [{"title": "Chapter 1"}],
                "alignment": {
                    "chapter_range_coverage": {
                        "contiguous_unique_ranges": True,
                    },
                },
            }
        }

    monkeypatch.setattr(module, "json_request", fake_json_request)

    inventory = module.preferred_epub_chapter_inventory(
        "https://api.example.test",
        "token",
        {
            "ebooks": [
                {
                    "type": "file",
                    "path": "Dan Brown/latest continuation.epub",
                    "modified_at": "2026-06-25T00:00:00Z",
                }
            ]
        },
        1.0,
    )

    assert inventory == {
        "default_epub_chapter_index_ready": True,
        "default_epub_chapters": 1,
        "default_epub_chapter_ranges_ready": True,
    }
    assert paths == [
        "/api/pipelines/files/content-index?input_file=Dan+Brown%2Flatest+continuation.epub"
    ]


def test_preferred_epub_chapter_inventory_reports_not_ready_on_http_error(monkeypatch) -> None:
    def fake_json_request(api_base_url: str, path: str, **kwargs):
        raise HTTPError(
            f"{api_base_url}{path}",
            422,
            "Unprocessable Content",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(module, "json_request", fake_json_request)

    assert module.preferred_epub_chapter_inventory(
        "https://api.example.test",
        "token",
        {"ebooks": [{"type": "file", "path": "/books/broken.epub"}]},
        1.0,
    ) == {
        "default_epub_chapter_index_ready": False,
        "default_epub_chapters": 0,
        "default_epub_chapter_ranges_ready": False,
    }


def test_preferred_epub_chapter_inventory_requires_range_coverage(monkeypatch) -> None:
    def fake_json_request(api_base_url: str, path: str, **kwargs):
        return {"content_index": {"chapters": [{"title": "Chapter 1"}]}}

    monkeypatch.setattr(module, "json_request", fake_json_request)

    assert module.preferred_epub_chapter_inventory(
        "https://api.example.test",
        "token",
        {"ebooks": [{"type": "file", "path": "/books/current.epub"}]},
        1.0,
    ) == {
        "default_epub_chapter_index_ready": False,
        "default_epub_chapters": 1,
        "default_epub_chapter_ranges_ready": False,
    }


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


def test_creation_template_inventory_accepts_empty_template_list() -> None:
    assert module.creation_template_inventory({"templates": []}) == {
        "creation_templates_route_ready": True,
        "creation_templates": 0,
    }
    assert module.creation_template_inventory(
        {"templates": [{"id": "draft-1"}, "ignored"]}
    ) == {
        "creation_templates_route_ready": True,
        "creation_templates": 1,
    }
    assert module.creation_template_inventory({}) == {
        "creation_templates_route_ready": False,
        "creation_templates": 0,
    }


def test_creation_template_mode_inventory_uses_template_list_shape() -> None:
    payloads = {
        "generated_book": {"templates": [{"id": "draft-1"}]},
        "narrate_ebook": {"templates": []},
        "subtitle_job": {"templates": [{"id": "draft-2"}, "ignored"]},
        "youtube_dub": {"templates": []},
    }
    assert module.creation_template_mode_inventory(payloads) == {
        "creation_templates_mode_route_ready": True,
        "creation_templates_mode_filtered": 2,
        "creation_template_modes_checked": 4,
        "creation_template_mode_issues": [],
    }
    assert module.creation_template_mode_inventory({"generated_book": {"templates": []}}) == {
        "creation_templates_mode_route_ready": False,
        "creation_templates_mode_filtered": 0,
        "creation_template_modes_checked": 4,
        "creation_template_mode_issues": ["narrate_ebook", "subtitle_job", "youtube_dub"],
    }


def test_creation_template_detail_inventory_accepts_missing_probe(monkeypatch) -> None:
    requested_paths: list[str] = []

    def fake_json_request(api_base_url: str, path: str, **kwargs):
        requested_paths.append(path)
        raise module.error.HTTPError(
            url=f"{api_base_url}{path}",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(module, "json_request", fake_json_request)

    assert module.creation_template_detail_inventory(
        "https://api.example.test",
        "token",
        2.0,
    ) == {"creation_template_detail_route_ready": True}
    assert requested_paths == [
        "/api/creation/templates/__apple_create_readiness_missing_template__"
    ]


def test_creation_template_detail_inventory_rejects_server_error(monkeypatch) -> None:
    def fake_json_request(api_base_url: str, path: str, **kwargs):
        raise module.error.HTTPError(
            url=f"{api_base_url}{path}",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(module, "json_request", fake_json_request)

    assert module.creation_template_detail_inventory(
        "https://api.example.test",
        "token",
        2.0,
    ) == {"creation_template_detail_route_ready": False}


def test_acquisition_provider_inventory_pins_registry_shape() -> None:
    providers = []
    for provider_id, requirements in module.REQUIRED_ACQUISITION_PROVIDERS.items():
        entry = {
            "id": provider_id,
            "label": provider_id.replace("_", " ").title(),
            "media_kinds": sorted(requirements["media_kinds"]),
            "capabilities": sorted(requirements["capabilities"]),
            "status": "planned" if provider_id == "zlibrary_attended" else "available",
            "configured": provider_id != "zlibrary_attended",
            "available": provider_id != "zlibrary_attended",
            "rights": ["unknown"],
            "policy_notes": (
                [
                    "Direct Z-Library automation is intentionally disabled.",
                    "Use an attended browser/download workflow only.",
                ]
                if provider_id == "zlibrary_attended"
                else ["Token-safe provider."]
            ),
        }
        discovery_media_kinds = sorted(
            module.REQUIRED_ACQUISITION_DISCOVERY_MEDIA_KINDS.get(provider_id, [])
        )
        if discovery_media_kinds:
            entry["discovery_media_kinds"] = discovery_media_kinds
        providers.append(add_source_label(entry, provider_id))

    assert module.acquisition_provider_inventory({
        "providers": providers,
        "default_provider_ids": {
            "book": ["local_epub"],
            "video": ["nas_video", "youtube_search"],
        },
    }) == {
        "acquisition_providers_ready": True,
        "acquisition_providers": len(module.REQUIRED_ACQUISITION_PROVIDERS),
        "missing_acquisition_providers": [],
        "invalid_acquisition_providers": [],
        "acquisition_default_providers_ready": True,
        "acquisition_default_book_providers": 1,
        "acquisition_default_video_providers": 2,
        "acquisition_default_provider_issues": [],
        "acquisition_source_labeled_providers": 3,
        "zlibrary_policy_ready": True,
        "download_station_handoff_ready": True,
        "download_station_handoff_issues": [],
    }


def test_acquisition_provider_inventory_normalizes_provider_ids_once() -> None:
    providers = []
    for provider_id, requirements in module.REQUIRED_ACQUISITION_PROVIDERS.items():
        entry = {
            "id": f" {provider_id} ",
            "label": provider_id,
            "media_kinds": sorted(requirements["media_kinds"]),
            "capabilities": sorted(requirements["capabilities"]),
            "available": provider_id != "zlibrary_attended",
            "policy_notes": (
                [
                    "Direct Z-Library automation is intentionally disabled.",
                    "Use an attended browser/download workflow only.",
                ]
                if provider_id == "zlibrary_attended"
                else []
            ),
        }
        discovery_media_kinds = sorted(
            module.REQUIRED_ACQUISITION_DISCOVERY_MEDIA_KINDS.get(provider_id, [])
        )
        if discovery_media_kinds:
            entry["discovery_media_kinds"] = discovery_media_kinds
        providers.append(add_source_label(entry, provider_id))

    inventory = module.acquisition_provider_inventory({
        "providers": providers,
        "default_provider_ids": {
            "book": ["local_epub"],
            "video": ["nas_video"],
        },
    })

    assert inventory["acquisition_providers_ready"] is True
    assert inventory["missing_acquisition_providers"] == []
    assert inventory["acquisition_default_provider_issues"] == []
    assert inventory["acquisition_source_labeled_providers"] == 3


def test_acquisition_provider_inventory_reports_missing_or_invalid_registry_entries() -> None:
    providers = [
        {
            "id": "local_epub",
            "media_kinds": ["book"],
            "capabilities": ["import_local", "metadata"],
            "available": True,
            "policy_notes": [],
        },
        {
            "id": "youtube_search",
            "media_kinds": ["video"],
            "capabilities": ["metadata"],
            "available": True,
            "policy_notes": [],
        },
        {
            "id": "zlibrary_attended",
            "media_kinds": ["book"],
            "capabilities": ["import_local"],
            "available": True,
            "policy_notes": ["Use attended import."],
        },
    ]

    inventory = module.acquisition_provider_inventory({"providers": providers})

    assert inventory["acquisition_providers_ready"] is False
    assert inventory["missing_acquisition_providers"] == [
        provider
        for provider in sorted(module.REQUIRED_ACQUISITION_PROVIDERS)
        if provider not in {"local_epub", "youtube_search", "zlibrary_attended"}
    ]
    assert inventory["invalid_acquisition_providers"] == [
        "local_epub.source_label",
        "youtube_search.capabilities:search",
        "zlibrary_attended.policy",
    ]
    assert inventory["acquisition_default_providers_ready"] is False
    assert inventory["acquisition_default_provider_issues"] == ["default_provider_ids"]
    assert inventory["zlibrary_policy_ready"] is False
    assert inventory["download_station_handoff_ready"] is False
    assert inventory["download_station_handoff_issues"] == [
        "newznab_torznab.missing",
        "download_station.missing",
    ]


def test_acquisition_provider_inventory_rejects_youtube_url_defaults_or_missing_discovery_kind() -> None:
    providers = []
    for provider_id, requirements in module.REQUIRED_ACQUISITION_PROVIDERS.items():
        entry = {
            "id": provider_id,
            "media_kinds": sorted(requirements["media_kinds"]),
            "capabilities": sorted(requirements["capabilities"]),
            "available": provider_id != "zlibrary_attended",
            "policy_notes": (
                [
                    "Direct Z-Library automation is intentionally disabled.",
                    "Use an attended browser/download workflow only.",
                ]
                if provider_id == "zlibrary_attended"
                else []
            ),
        }
        discovery_media_kinds = (
            []
            if provider_id == "youtube_url"
            else sorted(module.REQUIRED_ACQUISITION_DISCOVERY_MEDIA_KINDS.get(provider_id, []))
        )
        if provider_id == "youtube_url" or discovery_media_kinds:
            entry["discovery_media_kinds"] = discovery_media_kinds
        providers.append(add_source_label(entry, provider_id))

    inventory = module.acquisition_provider_inventory({
        "providers": providers,
        "default_provider_ids": {
            "book": ["local_epub"],
            "video": ["nas_video", "youtube_url"],
        },
    })

    assert inventory["acquisition_providers_ready"] is False
    assert inventory["invalid_acquisition_providers"] == [
        "youtube_url.discovery_media_kinds:video"
    ]
    assert inventory["acquisition_default_providers_ready"] is False
    assert inventory["acquisition_default_provider_issues"] == [
        "video.youtube_url.explicit_only"
    ]


def test_acquisition_provider_inventory_rejects_default_without_default_eligibility() -> None:
    providers = []
    for provider_id, requirements in module.REQUIRED_ACQUISITION_PROVIDERS.items():
        entry = {
            "id": provider_id,
            "media_kinds": sorted(requirements["media_kinds"]),
            "capabilities": sorted(requirements["capabilities"]),
            "available": provider_id == "local_epub",
            "policy_notes": (
                [
                    "Direct Z-Library automation is intentionally disabled.",
                    "Use an attended browser/download workflow only.",
                ]
                if provider_id == "zlibrary_attended"
                else []
            ),
            "discovery_media_kinds": sorted(
                module.REQUIRED_ACQUISITION_DISCOVERY_MEDIA_KINDS.get(provider_id, [])
            ),
        }
        if provider_id == "local_epub":
            entry["discovery_media_kinds"] = ["book"]
            entry["default_eligible_media_kinds"] = []
        if provider_id == "nas_video":
            entry["discovery_media_kinds"] = ["video"]
        providers.append(add_source_label(entry, provider_id))

    inventory = module.acquisition_provider_inventory({
        "providers": providers,
        "default_provider_ids": {
            "book": ["local_epub"],
            "video": ["nas_video"],
        },
    })

    assert inventory["acquisition_default_providers_ready"] is False
    assert inventory["acquisition_default_provider_issues"] == [
        "book.local_epub.default_eligible",
        "video.unavailable",
    ]


def test_acquisition_provider_inventory_reports_indexer_handoff_misconfiguration() -> None:
    providers = []
    for provider_id, requirements in module.REQUIRED_ACQUISITION_PROVIDERS.items():
        capabilities = sorted(requirements["capabilities"])
        if provider_id == "download_station":
            capabilities = ["poll"]
        providers.append(
            {
                "id": provider_id,
                "media_kinds": sorted(requirements["media_kinds"]),
                "capabilities": capabilities,
                "available": provider_id not in {"zlibrary_attended", "newznab_torznab"},
                "policy_notes": (
                    [
                        "Direct Z-Library automation is intentionally disabled.",
                        "Use an attended browser/download workflow only.",
                    ]
                    if provider_id == "zlibrary_attended"
                    else []
                ),
            }
        )

    inventory = module.acquisition_provider_inventory({
        "providers": providers,
        "default_provider_ids": {
            "book": ["local_epub"],
            "video": ["nas_video"],
        },
    })

    assert inventory["download_station_handoff_ready"] is False
    assert inventory["download_station_handoff_issues"] == [
        "newznab_torznab.available",
        "download_station.capabilities:acquire",
    ]


def test_acquisition_provider_inventory_reports_invalid_default_providers() -> None:
    providers = []
    for provider_id, requirements in module.REQUIRED_ACQUISITION_PROVIDERS.items():
        providers.append(
            {
                "id": provider_id,
                "media_kinds": sorted(requirements["media_kinds"]),
                "capabilities": sorted(requirements["capabilities"]),
                "available": provider_id != "zlibrary_attended",
                "policy_notes": (
                    [
                        "Direct Z-Library automation is intentionally disabled.",
                        "Use an attended browser/download workflow only.",
                    ]
                    if provider_id == "zlibrary_attended"
                    else []
                ),
            }
        )

    inventory = module.acquisition_provider_inventory({
        "providers": providers,
        "default_provider_ids": {
            "book": ["missing_catalog"],
            "video": ["local_epub"],
        },
    })

    assert inventory["acquisition_providers_ready"] is False
    assert inventory["acquisition_default_providers_ready"] is False
    assert inventory["acquisition_default_book_providers"] == 1
    assert inventory["acquisition_default_video_providers"] == 1
    assert inventory["acquisition_default_provider_issues"] == [
        "book.missing_catalog.missing",
        "video.local_epub.media_kind",
    ]


def test_acquisition_provider_inventory_reports_unavailable_default_providers() -> None:
    providers = []
    for provider_id, requirements in module.REQUIRED_ACQUISITION_PROVIDERS.items():
        providers.append(
            {
                "id": provider_id,
                "media_kinds": sorted(requirements["media_kinds"]),
                "discovery_media_kinds": sorted(requirements["media_kinds"]),
                "capabilities": sorted(requirements["capabilities"]),
                "available": provider_id
                not in {"local_epub", "nas_video", "zlibrary_attended"},
                "policy_notes": (
                    [
                        "Direct Z-Library automation is intentionally disabled.",
                        "Use an attended browser/download workflow only.",
                    ]
                    if provider_id == "zlibrary_attended"
                    else []
                ),
            }
        )

    inventory = module.acquisition_provider_inventory({
        "providers": providers,
        "default_provider_ids": {
            "book": ["local_epub"],
            "video": ["nas_video"],
        },
    })

    assert inventory["acquisition_providers_ready"] is False
    assert inventory["acquisition_default_providers_ready"] is False
    assert inventory["acquisition_default_provider_issues"] == [
        "book.unavailable",
        "video.unavailable",
    ]


def test_acquisition_discovery_inventory_checks_default_provider_routes(monkeypatch) -> None:
    paths: list[str] = []

    def fake_json_request(api_base_url: str, path: str, **kwargs):
        paths.append(path)
        assert kwargs.get("token") == "token"
        if path == "/api/acquisition/discover?media_kind=book&provider=local_epub&limit=1":
            return {
                "candidates": [
                    {
                        "candidate_id": "local_epub:origin",
                        "provider": "local_epub",
                        "media_kind": "book",
                        "title": "Origin",
                        "rights": "user_provided",
                        "capabilities": ["import_local"],
                        "candidate_token": "redacted-token",
                        "contributors": [],
                        "subtitles": [],
                        "requires_confirmation": False,
                        "policy_notes": [],
                    }
                ],
                "policy_notes": [],
                "providers_queried": ["local_epub"],
            }
        if path == "/api/acquisition/discover?media_kind=video&provider=nas_video&limit=1":
            return {
                "candidates": [],
                "policy_notes": ["NAS video candidates are local files."],
                "providers_queried": ["nas_video"],
            }
        raise AssertionError(f"unexpected path {path}")

    monkeypatch.setattr(module, "json_request", fake_json_request)

    inventory = module.acquisition_discovery_inventory(
        "https://api.example.test",
        "token",
        {
            "default_provider_ids": {
                "book": ["local_epub"],
                "video": ["nas_video", "youtube_search"],
            }
        },
        1.0,
    )

    assert paths == [
        "/api/acquisition/discover?media_kind=book&provider=local_epub&limit=1",
        "/api/acquisition/discover?media_kind=video&provider=nas_video&limit=1",
    ]
    assert inventory == {
        "acquisition_discovery_route_ready": True,
        "acquisition_book_discovery_candidates": 1,
        "acquisition_video_discovery_candidates": 0,
        "acquisition_book_discovery_providers": 1,
        "acquisition_video_discovery_providers": 1,
        "acquisition_discovery_issues": [],
    }


def test_acquisition_discovery_inventory_probes_first_available_default_provider(
    monkeypatch,
) -> None:
    paths: list[str] = []

    def fake_json_request(api_base_url: str, path: str, **kwargs):
        paths.append(path)
        provider = parse_query_value(path, "provider")
        return {
            "candidates": [],
            "policy_notes": [],
            "providers_queried": [provider],
        }

    monkeypatch.setattr(module, "json_request", fake_json_request)

    inventory = module.acquisition_discovery_inventory(
        "https://api.example.test",
        "token",
        {
            "providers": [
                {
                    "id": "local_epub",
                    "available": False,
                    "discovery_media_kinds": ["book"],
                },
                {
                    "id": "manual_downloads",
                    "available": True,
                    "discovery_media_kinds": ["book", "video"],
                },
                {
                    "id": "nas_video",
                    "available": False,
                    "discovery_media_kinds": ["video"],
                },
                {
                    "id": "youtube_search",
                    "available": True,
                    "discovery_media_kinds": ["video"],
                },
            ],
            "default_provider_ids": {
                "book": ["local_epub", "manual_downloads"],
                "video": ["nas_video", "youtube_search"],
            },
        },
        1.0,
    )

    assert paths == [
        "/api/acquisition/discover?media_kind=book&provider=manual_downloads&limit=1",
        "/api/acquisition/discover?media_kind=video&provider=youtube_search&limit=1",
    ]
    assert inventory["acquisition_discovery_route_ready"] is True
    assert inventory["acquisition_discovery_issues"] == []


def test_acquisition_discovery_inventory_reports_shape_issues(monkeypatch) -> None:
    def fake_json_request(api_base_url: str, path: str, **kwargs):
        if "media_kind=book" in path:
            return {
                "candidates": [{"candidate_id": "broken"}],
                "policy_notes": [],
                "providers_queried": ["openlibrary"],
            }
        return {"candidates": [], "policy_notes": [123], "providers_queried": []}

    monkeypatch.setattr(module, "json_request", fake_json_request)

    inventory = module.acquisition_discovery_inventory(
        "https://api.example.test",
        "token",
        {
            "default_provider_ids": {
                "book": ["local_epub"],
                "video": ["nas_video"],
            }
        },
        1.0,
    )

    assert inventory["acquisition_discovery_route_ready"] is False
    assert inventory["acquisition_book_discovery_candidates"] == 1
    assert inventory["acquisition_video_discovery_candidates"] == 0
    assert inventory["acquisition_discovery_issues"] == [
        "book.candidate_0.candidate_token",
        "book.candidate_0.capabilities",
        "book.candidate_0.contributors",
        "book.candidate_0.media_kind",
        "book.candidate_0.policy_notes",
        "book.candidate_0.provider",
        "book.candidate_0.requires_confirmation",
        "book.candidate_0.rights",
        "book.candidate_0.subtitles",
        "book.candidate_0.title",
        "book.providers_queried:local_epub",
        "video.policy_notes",
        "video.providers_queried:nas_video",
    ]


def test_acquisition_default_discovery_payload_accepts_default_fanout() -> None:
    payload = {
        "candidates": [
            {
                "candidate_id": "nas_video:demo",
                "provider": "nas_video",
                "media_kind": "video",
                "title": "Demo",
                "rights": "user_provided",
                "capabilities": ["use_local_video"],
                "candidate_token": "redacted-token",
                "contributors": [],
                "subtitles": [],
                "requires_confirmation": False,
                "policy_notes": [],
            }
        ],
        "policy_notes": [],
        "providers_queried": ["nas_video", "youtube_search"],
    }

    assert module.acquisition_default_discovery_payload_issues(
        payload,
        media_kind="video",
        expected_provider_ids=["nas_video", "youtube_search"],
    ) == []


def test_acquisition_default_discovery_payload_reports_unexpected_provider() -> None:
    payload = {
        "candidates": [
            {
                "candidate_id": "youtube_url:demo",
                "provider": "youtube_url",
                "media_kind": "video",
                "title": "Demo",
                "rights": "metadata_only",
                "capabilities": ["metadata"],
                "candidate_token": "redacted-token",
                "contributors": [],
                "subtitles": [],
                "requires_confirmation": False,
                "policy_notes": [],
            }
        ],
        "policy_notes": [],
        "providers_queried": ["youtube_url"],
    }

    assert module.acquisition_default_discovery_payload_issues(
        payload,
        media_kind="video",
        expected_provider_ids=["nas_video"],
    ) == [
        "candidate_0.provider:youtube_url",
        "providers_queried.default",
        "providers_queried.unexpected:youtube_url",
    ]


def test_acquisition_default_discovery_inventory_uses_no_provider_queries(monkeypatch) -> None:
    paths: list[str] = []

    def fake_json_request(api_base_url: str, path: str, **kwargs):
        paths.append(path)
        assert kwargs.get("token") == "token"
        if path == "/api/acquisition/discover?media_kind=book&limit=1":
            return {
                "candidates": [
                    {
                        "candidate_id": "local_epub:origin",
                        "provider": "local_epub",
                        "media_kind": "book",
                        "title": "Origin",
                        "rights": "user_provided",
                        "capabilities": ["import_local"],
                        "candidate_token": "redacted-token",
                        "contributors": [],
                        "subtitles": [],
                        "requires_confirmation": False,
                        "policy_notes": [],
                    }
                ],
                "policy_notes": [],
                "providers_queried": ["local_epub"],
            }
        if path == "/api/acquisition/discover?media_kind=video&limit=1":
            return {
                "candidates": [],
                "policy_notes": [],
                "providers_queried": ["nas_video", "youtube_search"],
            }
        raise AssertionError(f"unexpected path {path}")

    monkeypatch.setattr(module, "json_request", fake_json_request)

    inventory = module.acquisition_default_discovery_inventory(
        "https://api.example.test",
        "token",
        {
            "default_provider_ids": {
                "book": ["local_epub"],
                "video": ["nas_video", "youtube_search"],
            }
        },
        1.0,
    )

    assert paths == [
        "/api/acquisition/discover?media_kind=book&limit=1",
        "/api/acquisition/discover?media_kind=video&limit=1",
    ]
    assert inventory == {
        "acquisition_default_discovery_route_ready": True,
        "acquisition_default_book_discovery_candidates": 1,
        "acquisition_default_video_discovery_candidates": 0,
        "acquisition_default_book_discovery_providers": 1,
        "acquisition_default_video_discovery_providers": 2,
        "acquisition_default_discovery_issues": [],
    }


def test_acquisition_default_discovery_inventory_ignores_explicit_only_defaults(
    monkeypatch,
) -> None:
    def fake_json_request(api_base_url: str, path: str, **kwargs):
        raise AssertionError(f"unexpected path {path}")

    monkeypatch.setattr(module, "json_request", fake_json_request)

    inventory = module.acquisition_default_discovery_inventory(
        "https://api.example.test",
        "token",
        {"default_provider_ids": {"book": ["youtube_url"], "video": ["youtube_url"]}},
        1.0,
    )

    assert inventory == {
        "acquisition_default_discovery_route_ready": False,
        "acquisition_default_book_discovery_candidates": 0,
        "acquisition_default_video_discovery_candidates": 0,
        "acquisition_default_book_discovery_providers": 0,
        "acquisition_default_video_discovery_providers": 0,
        "acquisition_default_discovery_issues": [
            "book.default_provider",
            "video.default_provider",
        ],
    }


def test_acquisition_prepared_artifact_inventory_prepares_book_candidate(monkeypatch) -> None:
    paths: list[tuple[str, str]] = []

    def fake_json_request(api_base_url: str, path: str, **kwargs):
        paths.append((kwargs.get("method", "GET"), path))
        assert kwargs.get("token") == "token"
        if path == "/api/acquisition/discover?media_kind=book&provider=local_epub&limit=1":
            return {
                "candidates": [
                    {
                        "candidate_id": "local_epub:origin",
                        "provider": "local_epub",
                        "media_kind": "book",
                        "title": "Origin",
                        "rights": "user_provided",
                        "capabilities": ["import_local"],
                        "candidate_token": "token/with spaces",
                        "contributors": [],
                        "subtitles": [],
                        "requires_confirmation": False,
                        "policy_notes": [],
                    }
                ],
                "policy_notes": [],
                "providers_queried": ["local_epub"],
            }
        if path == "/api/acquisition/artifacts/token%2Fwith%20spaces/prepare":
            assert kwargs.get("method") == "POST"
            return {
                "provider": "local_epub",
                "media_kind": "book",
                "source_kind": "local_epub",
                "local_path": "Origin.epub",
                "input_file": "Origin.epub",
                "video_path": None,
                "subtitle_path": None,
                "subtitles": [],
                "next_actions": ["create_book_job", "load_content_index"],
                "metadata": {
                    "source_kind": "local_epub",
                    "source_provider": "local_epub",
                    "acquisition_provider": "local_epub",
                    "acquisition_candidate_id": "local_epub:Origin.epub",
                },
            }
        raise AssertionError(f"unexpected path {path}")

    monkeypatch.setattr(module, "json_request", fake_json_request)

    inventory = module.acquisition_prepared_artifact_inventory(
        "https://api.example.test",
        "token",
        {
            "providers": [
                {
                    "id": "local_epub",
                    "available": True,
                    "discovery_media_kinds": ["book"],
                }
            ],
            "default_provider_ids": {"book": ["local_epub"]},
        },
        1.0,
    )

    assert paths == [
        ("GET", "/api/acquisition/discover?media_kind=book&provider=local_epub&limit=1"),
        ("POST", "/api/acquisition/artifacts/token%2Fwith%20spaces/prepare"),
    ]
    assert inventory == {
        "acquisition_artifact_prepare_route_ready": True,
        "acquisition_artifact_prepare_issues": [],
    }


def test_acquisition_prepared_artifact_inventory_reports_payload_shape_issues(monkeypatch) -> None:
    def fake_json_request(api_base_url: str, path: str, **kwargs):
        if path == "/api/acquisition/discover?media_kind=book&provider=local_epub&limit=1":
            return {
                "candidates": [{"candidate_token": "prepared-token"}],
                "policy_notes": [],
                "providers_queried": ["local_epub"],
            }
        return {
            "provider": "manual_downloads",
            "media_kind": "video",
            "source_kind": "",
            "local_path": "Origin.epub",
            "input_file": "Different.epub",
            "next_actions": ["inspect"],
            "metadata": {},
        }

    monkeypatch.setattr(module, "json_request", fake_json_request)

    inventory = module.acquisition_prepared_artifact_inventory(
        "https://api.example.test",
        "token",
        {"default_provider_ids": {"book": ["local_epub"]}},
        1.0,
    )

    assert inventory == {
        "acquisition_artifact_prepare_route_ready": False,
        "acquisition_artifact_prepare_issues": [
            "input_file.local_path",
            "media_kind:book",
            "metadata.acquisition_candidate_id.empty",
            "metadata.acquisition_provider.empty",
            "metadata.source_kind.empty",
            "metadata.source_provider.empty",
            "next_actions:create_book_job",
            "provider:local_epub",
            "source_kind.empty",
        ],
    }


def test_acquisition_prepared_artifact_inventory_reports_missing_candidate_token(monkeypatch) -> None:
    def fake_json_request(api_base_url: str, path: str, **kwargs):
        return {
            "candidates": [{"candidate_id": "local_epub:origin"}],
            "policy_notes": [],
            "providers_queried": ["local_epub"],
        }

    monkeypatch.setattr(module, "json_request", fake_json_request)

    assert module.acquisition_prepared_artifact_inventory(
        "https://api.example.test",
        "token",
        {"default_provider_ids": {"book": ["local_epub"]}},
        1.0,
    ) == {
        "acquisition_artifact_prepare_route_ready": False,
        "acquisition_artifact_prepare_issues": ["book.candidate_token"],
    }


def test_acquisition_prepared_artifact_inventory_reuses_captured_discovery(monkeypatch) -> None:
    paths: list[str] = []

    def fake_json_request(api_base_url: str, path: str, **kwargs):
        paths.append(path)
        assert path == "/api/acquisition/artifacts/captured-token/prepare"
        return {
            "provider": "local_epub",
            "media_kind": "book",
            "source_kind": "local_epub",
            "local_path": "Captured.epub",
            "input_file": "Captured.epub",
            "next_actions": ["create_book_job"],
            "metadata": {
                "source_kind": "local_epub",
                "source_provider": "local_epub",
                "acquisition_provider": "local_epub",
                "acquisition_candidate_id": "local_epub:Captured.epub",
            },
        }

    monkeypatch.setattr(module, "json_request", fake_json_request)

    inventory = module.acquisition_prepared_artifact_inventory(
        "https://api.example.test",
        "token",
        {
            "providers": [
                {
                    "id": "local_epub",
                    "available": True,
                    "discovery_media_kinds": ["book"],
                }
            ],
            "default_provider_ids": {"book": ["local_epub"]},
        },
        1.0,
        discovery_payloads={
            "book": {
                "provider": "local_epub",
                "payload": {"candidates": [{"candidate_token": "captured-token"}]},
            }
        },
    )

    assert paths == ["/api/acquisition/artifacts/captured-token/prepare"]
    assert inventory == {
        "acquisition_artifact_prepare_route_ready": True,
        "acquisition_artifact_prepare_issues": [],
    }


def test_acquisition_prepared_artifact_inventory_prepares_video_candidate_when_available(
    monkeypatch,
) -> None:
    paths: list[str] = []

    def fake_json_request(api_base_url: str, path: str, **kwargs):
        paths.append(path)
        if path == "/api/acquisition/artifacts/book-token/prepare":
            assert kwargs.get("method") == "POST"
            return {
                "provider": "local_epub",
                "media_kind": "book",
                "source_kind": "local_epub",
                "local_path": "Origin.epub",
                "input_file": "Origin.epub",
                "next_actions": ["create_book_job", "load_content_index"],
                "metadata": {
                    "source_kind": "local_epub",
                    "source_provider": "local_epub",
                    "acquisition_provider": "local_epub",
                    "acquisition_candidate_id": "local_epub:Origin.epub",
                },
            }
        if path == "/api/acquisition/artifacts/video-token/prepare":
            assert kwargs.get("method") == "POST"
            return {
                "provider": "nas_video",
                "media_kind": "video",
                "source_kind": "nas_video",
                "local_path": "/nas/video.mp4",
                "input_file": None,
                "video_path": "/nas/video.mp4",
                "subtitle_path": "/nas/video.en.srt",
                "subtitles": [{"path": "/nas/video.en.srt", "filename": "video.en.srt"}],
                "next_actions": ["extract_subtitles", "create_dub_job"],
                "metadata": {
                    "source_kind": "nas_video",
                    "source_provider": "nas_video",
                    "acquisition_provider": "nas_video",
                    "acquisition_candidate_id": "nas_video:/nas/video.mp4",
                },
            }
        raise AssertionError(f"unexpected path {path}")

    monkeypatch.setattr(module, "json_request", fake_json_request)

    inventory = module.acquisition_prepared_artifact_inventory(
        "https://api.example.test",
        "token",
        {
            "providers": [
                {
                    "id": "local_epub",
                    "available": True,
                    "discovery_media_kinds": ["book"],
                },
                {
                    "id": "nas_video",
                    "available": True,
                    "discovery_media_kinds": ["video"],
                },
            ],
            "default_provider_ids": {"book": ["local_epub"], "video": ["nas_video"]},
        },
        1.0,
        discovery_payloads={
            "book": {
                "provider": "local_epub",
                "payload": {"candidates": [{"candidate_token": "book-token"}]},
            },
            "video": {
                "provider": "nas_video",
                "payload": {"candidates": [{"candidate_token": "video-token"}]},
            },
        },
    )

    assert paths == [
        "/api/acquisition/artifacts/book-token/prepare",
        "/api/acquisition/artifacts/video-token/prepare",
    ]
    assert inventory == {
        "acquisition_artifact_prepare_route_ready": True,
        "acquisition_artifact_prepare_issues": [],
    }


def test_acquisition_prepared_artifact_inventory_reports_video_payload_issues(
    monkeypatch,
) -> None:
    def fake_json_request(api_base_url: str, path: str, **kwargs):
        if path == "/api/acquisition/artifacts/book-token/prepare":
            return {
                "provider": "local_epub",
                "media_kind": "book",
                "source_kind": "local_epub",
                "local_path": "Origin.epub",
                "input_file": "Origin.epub",
                "next_actions": ["create_book_job"],
                "metadata": {
                    "source_kind": "local_epub",
                    "source_provider": "local_epub",
                    "acquisition_provider": "local_epub",
                    "acquisition_candidate_id": "local_epub:Origin.epub",
                },
            }
        if path == "/api/acquisition/artifacts/video-token/prepare":
            return {
                "provider": "manual_downloads",
                "media_kind": "book",
                "source_kind": "",
                "local_path": "/nas/video.mp4",
                "video_path": "/different/video.mp4",
                "subtitles": ["bad"],
                "next_actions": ["inspect"],
                "metadata": {},
            }
        raise AssertionError(f"unexpected path {path}")

    monkeypatch.setattr(module, "json_request", fake_json_request)

    inventory = module.acquisition_prepared_artifact_inventory(
        "https://api.example.test",
        "token",
        {
            "providers": [
                {
                    "id": "local_epub",
                    "available": True,
                    "discovery_media_kinds": ["book"],
                },
                {
                    "id": "nas_video",
                    "available": True,
                    "discovery_media_kinds": ["video"],
                },
            ],
            "default_provider_ids": {"book": ["local_epub"], "video": ["nas_video"]},
        },
        1.0,
        discovery_payloads={
            "book": {
                "provider": "local_epub",
                "payload": {"candidates": [{"candidate_token": "book-token"}]},
            },
            "video": {
                "provider": "nas_video",
                "payload": {"candidates": [{"candidate_token": "video-token"}]},
            },
        },
    )

    assert inventory == {
        "acquisition_artifact_prepare_route_ready": False,
        "acquisition_artifact_prepare_issues": [
            "video.media_kind:video",
            "video.metadata.acquisition_candidate_id.empty",
            "video.metadata.acquisition_provider.empty",
            "video.metadata.source_kind.empty",
            "video.metadata.source_provider.empty",
            "video.next_actions:create_dub_job",
            "video.provider:nas_video",
            "video.source_kind.empty",
            "video.subtitles.items",
            "video.video_path.local_path",
        ],
    }


def test_acquisition_prepared_artifact_metadata_issues_rejects_drift_and_tokens() -> None:
    assert module.acquisition_prepared_artifact_metadata_issues(
        {
            "source_kind": "manual_downloads",
            "source_provider": "manual_downloads",
            "acquisition_provider": "manual_downloads",
            "acquisition_candidate_id": "manual_downloads:book:Origin.epub",
            "candidate_token": "secret-token",
        },
        expected_provider="local_epub",
    ) == [
        "acquisition_provider:local_epub",
        "candidate_token.forbidden",
        "source_provider:local_epub",
    ]


def test_pipeline_intake_inventory_accepts_busy_queue_shape() -> None:
    assert module.pipeline_intake_inventory(
        {
            "acceptingJobs": True,
            "isUnderPressure": True,
            "queueDepth": 4,
            "activeCount": 2,
            "softLimit": 3,
            "hardLimit": 10,
            "delayCount": 7,
        }
    ) == {
        "pipeline_intake_ready": True,
        "pipeline_intake_accepting_jobs": True,
        "pipeline_intake_queue_depth": 4,
        "pipeline_intake_active_count": 2,
    }

    assert module.pipeline_intake_inventory(
        {
            "acceptingJobs": False,
            "isUnderPressure": True,
            "queueDepth": 10,
            "activeCount": 3,
            "softLimit": None,
            "hardLimit": None,
            "delayCount": 2,
        }
    ) == {
        "pipeline_intake_ready": True,
        "pipeline_intake_accepting_jobs": False,
        "pipeline_intake_queue_depth": 10,
        "pipeline_intake_active_count": 3,
    }


def test_pipeline_intake_inventory_rejects_malformed_shape() -> None:
    assert module.pipeline_intake_inventory(
        {
            "acceptingJobs": "yes",
            "isUnderPressure": False,
            "queueDepth": -1,
            "activeCount": True,
            "softLimit": None,
            "hardLimit": None,
            "delayCount": 0,
        }
    ) == {
        "pipeline_intake_ready": False,
        "pipeline_intake_accepting_jobs": False,
        "pipeline_intake_queue_depth": 0,
        "pipeline_intake_active_count": 0,
    }


def test_pipeline_defaults_inventory_checks_config_shape_without_values() -> None:
    assert module.pipeline_defaults_inventory(
        {"config": {"input_language": "English", "output_language": "Arabic"}}
    ) == {
        "pipeline_defaults_route_ready": True,
        "pipeline_defaults_config_keys": 2,
    }
    assert module.pipeline_defaults_inventory({"config": {}}) == {
        "pipeline_defaults_route_ready": True,
        "pipeline_defaults_config_keys": 0,
    }
    assert module.pipeline_defaults_inventory({"config": []}) == {
        "pipeline_defaults_route_ready": False,
        "pipeline_defaults_config_keys": 0,
    }


def test_model_inventory_accepts_empty_and_named_model_lists() -> None:
    assert module.model_inventory({"models": []}) == {
        "subtitle_models_ready": True,
        "subtitle_models": 0,
    }
    assert module.model_inventory({"models": ["ollama_local/demo", "", "lmstudio_local/demo"]}) == {
        "subtitle_models_ready": True,
        "subtitle_models": 2,
    }
    assert module.model_inventory({"models": ["valid", 123]}) == {
        "subtitle_models_ready": False,
        "subtitle_models": 1,
    }


def test_pipeline_llm_model_inventory_accepts_empty_and_named_model_lists() -> None:
    assert module.pipeline_llm_model_inventory({"models": []}) == {
        "pipeline_llm_models_ready": True,
        "pipeline_llm_models": 0,
    }
    assert module.pipeline_llm_model_inventory({"models": ["ollama_local/demo", "", "lmstudio_local/demo"]}) == {
        "pipeline_llm_models_ready": True,
        "pipeline_llm_models": 2,
    }
    assert module.pipeline_llm_model_inventory({"models": ["valid", 123]}) == {
        "pipeline_llm_models_ready": False,
        "pipeline_llm_models": 1,
    }


def test_image_node_availability_inventory_checks_shape_without_urls() -> None:
    assert module.image_node_availability_inventory(
        {
            "nodes": [
                {"base_url": "http://drawthings.local:7860", "available": True},
                {"base_url": "http://drawthings-backup.local:7860", "available": False},
            ],
            "available": ["http://drawthings.local:7860"],
            "unavailable": ["http://drawthings-backup.local:7860"],
        }
    ) == {
        "image_node_availability_ready": True,
        "image_nodes_checked": 2,
        "image_nodes_available": 1,
        "image_nodes_unavailable": 1,
    }
    assert module.image_node_availability_inventory(
        {"nodes": [], "available": [], "unavailable": []}
    ) == {
        "image_node_availability_ready": True,
        "image_nodes_checked": 0,
        "image_nodes_available": 0,
        "image_nodes_unavailable": 0,
    }
    assert module.image_node_availability_inventory(
        {"nodes": [{"base_url": "http://drawthings.local", "available": "yes"}], "available": [], "unavailable": []}
    ) == {
        "image_node_availability_ready": False,
        "image_nodes_checked": 1,
        "image_nodes_available": 0,
        "image_nodes_unavailable": 0,
    }


def test_voice_inventory_validates_voice_picker_shape() -> None:
    assert module.voice_inventory(
        {
            "macos": [{"name": "Samantha", "lang": "en_US", "quality": "premium", "gender": "Female"}],
            "gtts": [{"code": "en", "name": "English"}],
            "piper": [{"name": "en_US-lessac-medium", "lang": "en_US", "quality": "medium"}],
        }
    ) == {
        "voice_inventory_ready": True,
        "macos_voices": 1,
        "gtts_voices": 1,
        "piper_voices": 1,
    }
    assert module.voice_inventory({"macos": [], "gtts": [{"code": "en"}], "piper": []}) == {
        "voice_inventory_ready": False,
        "macos_voices": 0,
        "gtts_voices": 1,
        "piper_voices": 0,
    }


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
            "sentence_splitter_capabilities": build_sentence_splitter_capabilities(),
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
        "sentence_splitter_capabilities_ready": True,
        "subtitle_job_defaults_ready": True,
        "youtube_dub_defaults_ready": True,
        "generated_book_defaults_errors": [],
        "sentence_splitter_capabilities_errors": [],
        "subtitle_job_defaults_errors": [],
        "youtube_dub_defaults_errors": [],
    }

    bad_splitter = build_sentence_splitter_capabilities()
    bad_splitter["default_mode"] = "modern"
    assert isinstance(bad_splitter["supported_modes"], list)
    bad_splitter["supported_modes"][1]["cache_version"] = "old-modern"
    assert isinstance(bad_splitter["comparison_metric_fields"], list)
    bad_splitter["comparison_metric_fields"].remove("contiguous_text_preserved")

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
            "sentence_splitter_capabilities": bad_splitter,
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
        "sentence_splitter_capabilities_ready": False,
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
        "sentence_splitter_capabilities_errors": [
            "sentence_splitter_capabilities.default_mode",
            "sentence_splitter_capabilities.supported_modes.modern.cache_version",
            "sentence_splitter_capabilities.comparison_metric_fields.contiguous_text_preserved",
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
            "default_epub_chapter_index_ready": True,
            "default_epub_chapters": 12,
            "default_epub_chapter_ranges_ready": True,
            "default_subtitle_source_ready": True,
            "default_youtube_video_ready": True,
            "default_youtube_subtitle_ready": True,
            "book_input_languages": 65,
            "book_output_languages": 65,
            "missing_book_input_languages": [],
            "missing_book_output_languages": [],
            "generated_book_defaults_ready": True,
            "sentence_splitter_capabilities_ready": True,
            "subtitle_job_defaults_ready": True,
            "youtube_dub_defaults_ready": True,
            "generated_book_defaults_errors": [],
            "sentence_splitter_capabilities_errors": [],
            "subtitle_job_defaults_errors": [],
            "youtube_dub_defaults_errors": [],
            "pipeline_defaults_route_ready": True,
            "pipeline_defaults_config_keys": 17,
            "creation_templates_route_ready": True,
            "creation_templates_mode_route_ready": True,
            "creation_templates_mode_filtered": 0,
            "creation_template_modes_checked": 4,
            "creation_template_mode_issues": [],
            "creation_template_detail_route_ready": True,
            "creation_templates": 0,
            "acquisition_providers_ready": True,
            "acquisition_providers": len(module.REQUIRED_ACQUISITION_PROVIDERS),
            "missing_acquisition_providers": [],
            "invalid_acquisition_providers": [],
            "acquisition_default_providers_ready": True,
            "acquisition_default_book_providers": 1,
            "acquisition_default_video_providers": 2,
            "acquisition_default_provider_issues": [],
            "acquisition_source_labeled_providers": 3,
            "zlibrary_policy_ready": True,
            "download_station_handoff_ready": True,
            "download_station_handoff_issues": [],
            "acquisition_discovery_route_ready": True,
            "acquisition_book_discovery_candidates": 1,
            "acquisition_video_discovery_candidates": 1,
            "acquisition_book_discovery_providers": 1,
            "acquisition_video_discovery_providers": 1,
            "acquisition_discovery_issues": [],
            "acquisition_default_discovery_route_ready": True,
            "acquisition_default_book_discovery_candidates": 1,
            "acquisition_default_video_discovery_candidates": 1,
            "acquisition_default_book_discovery_providers": 1,
            "acquisition_default_video_discovery_providers": 2,
            "acquisition_default_discovery_issues": [],
            "acquisition_artifact_prepare_route_ready": True,
            "acquisition_artifact_prepare_issues": [],
            "acquisition_job_status_route_ready": True,
            "acquisition_job_status_issues": [],
            "pipeline_intake_ready": True,
            "pipeline_intake_accepting_jobs": True,
            "pipeline_intake_queue_depth": 1,
            "pipeline_intake_active_count": 0,
            "subtitle_models_ready": True,
            "subtitle_models": 2,
            "pipeline_llm_models_ready": True,
            "pipeline_llm_models": 2,
            "image_node_availability_ready": True,
            "image_nodes_checked": 0,
            "image_nodes_available": 0,
            "image_nodes_unavailable": 0,
            "voice_inventory_ready": True,
            "macos_voices": 1,
            "gtts_voices": 1,
            "piper_voices": 0,
        }
    ) == []
    assert module.validate_summary(
        {
            "epubs": 0,
            "subtitle_sources": 0,
            "youtube_videos": 1,
            "youtube_subtitles": 0,
            "default_epub_ready": False,
            "default_epub_chapter_index_ready": False,
            "default_epub_chapters": 0,
            "default_epub_chapter_ranges_ready": False,
            "default_subtitle_source_ready": False,
            "default_youtube_video_ready": True,
            "default_youtube_subtitle_ready": False,
            "book_input_languages": 6,
            "book_output_languages": 6,
            "missing_book_input_languages": ["hindi"],
            "missing_book_output_languages": ["persian"],
            "generated_book_defaults_ready": False,
            "sentence_splitter_capabilities_ready": False,
            "subtitle_job_defaults_ready": False,
            "youtube_dub_defaults_ready": False,
            "generated_book_defaults_errors": ["defaults.voice"],
            "sentence_splitter_capabilities_errors": ["sentence_splitter_capabilities.supported_modes.modern.cache_version"],
            "subtitle_job_defaults_errors": ["batch_size"],
            "youtube_dub_defaults_errors": ["target_height"],
            "pipeline_defaults_route_ready": False,
            "pipeline_defaults_config_keys": 0,
            "creation_templates_route_ready": False,
            "creation_templates_mode_route_ready": False,
            "creation_templates_mode_filtered": 0,
            "creation_template_modes_checked": 4,
            "creation_template_mode_issues": ["subtitle_job", "youtube_dub"],
            "creation_template_detail_route_ready": False,
            "creation_templates": 0,
            "acquisition_providers_ready": False,
            "acquisition_providers": 3,
            "missing_acquisition_providers": ["nas_video"],
            "invalid_acquisition_providers": [
                "local_epub.source_label",
                "youtube_search.capabilities:search",
                "zlibrary_attended.policy",
            ],
            "acquisition_default_providers_ready": False,
            "acquisition_default_book_providers": 0,
            "acquisition_default_video_providers": 1,
            "acquisition_default_provider_issues": ["book.missing", "video.local_epub.media_kind"],
            "acquisition_source_labeled_providers": 0,
            "zlibrary_policy_ready": False,
            "download_station_handoff_ready": False,
            "download_station_handoff_issues": ["download_station.capabilities:acquire"],
            "acquisition_discovery_route_ready": False,
            "acquisition_book_discovery_candidates": 0,
            "acquisition_video_discovery_candidates": 0,
            "acquisition_book_discovery_providers": 0,
            "acquisition_video_discovery_providers": 0,
            "acquisition_discovery_issues": ["book.default_provider"],
            "acquisition_default_discovery_route_ready": False,
            "acquisition_default_book_discovery_candidates": 0,
            "acquisition_default_video_discovery_candidates": 0,
            "acquisition_default_book_discovery_providers": 0,
            "acquisition_default_video_discovery_providers": 0,
            "acquisition_default_discovery_issues": ["video.providers_queried.default"],
            "acquisition_artifact_prepare_route_ready": False,
            "acquisition_artifact_prepare_issues": ["book.candidate_token"],
            "acquisition_job_status_route_ready": False,
            "acquisition_job_status_issues": ["status"],
            "pipeline_intake_ready": False,
            "pipeline_intake_accepting_jobs": False,
            "pipeline_intake_queue_depth": 0,
            "pipeline_intake_active_count": 0,
            "subtitle_models_ready": False,
            "subtitle_models": 0,
            "pipeline_llm_models_ready": False,
            "pipeline_llm_models": 0,
            "image_node_availability_ready": False,
            "image_nodes_checked": 0,
            "image_nodes_available": 0,
            "image_nodes_unavailable": 0,
            "voice_inventory_ready": False,
            "macos_voices": 0,
            "gtts_voices": 0,
            "piper_voices": 0,
        }
    ) == [
        "backend-visible EPUBs",
        "backend-visible subtitle sources",
        "YouTube/NAS videos with playable subtitles",
        "default Narrate EPUB source",
        "default Narrate EPUB chapter index",
        "default subtitle source",
        "default YouTube/NAS video+subtitle selection",
        "broad book input language options",
        "broad book output language options",
        "book input language sentinels: hindi",
        "book output language sentinels: persian",
        "generated book defaults: defaults.voice",
        "sentence splitter capabilities: sentence_splitter_capabilities.supported_modes.modern.cache_version",
        "subtitle job processing defaults: batch_size",
        "YouTube dubbing processing defaults: target_height",
        "pipeline defaults endpoint",
        "creation template list endpoint",
        "creation template mode-filtered list endpoint: subtitle_job, youtube_dub",
        "creation template detail endpoint",
        "acquisition provider registry: missing nas_video; invalid local_epub.source_label, youtube_search.capabilities:search, zlibrary_attended.policy; default book.missing, video.local_epub.media_kind",
        "Download Station indexer handoff: download_station.capabilities:acquire",
        "acquisition discovery endpoint: book.default_provider",
        "default acquisition discovery fanout: video.providers_queried.default",
        "acquisition artifact prepare endpoint: book.candidate_token",
        "acquisition job status endpoint: status",
        "pipeline intake status endpoint",
        "subtitle model inventory endpoint",
        "pipeline LLM model inventory endpoint",
        "image-node availability endpoint",
        "audio voice inventory endpoint",
    ]


def test_runtime_create_contract_validation() -> None:
    assert module.validate_runtime_create_contract(build_runtime_payload()) == []

    assert module.validate_runtime_create_contract({}) == [
        "runtime descriptor is missing auth metadata",
        "runtime descriptor is missing creation metadata",
        "runtime descriptor is missing libraryActions metadata",
        "runtime descriptor is missing pipelineJobs metadata",
        "runtime descriptor is missing pipelineMedia metadata",
        "runtime descriptor is missing linguist metadata",
        "runtime descriptor is missing offlineExports metadata",
        "runtime descriptor is missing playbackState metadata",
        "runtime descriptor is missing notifications metadata",
    ]

    payload = build_runtime_payload()
    payload["creation"] = {
        "bookOptionsPath": "/old/books/options",
        "bookJobsPath": "",
    }
    assert module.validate_runtime_create_contract(payload) == [
        "bookOptionsPath=/old/books/options expected /api/books/options",
        "bookJobsPath=<missing> expected /api/books/jobs",
        "pipelineFilesPath=<missing> expected /api/pipelines/files",
        "pipelineContentIndexPath=<missing> expected /api/pipelines/files/content-index",
        "pipelineUploadPath=<missing> expected /api/pipelines/files/upload",
        "pipelineJobsPath=<missing> expected /api/pipelines",
        "pipelineIntakeStatusPath=<missing> expected /api/pipelines/intake/status",
        "pipelineDefaultsPath=<missing> expected /api/pipelines/defaults",
        "pipelineLlmModelsPath=<missing> expected /api/pipelines/llm-models",
        "pipelineSearchPath=<missing> expected /api/pipelines/search",
        "imageNodeAvailabilityPath=<missing> expected /api/pipelines/image-nodes/availability",
        "audioVoicesPath=<missing> expected /api/audio/voices",
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
        "acquisitionProvidersPath=<missing> expected /api/acquisition/providers",
        "acquisitionDiscoverPath=<missing> expected /api/acquisition/discover",
        "acquisitionAcquirePath=<missing> expected /api/acquisition/acquire",
        "acquisitionArtifactPreparePathTemplate=<missing> expected /api/acquisition/artifacts/{artifact_id}/prepare",
        "acquisitionJobsPath=<missing> expected /api/acquisition/jobs",
        "acquisitionJobPathTemplate=<missing> expected /api/acquisition/jobs/{task_id}",
        "templateListPath=<missing> expected /api/creation/templates",
        "templatePathTemplate=<missing> expected /api/creation/templates/{template_id}",
    ]

    payload = build_runtime_payload()
    payload["auth"]["oauthPath"] = "/old/oauth"
    payload["libraryActions"]["isbnLookupPath"] = ""
    payload["pipelineJobs"]["restartPathTemplate"] = "/old/restart/{job_id}"
    payload["pipelineMedia"]["jobTimingPathTemplate"] = ""
    payload["linguist"]["audioSynthesisPath"] = "/old/audio"
    payload["offlineExports"]["sourceKinds"] = ["job"]
    payload["playbackState"].pop("resumeListPath")
    payload["notifications"]["preferencesPath"] = "/old/preferences"
    assert module.validate_runtime_create_contract(payload) == [
        "auth.oauthPath=/old/oauth expected /api/auth/oauth",
        "libraryActions.isbnLookupPath=<missing> expected /api/library/isbn/lookup",
        "pipelineJobs.restartPathTemplate=/old/restart/{job_id} expected /api/pipelines/jobs/{job_id}/restart",
        "pipelineMedia.jobTimingPathTemplate=<missing> expected /api/jobs/{job_id}/timing",
        "linguist.audioSynthesisPath=/old/audio expected /api/audio",
        "offlineExports.sourceKinds=['job'] expected ['job', 'library']",
        "playbackState.resumeListPath=<missing> expected /api/resume",
        "notifications.preferencesPath=/old/preferences expected /api/notifications/preferences",
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
            "Backend runtime Apple contract is not ready: "
            "runtime descriptor is missing auth metadata; "
            "runtime descriptor is missing creation metadata; "
            "runtime descriptor is missing libraryActions metadata; "
            "runtime descriptor is missing pipelineJobs metadata; "
            "runtime descriptor is missing pipelineMedia metadata; "
            "runtime descriptor is missing linguist metadata; "
            "runtime descriptor is missing offlineExports metadata; "
            "runtime descriptor is missing playbackState metadata; "
            "runtime descriptor is missing notifications metadata"
        )
    else:
        raise AssertionError("fetch_readiness should fail on missing runtime Create contract")

    assert paths == ["/api/system/runtime"]


def test_fetch_readiness_includes_creation_option_default_contract(monkeypatch) -> None:
    paths: list[str] = []

    def fake_json_request(api_base_url: str, path: str, **kwargs):
        paths.append(path)
        if path == "/api/system/runtime":
            return build_runtime_payload()
        if path == module.EXPECTED_PIPELINE_FILES_PICKER_PATH:
            return {"ebooks": [{"type": "file", "path": "/books/current.epub"}]}
        if path == "/api/pipelines/files/content-index?input_file=%2Fbooks%2Fcurrent.epub":
            return {
                "content_index": {
                    "chapters": [{"title": "Chapter 1"}],
                    "alignment": {
                        "chapter_range_coverage": {
                            "contiguous_unique_ranges": True,
                        },
                    },
                }
            }
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
                "sentence_splitter_capabilities": build_sentence_splitter_capabilities(),
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
        if path == module.EXPECTED_PIPELINE_DEFAULTS_PATH:
            return {"config": {"input_language": "English", "output_language": "Arabic"}}
        if path == "/api/creation/templates":
            return {"templates": []}
        if path == "/api/creation/templates?mode=generated_book":
            return {"templates": []}
        if path == "/api/creation/templates?mode=narrate_ebook":
            return {"templates": []}
        if path == "/api/creation/templates?mode=subtitle_job":
            return {"templates": []}
        if path == "/api/creation/templates?mode=youtube_dub":
            return {"templates": []}
        if path == "/api/creation/templates/__apple_create_readiness_missing_template__":
            raise module.error.HTTPError(
                url=f"{api_base_url}{path}",
                code=404,
                msg="Not Found",
                hdrs=None,
                fp=None,
            )
        if path == module.EXPECTED_ACQUISITION_PROVIDERS_PATH:
            providers = []
            for provider_id, requirements in module.REQUIRED_ACQUISITION_PROVIDERS.items():
                entry = {
                    "id": provider_id,
                    "media_kinds": sorted(requirements["media_kinds"]),
                    "capabilities": sorted(requirements["capabilities"]),
                    "available": provider_id != "zlibrary_attended",
                    "policy_notes": (
                        [
                            "Direct Z-Library automation is intentionally disabled.",
                            "Use an attended browser/download workflow only.",
                        ]
                        if provider_id == "zlibrary_attended"
                        else []
                    ),
                }
                discovery_media_kinds = sorted(
                    module.REQUIRED_ACQUISITION_DISCOVERY_MEDIA_KINDS.get(provider_id, [])
                )
                if discovery_media_kinds:
                    entry["discovery_media_kinds"] = discovery_media_kinds
                providers.append(add_source_label(entry, provider_id))
            return {
                "providers": providers,
                "default_provider_ids": {
                    "book": ["local_epub"],
                    "video": ["nas_video", "youtube_search"],
                },
            }
        if path == "/api/acquisition/discover?media_kind=book&provider=local_epub&limit=1":
            return {
                "candidates": [
                    {
                        "candidate_id": "local_epub:current",
                        "provider": "local_epub",
                        "media_kind": "book",
                        "title": "Current",
                        "rights": "user_provided",
                        "capabilities": ["import_local"],
                        "candidate_token": "redacted-token",
                        "contributors": [],
                        "subtitles": [],
                        "requires_confirmation": False,
                        "policy_notes": [],
                    }
                ],
                "policy_notes": [],
                "providers_queried": ["local_epub"],
            }
        if path == "/api/acquisition/discover?media_kind=video&provider=nas_video&limit=1":
            return {
                "candidates": [
                    {
                        "candidate_id": "nas_video:current",
                        "provider": "nas_video",
                        "media_kind": "video",
                        "title": "Current Video",
                        "rights": "user_provided",
                        "capabilities": ["select_video", "extract_subtitles"],
                        "candidate_token": "video-token",
                        "contributors": [],
                        "subtitles": [
                            {
                                "path": "/video/current.en.srt",
                                "filename": "current.en.srt",
                                "language": "en",
                            }
                        ],
                        "requires_confirmation": False,
                        "policy_notes": [],
                    }
                ],
                "policy_notes": [],
                "providers_queried": ["nas_video"],
            }
        if path == "/api/acquisition/discover?media_kind=book&limit=1":
            return {
                "candidates": [
                    {
                        "candidate_id": "local_epub:current",
                        "provider": "local_epub",
                        "media_kind": "book",
                        "title": "Current",
                        "rights": "user_provided",
                        "capabilities": ["import_local"],
                        "candidate_token": "redacted-token",
                        "contributors": [],
                        "subtitles": [],
                        "requires_confirmation": False,
                        "policy_notes": [],
                    }
                ],
                "policy_notes": [],
                "providers_queried": ["local_epub"],
            }
        if path == "/api/acquisition/discover?media_kind=video&limit=1":
            return {
                "candidates": [
                    {
                        "candidate_id": "nas_video:current",
                        "provider": "nas_video",
                        "media_kind": "video",
                        "title": "Current Video",
                        "rights": "user_provided",
                        "capabilities": ["select_video", "extract_subtitles"],
                        "candidate_token": "video-token",
                        "contributors": [],
                        "subtitles": [
                            {
                                "path": "/video/current.en.srt",
                                "filename": "current.en.srt",
                                "language": "en",
                            }
                        ],
                        "requires_confirmation": False,
                        "policy_notes": [],
                    }
                ],
                "policy_notes": [],
                "providers_queried": ["nas_video", "youtube_search"],
            }
        if path == "/api/acquisition/artifacts/redacted-token/prepare":
            assert kwargs.get("method") == "POST"
            return {
                "provider": "local_epub",
                "media_kind": "book",
                "source_kind": "local_epub",
                "local_path": "current.epub",
                "input_file": "current.epub",
                "video_path": None,
                "subtitle_path": None,
                "subtitles": [],
                "next_actions": ["create_book_job", "load_content_index"],
                "metadata": {
                    "source_kind": "local_epub",
                    "source_provider": "local_epub",
                    "acquisition_provider": "local_epub",
                    "acquisition_candidate_id": "local_epub:current.epub",
                },
            }
        if path == "/api/acquisition/artifacts/video-token/prepare":
            assert kwargs.get("method") == "POST"
            return {
                "provider": "nas_video",
                "media_kind": "video",
                "source_kind": "nas_video",
                "local_path": "/video/current.mp4",
                "input_file": None,
                "video_path": "/video/current.mp4",
                "subtitle_path": "/video/current.en.srt",
                "subtitles": [
                    {
                        "path": "/video/current.en.srt",
                        "filename": "current.en.srt",
                        "language": "en",
                    }
                ],
                "next_actions": ["extract_subtitles", "create_dub_job"],
                "metadata": {
                    "source_kind": "nas_video",
                    "source_provider": "nas_video",
                    "acquisition_provider": "nas_video",
                    "acquisition_candidate_id": "nas_video:/video/current.mp4",
                },
            }
        if path == "/api/acquisition/jobs/download_station%3Asubmitted?provider=download_station":
            return {
                "provider": "download_station",
                "task_id": "download_station:submitted",
                "status": "submitted",
                "progress": None,
                "message": "Use manual downloads discovery after completion.",
                "external_task_id": None,
                "raw_status": None,
                "started_at": None,
                "updated_at": "2026-06-27T00:00:00Z",
                "completed_files": [],
                "next_actions": ["discover_manual_downloads", "import_local"],
                "metadata": {"source_kind": "download_station"},
            }
        if path == "/api/pipelines/intake/status":
            return {
                "acceptingJobs": True,
                "isUnderPressure": True,
                "queueDepth": 4,
                "activeCount": 2,
                "softLimit": 3,
                "hardLimit": 10,
                "delayCount": 5,
            }
        if path == "/api/subtitles/models":
            return {"models": ["ollama_local/demo"]}
        if path == module.EXPECTED_PIPELINE_LLM_MODELS_PATH:
            return {"models": ["ollama_local/demo", "lmstudio_local/demo"]}
        if path == module.EXPECTED_IMAGE_NODE_AVAILABILITY_PATH:
            assert kwargs.get("method") == "POST"
            assert kwargs.get("payload") == {"base_urls": []}
            return {"nodes": [], "available": [], "unavailable": []}
        if path == "/api/audio/voices":
            return {
                "macos": [{"name": "Samantha", "lang": "en_US"}],
                "gtts": [{"code": "en", "name": "English"}],
                "piper": [],
            }
        raise AssertionError(f"unexpected path {path}")

    monkeypatch.setattr(module, "json_request", fake_json_request)

    summary = module.fetch_readiness("https://api.example.test", "token", 1.0)

    assert paths == [
        "/api/system/runtime",
        module.EXPECTED_PIPELINE_FILES_PICKER_PATH,
        "/api/subtitles/sources",
        "/api/subtitles/youtube/library",
        "/api/books/options",
        "/api/pipelines/defaults",
        "/api/creation/templates",
        "/api/creation/templates?mode=generated_book",
        "/api/creation/templates?mode=narrate_ebook",
        "/api/creation/templates?mode=subtitle_job",
        "/api/creation/templates?mode=youtube_dub",
        "/api/acquisition/providers",
        "/api/pipelines/intake/status",
        "/api/subtitles/models",
        "/api/pipelines/llm-models",
        "/api/pipelines/image-nodes/availability",
        "/api/audio/voices",
        "/api/pipelines/files/content-index?input_file=%2Fbooks%2Fcurrent.epub",
        "/api/creation/templates/__apple_create_readiness_missing_template__",
        "/api/acquisition/discover?media_kind=book&provider=local_epub&limit=1",
        "/api/acquisition/discover?media_kind=video&provider=nas_video&limit=1",
        "/api/acquisition/discover?media_kind=book&limit=1",
        "/api/acquisition/discover?media_kind=video&limit=1",
        "/api/acquisition/artifacts/redacted-token/prepare",
        "/api/acquisition/artifacts/video-token/prepare",
        "/api/acquisition/jobs/download_station%3Asubmitted?provider=download_station",
    ]
    assert summary["generated_book_defaults_ready"] is True
    assert summary["sentence_splitter_capabilities_ready"] is True
    assert summary["sentence_splitter_capabilities_errors"] == []
    assert summary["subtitle_job_defaults_ready"] is True
    assert summary["youtube_dub_defaults_ready"] is True
    assert summary["pipeline_defaults_route_ready"] is True
    assert summary["pipeline_defaults_config_keys"] == 2
    assert summary["default_epub_chapter_index_ready"] is True
    assert summary["default_epub_chapters"] == 1
    assert summary["default_epub_chapter_ranges_ready"] is True
    assert summary["creation_templates_route_ready"] is True
    assert summary["creation_templates_mode_route_ready"] is True
    assert summary["creation_templates_mode_filtered"] == 0
    assert summary["creation_template_modes_checked"] == 4
    assert summary["creation_template_mode_issues"] == []
    assert summary["creation_template_detail_route_ready"] is True
    assert summary["creation_templates"] == 0
    assert summary["acquisition_providers_ready"] is True
    assert summary["acquisition_providers"] == len(module.REQUIRED_ACQUISITION_PROVIDERS)
    assert summary["acquisition_default_providers_ready"] is True
    assert summary["acquisition_default_book_providers"] == 1
    assert summary["acquisition_default_video_providers"] == 2
    assert summary["acquisition_default_provider_issues"] == []
    assert summary["acquisition_source_labeled_providers"] == 3
    assert summary["zlibrary_policy_ready"] is True
    assert summary["download_station_handoff_ready"] is True
    assert summary["download_station_handoff_issues"] == []
    assert summary["acquisition_discovery_route_ready"] is True
    assert summary["acquisition_book_discovery_candidates"] == 1
    assert summary["acquisition_video_discovery_candidates"] == 1
    assert summary["acquisition_book_discovery_providers"] == 1
    assert summary["acquisition_video_discovery_providers"] == 1
    assert summary["acquisition_discovery_issues"] == []
    assert summary["acquisition_default_discovery_route_ready"] is True
    assert summary["acquisition_default_book_discovery_candidates"] == 1
    assert summary["acquisition_default_video_discovery_candidates"] == 1
    assert summary["acquisition_default_book_discovery_providers"] == 1
    assert summary["acquisition_default_video_discovery_providers"] == 2
    assert summary["acquisition_default_discovery_issues"] == []
    assert summary["acquisition_artifact_prepare_route_ready"] is True
    assert summary["acquisition_artifact_prepare_issues"] == []
    assert summary["acquisition_job_status_route_ready"] is True
    assert summary["acquisition_job_status_issues"] == []
    assert summary["pipeline_intake_ready"] is True
    assert summary["pipeline_intake_accepting_jobs"] is True
    assert summary["pipeline_intake_queue_depth"] == 4
    assert summary["pipeline_intake_active_count"] == 2
    assert summary["subtitle_models_ready"] is True
    assert summary["subtitle_models"] == 1
    assert summary["pipeline_llm_models_ready"] is True
    assert summary["pipeline_llm_models"] == 2
    assert summary["image_node_availability_ready"] is True
    assert summary["image_nodes_checked"] == 0
    assert summary["image_nodes_available"] == 0
    assert summary["image_nodes_unavailable"] == 0
    assert summary["voice_inventory_ready"] is True
    assert summary["macos_voices"] == 1
    assert summary["gtts_voices"] == 1
    assert summary["piper_voices"] == 0


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
