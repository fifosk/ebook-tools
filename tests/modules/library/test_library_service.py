from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.library import LibraryError, LibraryIndexer, LibraryNotFoundError, LibraryService
from modules.services.file_locator import FileLocator


class TrackingJobManager:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_job(self, job_id: str) -> None:
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


def create_service(tmp_path: Path) -> tuple[LibraryService, FileLocator, Path, TrackingJobManager]:
    queue_root = tmp_path / 'queue'
    library_root = tmp_path / 'library'
    locator = FileLocator(storage_dir=queue_root)
    indexer = LibraryIndexer(library_root)
    job_manager = TrackingJobManager()
    service = LibraryService(
        library_root=library_root,
        file_locator=locator,
        indexer=indexer,
        job_manager=job_manager
    )
    return service, locator, library_root, job_manager


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

    stored = service._indexer.get(job_id)
    assert stored is not None
    assert stored.library_path == str(library_path.resolve())

    metadata_path = library_path / 'metadata' / 'job.json'
    payload = json.loads(metadata_path.read_text(encoding='utf-8'))
    assert payload['status'] == 'finished'
    assert job_manager.deleted == [job_id]


def test_remove_media_and_entry(tmp_path):
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

    updated_item, removed = service.remove_media(job_id)
    assert removed == 1
    assert updated_item is not None
    assert not (media_dir / 'audio.mp3').exists()
    assert (media_dir / 'notes.txt').exists()
    metadata_payload = json.loads((library_path / 'metadata' / 'job.json').read_text(encoding='utf-8'))
    assert metadata_payload.get('media_completed') is False

    service.remove_entry(job_id)
    assert not library_path.exists()
    assert service._indexer.get(job_id) is None

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
    stored = service._indexer.get(job_id)
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


def test_reindex_from_filesystem(tmp_path):
    service, _locator, library_root, _job_manager = create_service(tmp_path)

    job_root = library_root / 'Manual Author' / 'Manual Title' / 'en' / 'job-900'
    job_root.mkdir(parents=True)
    write_metadata(job_root, build_job_metadata('job-900'))

    indexed = service.reindex_from_fs()
    assert indexed == 1
    assert service._indexer.get('job-900') is not None
