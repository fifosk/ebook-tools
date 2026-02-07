from __future__ import annotations

from pathlib import Path

import sys
import modules.fsutils.atomic_move  # ensure module is importable
atomic_move_module = sys.modules["modules.fsutils.atomic_move"]
from modules.fsutils.atomic_move import atomic_move


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def test_atomic_move_same_filesystem(tmp_path):
    source_dir = tmp_path / 'source'
    source_dir.mkdir()
    write_file(source_dir / 'sample.txt', 'hello world')

    destination_dir = tmp_path / 'destination'

    atomic_move(source_dir, destination_dir)

    assert not source_dir.exists()
    assert destination_dir.exists()
    assert (destination_dir / 'sample.txt').read_text(encoding='utf-8') == 'hello world'


def test_atomic_move_cross_filesystem(monkeypatch, tmp_path):
    source_file = tmp_path / 'source.txt'
    write_file(source_file, 'cross device data')
    destination_file = tmp_path / 'target.txt'

    monkeypatch.setattr(atomic_move_module, '_same_filesystem', lambda _src, _dst: False)

    atomic_move(source_file, destination_file)

    assert not source_file.exists()
    assert destination_file.exists()
    assert destination_file.read_text(encoding='utf-8') == 'cross device data'
