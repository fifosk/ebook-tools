from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from modules.library import LibraryRepository, LibrarySync
from modules.services.file_locator import FileLocator
from modules.webapi.application import create_app
from modules.webapi import dependencies
from modules.webapi.dependencies import RequestUserContext


def _build_job_metadata(job_id: str, *, author: str = 'Jane Doe', title: str = 'Sample Book') -> dict:
    return {
        'job_id': job_id,
        'author': author,
        'book_title': title,
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


def _write_metadata(job_root: Path, payload: dict) -> None:
    metadata_dir = job_root / 'metadata'
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / 'job.json').write_text(json.dumps(payload), encoding='utf-8')


def _create_library_service(tmp_path: Path) -> tuple[LibrarySync, FileLocator, Path, Path]:
    queue_root = tmp_path / 'queue'
    library_root = tmp_path / 'library'
    locator = FileLocator(storage_dir=queue_root)
    repository = LibraryRepository(library_root)
    service = LibrarySync(library_root=library_root, file_locator=locator, repository=repository)
    return service, locator, library_root, queue_root


def test_update_metadata_moves_and_updates_snapshot(tmp_path):
    service, locator, library_root, queue_root = _create_library_service(tmp_path)

    job_id = 'job-100'
    queue_job_root = locator.job_root(job_id)
    queue_job_root.mkdir(parents=True)
    _write_metadata(queue_job_root, _build_job_metadata(job_id))

    service.move_to_library(job_id, status_override='finished')

    updated = service.update_metadata(
        job_id,
        title='Atlas of Dreams',
        author='Mary Shelley',
        genre='Gothic',
        language='fr'
    )

    # The library path should reflect the updated metadata.
    updated_path = Path(updated.library_path)
    assert updated_path.exists()
    assert updated.book_title == 'Atlas of Dreams'
    assert updated.author == 'Mary Shelley'
    assert updated.genre == 'Gothic'
    assert updated.language == 'fr'

    snapshot_path = updated_path / 'metadata' / 'job.json'
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    assert snapshot['book_title'] == 'Atlas of Dreams'
    assert snapshot['author'] == 'Mary Shelley'
    assert snapshot['genre'] == 'Gothic'
    assert snapshot['language'] == 'fr'


def test_refresh_metadata_infers_and_copies_cover(tmp_path, monkeypatch):
    service, locator, library_root, queue_root = _create_library_service(tmp_path)

    job_id = 'job-refresh'
    queue_job_root = locator.job_root(job_id)
    queue_job_root.mkdir(parents=True)
    metadata = _build_job_metadata(job_id)
    epub_path = queue_job_root / 'input.epub'
    epub_path.write_bytes(b'EPUB placeholder')
    metadata['input_file'] = str(epub_path)
    _write_metadata(queue_job_root, metadata)

    service.move_to_library(job_id, status_override='finished')
    library_job_root = Path(service._repository.get_entry_by_id(job_id).library_path)  # type: ignore[union-attr]

    cover_source = tmp_path / 'cover-source.png'
    cover_source.write_bytes(b'PNG DATA')

    inferred_payload = {
        'book_title': 'Refreshed Title',
        'book_author': 'Refreshed Author',
        'book_cover_file': str(cover_source),
        'book_summary': 'Updated summary from refresher.'
    }

    def _fake_infer(path: str, *, existing_metadata=None, force_refresh=False):
        assert Path(path) == library_job_root / 'data' / 'input.epub'
        return inferred_payload

    monkeypatch.setattr('modules.library.library_metadata.metadata_manager.infer_metadata', _fake_infer)

    refreshed = service.refresh_metadata(job_id)

    assert refreshed.book_title == 'Refreshed Title'
    assert refreshed.author == 'Refreshed Author'
    assert refreshed.cover_path is not None

    cover_path = library_job_root / refreshed.cover_path
    assert cover_path.exists()

    snapshot_path = library_job_root / 'metadata' / 'job.json'
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    summary = snapshot.get('book_metadata', {}).get('book_summary')
    assert summary == 'Updated summary from refresher.'

    # Ensure reindex respects the refreshed payload.
    indexed = service.reindex_from_fs()
    assert indexed == 1
    stored = service._repository.get_entry_by_id(job_id)
    assert stored is not None
    assert stored.book_title == 'Refreshed Title'
    assert stored.metadata.data


def test_search_endpoint_includes_library_results(tmp_path):
    service, locator, library_root, queue_root = _create_library_service(tmp_path)

    job_id = 'search-job'
    queue_job_root = locator.job_root(job_id)
    queue_job_root.mkdir(parents=True)
    metadata = _build_job_metadata(job_id, author='Arthur Doyle', title='Mystery Atlas')
    _write_metadata(queue_job_root, metadata)
    service.move_to_library(job_id, status_override='finished')

    app = create_app()

    class StubPipelineService:
        def get_job(self, job_id: str, user_id=None, user_role=None):
            return SimpleNamespace(job_id=job_id)

    from modules.library import LibraryService as LibraryOrchestrator

    orchestrator = LibraryOrchestrator(library_root=library_root, file_locator=locator)
    library_sync = orchestrator.sync

    dependencies.get_library_service.cache_clear()
    dependencies.get_library_sync.cache_clear()
    dependencies.get_pipeline_service.cache_clear()
    dependencies.get_file_locator.cache_clear()

    app.dependency_overrides[dependencies.get_library_service] = lambda: orchestrator
    app.dependency_overrides[dependencies.get_library_sync] = lambda: library_sync
    app.dependency_overrides[dependencies.get_pipeline_service] = lambda: StubPipelineService()
    app.dependency_overrides[dependencies.get_file_locator] = lambda: locator
    app.dependency_overrides[dependencies.get_request_user] = lambda: RequestUserContext(
        user_id='tester', user_role='admin'
    )

    with patch('modules.webapi.routes.library_routes.search_generated_media', return_value=[]):
        client = TestClient(app)
        response = client.get('/pipelines/search', params={'query': 'Mystery', 'limit': 5, 'job_id': job_id})

    app.dependency_overrides.clear()
    dependencies.get_library_service.cache_clear()
    dependencies.get_library_sync.cache_clear()
    dependencies.get_pipeline_service.cache_clear()
    dependencies.get_file_locator.cache_clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload['count'] == 1
    result = payload['results'][0]
    assert result['source'] == 'library'
    assert result['job_id'] == job_id
    assert 'Mystery' in result['snippet']
