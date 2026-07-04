from dataclasses import dataclass, field

from modules.services.media_diagnostics import (
    build_camel_media_diagnostic_counts,
    build_media_diagnostic_counts,
    count_media_gaps,
)


@dataclass
class _MediaFile:
    name: str
    type: str | None = None
    url: str | None = None
    size: int | None = None


@dataclass
class _Sentence:
    timeline: list[dict] = field(default_factory=list)
    image_path: str | None = None


@dataclass
class _Chunk:
    files: list[_MediaFile] = field(default_factory=list)
    sentences: list[_Sentence] = field(default_factory=list)
    metadata_path: str | None = None
    metadata_url: str | None = None
    audio_tracks: dict[str, dict] = field(default_factory=dict)
    timing_tracks: dict[str, list[dict]] | None = None


def test_count_media_gaps_sums_warning_counters() -> None:
    assert count_media_gaps(
        chunks_without_files=2,
        chunks_without_metadata=3,
        files_without_url=5,
        files_without_size=7,
    ) == 17


def test_build_media_diagnostic_counts_handles_route_models() -> None:
    counts = build_media_diagnostic_counts(
        {
            "audio": [_MediaFile(name="translation.m4a", type="audio", url="/media/translation.m4a", size=42)],
            "images": [_MediaFile(name="sentence.png", type="image", url=None)],
        },
        [
            _Chunk(
                files=[_MediaFile(name="translation.m4a", type="audio")],
                sentences=[_Sentence(timeline=[{"word": "Hello"}], image_path="media/images/1.png")],
                metadata_path="metadata/chunk_0000.json",
                audio_tracks={"translation": {"url": "/media/translation.m4a"}},
                timing_tracks={"translation": [{"text": "Hello"}]},
            ),
            _Chunk(),
        ],
    )

    assert counts == {
        "media_file_count": 2,
        "chunk_count": 2,
        "chunk_file_count": 1,
        "audio_file_count": 1,
        "image_file_count": 1,
        "chunks_with_audio": 1,
        "chunks_with_timing": 1,
        "chunks_with_images": 1,
        "chunks_without_files": 1,
        "chunks_without_metadata": 1,
        "files_without_url": 1,
        "files_without_size": 1,
        "gap_count": 4,
    }


def test_build_media_diagnostic_counts_handles_export_dicts_with_camel_keys() -> None:
    counts = build_camel_media_diagnostic_counts(
        {"audio": [{"name": "chunk.mp3", "type": "audio", "url": "media/chunk.mp3", "size": 42}]},
        [
            {
                "files": [{"name": "chunk.mp3", "type": "audio", "url": "media/chunk.mp3"}],
                "sentences": [{"timeline": [{"word": "Hello"}], "imagePath": "media/images/1.png"}],
                "audioTracks": {"translation": {"url": "media/chunk.mp3"}},
                "timingTracks": {"translation": [{"text": "Hello"}]},
                "metadataPath": "metadata/chunk_0000.json",
            }
        ],
    )

    assert counts["mediaFileCount"] == 1
    assert counts["chunksWithAudio"] == 1
    assert counts["chunksWithTiming"] == 1
    assert counts["chunksWithImages"] == 1
    assert counts["gapCount"] == 0
