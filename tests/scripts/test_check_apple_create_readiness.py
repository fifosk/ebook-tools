from __future__ import annotations

import importlib.util
from pathlib import Path


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


def test_validate_summary_reports_missing_create_sources() -> None:
    assert module.validate_summary(
        {
            "epubs": 1,
            "subtitle_sources": 1,
            "youtube_videos": 1,
            "youtube_subtitles": 1,
        }
    ) == []
    assert module.validate_summary(
        {
            "epubs": 0,
            "subtitle_sources": 0,
            "youtube_videos": 1,
            "youtube_subtitles": 0,
        }
    ) == [
        "backend-visible EPUBs",
        "backend-visible subtitle sources",
        "YouTube/NAS videos with playable subtitles",
    ]


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
