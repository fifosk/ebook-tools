from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from modules.library import (
    LibraryEntry,
    LibraryError,
    LibraryNotFoundError,
    LibraryRepository,
    LibraryService,
    LibrarySync,
    MetadataSnapshot,
)
from modules.library import library_sync as library_sync_module
from modules.library.sync import file_ops
from modules.services.file_locator import FileLocator

pytestmark = pytest.mark.library


class TrackingJobManager:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_job(self, job_id: str, **_kwargs) -> None:
        self.deleted.append(job_id)


def build_job_metadata(job_id: str) -> dict:
    return {
        'job_id': job_id,
        'author': 'Jane Doe',
        'book_title': 'Sample Book',
        'genre': 'Fiction',
        'language': 'en',
        'status': 'completed',
        'created_at': '2024-01-01T00:00:00+00:00',
        'updated_at': '2024-01-01T00:00:00+00:00',
        'media_completed': True,
        'generated_files': {'chunks': [], 'files': [], 'complete': True},
        'sources': [],
        'artifacts': {}
    }


def write_metadata(job_root: Path, payload: dict) -> None:
    metadata_dir = job_root / 'metadata'
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / 'job.json').write_text(json.dumps(payload), encoding='utf-8')


def create_service(tmp_path: Path) -> tuple[LibrarySync, FileLocator, Path, TrackingJobManager]:
    queue_root = tmp_path / 'queue'
    library_root = tmp_path / 'library'
    locator = FileLocator(storage_dir=queue_root)
    repository = LibraryRepository(library_root)
    job_manager = TrackingJobManager()
    service = LibrarySync(
        library_root=library_root,
        file_locator=locator,
        repository=repository,
        job_manager=job_manager
    )
    return service, locator, library_root, job_manager


def test_prepare_youtube_dub_bundle_uses_safe_stat_for_media_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _locator, _library_root, _job_manager = create_service(tmp_path)
    job_id = "video-job"
    job_root = tmp_path / "source" / job_id
    media_root = job_root / "media"
    metadata_dir = job_root / "metadata"
    media_root.mkdir(parents=True)
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "job.json").write_text(json.dumps({"job_id": job_id}), encoding="utf-8")
    video_path = media_root / "sample.dub.full.mp4"
    subtitle_path = media_root / "sample.dub.full.vtt"
    video_path.write_bytes(b"video")
    subtitle_path.write_text("WEBVTT", encoding="utf-8")
    original_exists = Path.exists
    original_is_file = Path.is_file

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path in {media_root, subtitle_path, metadata_dir}:
            raise AssertionError("YouTube dub bundle paths should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    def guarded_is_file(path: Path, *args, **kwargs) -> bool:
        if path == video_path:
            raise AssertionError("YouTube dub media files should be probed via safe_stat")
        return original_is_file(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_file", guarded_is_file)

    staging_root, metadata = service._prepare_youtube_dub_library_bundle(
        job_id,
        job_root=job_root,
        metadata={"job_id": job_id, "job_type": "youtube_dub"},
    )

    assert metadata["generated_files"]["files"][0]["relative_path"] == "media/sample.dub.full.mp4"
    assert metadata["generated_files"]["files"][1]["relative_path"] == "media/sample.dub.full.vtt"
    assert original_exists(staging_root / "media" / "sample.dub.full.mp4")
    assert original_exists(staging_root / "media" / "sample.dub.full.vtt")
    shutil.rmtree(staging_root, ignore_errors=True)


def test_move_to_library_and_index(tmp_path):
    service, locator, library_root, job_manager = create_service(tmp_path)

    job_id = 'job-42'
    queue_root = locator.job_root(job_id)
    queue_root.mkdir(parents=True)
    write_metadata(queue_root, build_job_metadata(job_id))
    (queue_root / 'media').mkdir(parents=True, exist_ok=True)
    (queue_root / 'media' / 'clip.mp3').write_bytes(b'123')

    item = service.move_to_library(job_id, status_override='finished')

    library_path = library_root / 'Jane Doe' / 'Sample Book' / 'en' / 'job-42'
    assert library_path.exists()
    assert not queue_root.exists()
    assert item.status == 'finished'

    stored = service._repository.get_entry_by_id(job_id)
    assert stored is not None
    assert stored.library_path == str(library_path.resolve())

    metadata_path = library_path / 'metadata' / 'job.json'
    payload = json.loads(metadata_path.read_text(encoding='utf-8'))
    assert payload['status'] == 'finished'
    assert job_manager.deleted == [job_id]


def test_move_to_library_uses_safe_stat_for_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, locator, library_root, job_manager = create_service(tmp_path)
    job_id = "job-safe-roots"
    queue_root = locator.job_root(job_id)
    queue_root.mkdir(parents=True)
    write_metadata(queue_root, build_job_metadata(job_id))
    (queue_root / "media").mkdir(parents=True, exist_ok=True)
    (queue_root / "media" / "clip.mp3").write_bytes(b"123")
    target_path = library_root / "Jane Doe" / "Sample Book" / "en" / job_id
    original_exists = Path.exists

    def fake_atomic_move(source: Path, destination: Path, **_kwargs) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination)
        shutil.rmtree(source)

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path in {queue_root, target_path}:
            raise AssertionError("library move roots should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(library_sync_module, "atomic_move", fake_atomic_move)
    monkeypatch.setattr(Path, "exists", guarded_exists)

    item = service.move_to_library(job_id, status_override="finished")

    assert item.id == job_id
    assert item.library_path == str(target_path.resolve())
    assert original_exists(target_path / "metadata" / "job.json")
    assert job_manager.deleted == [job_id]


def test_move_youtube_dub_to_library_uses_safe_stat_for_stitched_detection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, locator, library_root, job_manager = create_service(tmp_path)
    job_id = "video-safe-roots"
    queue_root = locator.job_root(job_id)
    media_root = queue_root / "media"
    media_root.mkdir(parents=True)
    metadata = build_job_metadata(job_id)
    metadata["job_type"] = "youtube_dub"
    write_metadata(queue_root, metadata)
    video_path = media_root / "sample.dub.full.mp4"
    video_path.write_bytes(b"video")
    target_path = library_root / "Jane Doe" / "Sample Book" / "en" / job_id
    original_exists = Path.exists
    original_is_file = Path.is_file

    def fake_atomic_move(source: Path, destination: Path, **_kwargs) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination)
        shutil.rmtree(source)

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path in {queue_root, target_path, media_root}:
            raise AssertionError("library YouTube move roots should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    def guarded_is_file(path: Path, *args, **kwargs) -> bool:
        if path == video_path:
            raise AssertionError("library YouTube stitched candidates should be probed via safe_stat")
        return original_is_file(path, *args, **kwargs)

    monkeypatch.setattr(library_sync_module, "atomic_move", fake_atomic_move)
    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_file", guarded_is_file)

    item = service.move_to_library(job_id, status_override="finished")

    assert item.id == job_id
    assert item.item_type == "video"
    assert original_exists(target_path / "media" / "sample.dub.full.mp4")
    assert job_manager.deleted == [job_id]


def test_library_service_import_book_uses_safe_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    library_root = tmp_path / "library"
    source_root = tmp_path / "incoming"
    metadata = build_job_metadata("job-import")
    write_metadata(source_root, metadata)
    target_root = library_root / "Jane Doe" / "Sample Book" / "en" / "job-import"
    service = LibraryService(library_root=library_root)
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path in {source_root, source_root / "metadata" / "job.json", target_root}:
            raise AssertionError("library import paths should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    entry = service.import_book(source_root)

    assert entry.id == "job-import"
    assert original_exists(target_root / "metadata" / "job.json")
    assert service.repository.get_entry_by_id("job-import") is not None


def test_library_service_export_entry_uses_safe_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    library_root = tmp_path / "library"
    source_root = library_root / "job-export"
    write_metadata(source_root, build_job_metadata("job-export"))
    repository = LibraryRepository(library_root)
    repository.add_entry(
        LibraryEntry(
            id="job-export",
            author="Jane Doe",
            book_title="Sample Book",
            item_type="book",
            genre="Fiction",
            language="en",
            status="finished",
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-01T00:00:00+00:00",
            library_path=str(source_root),
            metadata=MetadataSnapshot(metadata=build_job_metadata("job-export")),
        )
    )
    service = LibraryService(library_root=library_root, repository=repository)
    destination = tmp_path / "exports" / "job-export.zip"
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path == source_root:
            raise AssertionError("library export source should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    exported = service.export_entry("job-export", destination=destination)

    assert exported == destination
    assert original_exists(destination)


def test_remove_media_and_entry(tmp_path, monkeypatch: pytest.MonkeyPatch):
    service, locator, library_root, _job_manager = create_service(tmp_path)

    job_id = 'job-7'
    queue_root = locator.job_root(job_id)
    queue_root.mkdir(parents=True)
    write_metadata(queue_root, build_job_metadata(job_id))

    service.move_to_library(job_id)

    library_path = library_root / 'Jane Doe' / 'Sample Book' / 'en' / 'job-7'
    media_dir = library_path / 'media'
    media_dir.mkdir(parents=True, exist_ok=True)
    (media_dir / 'audio.mp3').write_bytes(b'audio')
    (media_dir / 'notes.txt').write_text('keep me', encoding='utf-8')
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path in {library_path, library_path.parent}:
            raise AssertionError("library remove paths should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    updated_item, removed = service.remove_media(job_id)
    assert removed == 1
    assert updated_item is not None
    assert not original_exists(media_dir / 'audio.mp3')
    assert original_exists(media_dir / 'notes.txt')
    metadata_payload = json.loads((library_path / 'metadata' / 'job.json').read_text(encoding='utf-8'))
    assert metadata_payload.get('media_completed') is False

    service.remove_entry(job_id)
    assert not original_exists(library_path)
    assert service._repository.get_entry_by_id(job_id) is None

    with pytest.raises(LibraryNotFoundError):
        service.remove_entry(job_id)


def test_move_paused_job_requires_completed_media(tmp_path):
    service, locator, library_root, job_manager = create_service(tmp_path)

    job_id = 'job-paused'
    queue_root = locator.job_root(job_id)
    queue_root.mkdir(parents=True)
    metadata = build_job_metadata(job_id)
    metadata['status'] = 'paused'
    metadata['media_completed'] = False
    metadata['generated_files'] = {'chunks': [], 'files': []}
    write_metadata(queue_root, metadata)

    with pytest.raises(LibraryError):
        service.move_to_library(job_id)
    assert job_manager.deleted == []

    metadata['media_completed'] = True
    metadata['generated_files'] = {'chunks': [], 'files': [], 'complete': True}
    write_metadata(queue_root, metadata)
    (queue_root / 'media').mkdir(parents=True, exist_ok=True)

    item = service.move_to_library(job_id)
    assert item.status == 'paused'
    assert job_manager.deleted == [job_id]


def test_move_paused_job_with_partial_media(tmp_path):
    service, locator, library_root, job_manager = create_service(tmp_path)

    job_id = 'job-paused-partial'
    queue_root = locator.job_root(job_id)
    queue_root.mkdir(parents=True)
    metadata = build_job_metadata(job_id)
    metadata['status'] = 'paused'
    metadata['media_completed'] = False
    metadata['generated_files'] = {
        'chunks': [
            {
                'chunk_id': 'chunk-001',
                'range_fragment': 'sentences=1-10',
                'files': [
                    {'type': 'audio', 'path': '/tmp/audio-1.mp3'}
                ]
            }
        ],
        'files': []
    }
    write_metadata(queue_root, metadata)

    (queue_root / 'media').mkdir(parents=True, exist_ok=True)

    item = service.move_to_library(job_id)
    assert item.status == 'paused'
    stored = service._repository.get_entry_by_id(job_id)
    assert stored is not None
    payload = json.loads((library_root / 'Jane Doe' / 'Sample Book' / 'en' / job_id / 'metadata' / 'job.json').read_text(encoding='utf-8'))
    assert payload.get('media_completed') is True
    assert job_manager.deleted == [job_id]


def test_move_paused_job_with_filesystem_media(tmp_path):
    service, locator, library_root, job_manager = create_service(tmp_path)

    job_id = 'job-paused-fs'
    queue_root = locator.job_root(job_id)
    queue_root.mkdir(parents=True)
    metadata = build_job_metadata(job_id)
    metadata['status'] = 'paused'
    metadata['media_completed'] = False
    metadata['generated_files'] = {'chunks': [], 'files': []}
    write_metadata(queue_root, metadata)

    media_dir = queue_root / 'media'
    media_dir.mkdir(parents=True, exist_ok=True)
    (media_dir / 'chunk-01.mp3').write_bytes(b'mock audio')

    item = service.move_to_library(job_id)
    assert item.status == 'paused'
    snapshot = json.loads((library_root / 'Jane Doe' / 'Sample Book' / 'en' / job_id / 'metadata' / 'job.json').read_text(encoding='utf-8'))
    assert snapshot.get('media_completed') is True
    assert job_manager.deleted == [job_id]


def test_generated_file_paths_retargeted_on_move(tmp_path):
    service, locator, library_root, _job_manager = create_service(tmp_path)

    job_id = 'job-retarget'
    queue_root = locator.job_root(job_id)
    queue_root.mkdir(parents=True)
    metadata = build_job_metadata(job_id)
    metadata['status'] = 'paused'
    metadata['media_completed'] = True
    metadata['generated_files'] = {
        'chunks': [
            {
                'chunk_id': 'chunk-001',
                'files': [
                    {
                        'type': 'audio',
                        'path': '/tmp/queue-root/media/chunk-001/audio.mp3',
                        'relative_path': 'media/chunk-001/audio.mp3'
                    }
                ]
            }
        ],
        'files': []
    }
    write_metadata(queue_root, metadata)

    item = service.move_to_library(job_id)
    metadata_path = Path(item.library_path) / 'metadata' / 'job.json'
    stored = json.loads(metadata_path.read_text(encoding='utf-8'))
    generated = stored.get('generated_files')
    assert isinstance(generated, dict)
    chunk_files = generated['chunks'][0]['files'][0]
    assert chunk_files['relative_path'] == 'media/chunk-001/audio.mp3'
    expected_absolute = (Path(item.library_path) / chunk_files['relative_path']).resolve().as_posix()
    assert chunk_files['path'] == expected_absolute
    assert chunk_files['url'].startswith(f"/api/library/media/{job_id}/file/")

    media_map, chunk_records, complete = service.get_media(job_id)
    assert complete is True
    assert 'audio' in media_map
    audio_entry = media_map['audio'][0]
    assert audio_entry['url'] == chunk_files['url']
    assert audio_entry['path'] == chunk_files['path']
    assert chunk_records and chunk_records[0]['files'][0]['url'] == chunk_files['url']


def test_serialize_media_entries_loads_chunk_file_once_for_full_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_root = tmp_path / "job"
    (job_root / "metadata").mkdir(parents=True)
    (job_root / "metadata" / "job.json").write_text("{}", encoding="utf-8")
    (job_root / "media").mkdir()
    (job_root / "media" / "audio.mp3").write_bytes(b"audio")

    class CountingMetadataLoader:
        instances: list["CountingMetadataLoader"] = []

        def __init__(self, _job_root: Path) -> None:
            self.load_chunk_calls = 0
            self.load_chunk_sentences_calls = 0
            self.include_sentences_values: list[bool] = []
            self.instances.append(self)

        def load_chunk(self, chunk: dict, *, include_sentences: bool = True) -> dict:
            self.load_chunk_calls += 1
            self.include_sentences_values.append(include_sentences)
            payload = {
                key: value
                for key, value in chunk.items()
                if key != "sentences"
            }
            payload["sentence_count"] = 1
            if include_sentences:
                payload["sentences"] = [{"sentence_number": 1, "text": "Loaded once"}]
            return payload

        def load_chunk_sentences(self, _chunk: dict) -> list[dict]:
            self.load_chunk_sentences_calls += 1
            return [{"sentence_number": 1, "text": "Loaded twice"}]

    monkeypatch.setattr(file_ops, "MetadataLoader", CountingMetadataLoader)
    generated_files = {
        "complete": True,
        "chunks": [
            {
                "chunk_id": "chunk-001",
                "range_fragment": "1-1",
                "metadata_path": "metadata/chunk_0001.json",
                "files": [
                    {
                        "name": "audio.mp3",
                        "relative_path": "media/audio.mp3",
                        "type": "audio",
                    }
                ],
            }
        ],
    }

    media_map, chunk_records, complete = file_ops.serialize_media_entries(
        "job-1",
        generated_files,
        job_root,
        include_stats=False,
        include_chunk_sentences=True,
        include_chunk_metadata=True,
    )

    loader = CountingMetadataLoader.instances[0]
    assert complete is True
    assert media_map["audio"][0]["url"] == "/api/library/media/job-1/file/media/audio.mp3"
    assert chunk_records[0]["sentences"] == [{"sentence_number": 1, "text": "Loaded once"}]
    assert chunk_records[0]["sentence_count"] == 1
    assert loader.load_chunk_calls == 1
    assert loader.include_sentences_values == [True]
    assert loader.load_chunk_sentences_calls == 0


def test_serialize_media_entries_sorts_chunks_by_sentence_range(tmp_path: Path) -> None:
    job_root = tmp_path / "job"
    job_root.mkdir()
    generated_files = {
        "complete": True,
        "chunks": [
            {
                "chunk_id": "chunk-2230",
                "range_fragment": "02230-02239",
                "start_sentence": 2230,
                "end_sentence": 2240,
                "files": [
                    {
                        "type": "audio",
                        "relative_path": "media/translation-2230.mp3",
                    }
                ],
            },
            {
                "chunk_id": "chunk-2210",
                "range_fragment": "02210-02219",
                "start_sentence": 2210,
                "end_sentence": 2220,
                "files": [
                    {
                        "type": "audio",
                        "relative_path": "media/translation-2210.mp3",
                    }
                ],
            },
            {
                "chunk_id": "chunk-2220",
                "range_fragment": "02220-02229",
                "start_sentence": 2220,
                "end_sentence": 2230,
                "files": [
                    {
                        "type": "audio",
                        "relative_path": "media/translation-2220.mp3",
                    }
                ],
            },
        ],
    }

    media_map, chunk_records, complete = file_ops.serialize_media_entries(
        "job-1",
        generated_files,
        job_root,
        include_stats=False,
        include_chunk_sentences=False,
        include_chunk_metadata=False,
    )

    assert complete is True
    assert "audio" in media_map
    assert [chunk["chunk_id"] for chunk in chunk_records] == [
        "chunk-2210",
        "chunk-2220",
        "chunk-2230",
    ]
    assert [chunk["start_sentence"] for chunk in chunk_records] == [2210, 2220, 2230]


def test_reindex_from_filesystem(tmp_path):
    service, _locator, library_root, _job_manager = create_service(tmp_path)

    job_root = library_root / 'Manual Author' / 'Manual Title' / 'en' / 'job-900'
    job_root.mkdir(parents=True)
    write_metadata(job_root, build_job_metadata('job-900'))

    indexed = service.reindex_from_fs()
    assert indexed == 1
    assert service._repository.get_entry_by_id('job-900') is not None
