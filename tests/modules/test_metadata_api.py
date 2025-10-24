import contextlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules import config_manager as cfg
from modules import metadata_manager
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_runtime_context_provider


class StubRuntimeContext:
    def __init__(self, books_dir: Path) -> None:
        self.books_dir = books_dir


class StubRuntimeContextProvider:
    def __init__(self, context: StubRuntimeContext) -> None:
        self._context = context

    @contextlib.contextmanager
    def activation(self, _config: dict, _overrides: dict | None = None):
        cfg.set_runtime_context(self._context)
        try:
            yield self._context
        finally:
            cfg.clear_runtime_context()


@pytest.fixture()
def api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    books_dir = tmp_path / 'books'
    books_dir.mkdir(parents=True, exist_ok=True)
    context = StubRuntimeContext(books_dir)
    provider = StubRuntimeContextProvider(context)

    app = create_app()
    app.dependency_overrides[get_runtime_context_provider] = lambda: provider

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_metadata_lookup_returns_inferred_values(api_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    books_dir = tmp_path / 'books'
    books_dir.mkdir(parents=True, exist_ok=True)
    epub_path = books_dir / 'sample.epub'
    epub_path.write_bytes(b'placeholder epub')

    captured = {}

    def _fake_infer(input_file: str, *, existing_metadata: dict | None = None, force_refresh: bool = False):
        captured['input_file'] = input_file
        captured['existing_metadata'] = existing_metadata or {}
        captured['force_refresh'] = force_refresh
        return {'book_title': 'Stub Title', 'book_author': 'Stub Author'}

    monkeypatch.setattr(metadata_manager, 'infer_metadata', _fake_infer)

    response = api_client.post(
        '/pipelines/files/metadata',
        json={'input_file': 'sample.epub', 'existing_metadata': {'book_title': 'Initial'}}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['metadata'] == {
        'book_title': 'Stub Title',
        'book_author': 'Stub Author'
    }
    assert captured['input_file'] == 'sample.epub'
    assert captured['existing_metadata'] == {'book_title': 'Initial'}
    assert captured['force_refresh'] is False


def test_metadata_lookup_returns_404_for_missing_file(api_client: TestClient) -> None:
    response = api_client.post('/pipelines/files/metadata', json={'input_file': 'missing.epub'})
    assert response.status_code == 404
