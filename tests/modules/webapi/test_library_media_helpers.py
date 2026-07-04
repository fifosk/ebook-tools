from __future__ import annotations

import inspect

from modules.webapi.routers import library_media
from modules.webapi.routers.library_media import (
    build_library_media_response,
    library_media_file_url,
)


def test_library_media_file_url_normalizes_and_quotes_paths() -> None:
    assert library_media_file_url(
        "job/with space",
        r" \media\chunk one\translation track.m4a ",
    ) == (
        "/api/library/media/job%2Fwith%20space/file/"
        "media/chunk%20one/translation%20track.m4a"
    )


def test_library_media_diagnostics_use_shared_gap_counter() -> None:
    source = inspect.getsource(library_media.build_library_media_diagnostics)

    assert "count_media_gaps(" in source
    assert "chunks_without_files + chunks_without_metadata" not in source


def test_library_media_response_normalizes_audio_and_timing_tracks() -> None:
    response = build_library_media_response(
        job_id="library-job",
        media_map={
            "audio": [
                {
                    "name": "translation.m4a",
                    "path": "media/chunk/translation.m4a",
                    "source": "completed",
                }
            ]
        },
        chunk_records=[
            {
                "chunk_id": "chunk-001",
                "range_fragment": "1-1",
                "start_sentence": 1,
                "end_sentence": 1,
                "files": [
                    {
                        "name": "translation.m4a",
                        "path": "media/chunk/translation.m4a",
                        "source": "completed",
                    }
                ],
                "sentence_count": 1,
                "audio_tracks": {
                    "translation": {
                        "path": "media/chunk/translation.m4a",
                        "duration": 1.2,
                    },
                    "original": {
                        "path": "media/chunk/original.m4a",
                        "url": "/already-present.m4a",
                    },
                    "ignored": "   ",
                },
                "timingTracks": {
                    "translation": [
                        {
                            "text": "Hallo",
                            "start": 0.0,
                            "end": 0.4,
                        }
                    ],
                    "empty": [],
                    42: [{"text": "ignored"}],
                },
            }
        ],
        complete=True,
    )

    chunk = response.chunks[0]
    assert response.complete is True
    assert chunk.audio_tracks["translation"].url.endswith(
        "/api/library/media/library-job/file/media/chunk/translation.m4a"
    )
    assert chunk.audio_tracks["original"].url == "/already-present.m4a"
    assert "ignored" not in chunk.audio_tracks
    assert chunk.timing_tracks == {
        "translation": [{"text": "Hallo", "start": 0.0, "end": 0.4}]
    }
    assert response.diagnostics.media_file_count == 1
    assert response.diagnostics.chunk_count == 1
    assert response.diagnostics.chunks_with_audio == 1
    assert response.diagnostics.chunks_with_timing == 1
    assert response.diagnostics.files_without_url == 1
    assert response.diagnostics.gap_count == 3


def test_library_media_response_diagnostics_detect_sentence_images() -> None:
    response = build_library_media_response(
        job_id="library-job",
        media_map={},
        chunk_records=[
            {
                "chunk_id": "chunk-001",
                "files": [],
                "sentences": [
                    {
                        "sentence_number": 1,
                        "original": {"text": "Hello", "tokens": ["Hello"]},
                        "image_path": "media/images/sentence_00001.png",
                    }
                ],
            }
        ],
        complete=False,
    )

    assert response.diagnostics.chunk_count == 1
    assert response.diagnostics.chunks_with_images == 1
    assert response.diagnostics.chunks_without_files == 1
    assert response.diagnostics.chunks_without_metadata == 0
    assert response.diagnostics.gap_count == 1
