from __future__ import annotations

from pathlib import Path

from modules.library.sqlite_indexer import LibraryIndexer, LibraryItem


def make_item(job_id: str, library_path: Path, **overrides) -> LibraryItem:
    payload = {
        'id': job_id,
        'author': overrides.get('author', 'Author Name'),
        'book_title': overrides.get('book_title', 'Book Title'),
        'genre': overrides.get('genre', 'Genre'),
        'language': overrides.get('language', 'en'),
        'status': overrides.get('status', 'finished'),
        'created_at': overrides.get('created_at', '2024-01-01T00:00:00+00:00'),
        'updated_at': overrides.get('updated_at', '2024-01-02T00:00:00+00:00'),
        'library_path': str(library_path),
        'cover_path': overrides.get('cover_path'),
        'isbn': overrides.get('isbn'),
        'source_path': overrides.get('source_path'),
        'meta_json': overrides.get('meta_json', '{}')
    }
    return LibraryItem(**payload)


def test_indexer_upsert_and_search(tmp_path):
    library_root = tmp_path / 'library'
    indexer = LibraryIndexer(library_root)

    item = make_item('job-1', library_root / 'Author' / 'Book' / 'en' / 'job-1', author='Jane Doe')
    indexer.upsert(item)

    results = indexer.search(query=None, filters={}, limit=10, offset=0)
    assert len(results) == 1
    assert results[0].id == 'job-1'

    count = indexer.count(query=None, filters={})
    assert count == 1

    # Update existing record
    updated = make_item(
        'job-1',
        library_root / 'Author' / 'Book' / 'en' / 'job-1',
        updated_at='2024-01-03T00:00:00+00:00',
        meta_json='{"updated_at": "2024-01-03T00:00:00+00:00"}'
    )
    indexer.upsert(updated)
    stored = indexer.get('job-1')
    assert stored is not None
    assert stored.updated_at == '2024-01-03T00:00:00+00:00'


def test_indexer_fts_search(tmp_path):
    library_root = tmp_path / 'library'
    indexer = LibraryIndexer(library_root)

    indexer.upsert(
        make_item('job-100', library_root / 'Ray' / 'SciFi' / 'en' / 'job-100', author='Ray Bradbury', book_title='Fahrenheit 451', genre='Dystopian')
    )
    indexer.upsert(
        make_item('job-101', library_root / 'Frank' / 'SciFi' / 'en' / 'job-101', author='Frank Herbert', book_title='Dune', genre='Science Fiction')
    )

    results = indexer.search(query='Dun', filters={}, limit=10, offset=0)
    assert len(results) == 1
    assert results[0].book_title == 'Dune'

    filtered = indexer.search(query=None, filters={'genre': 'Dystopian'}, limit=10, offset=0)
    assert len(filtered) == 1
    assert filtered[0].id == 'job-100'
