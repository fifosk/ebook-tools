"""Tests for the backwards-compatibility helpers in :mod:`main`."""

from __future__ import annotations

import warnings

import main


def test_run_pipeline_aliases_main(monkeypatch):
    calls = {}

    def _fake_main(argv):
        calls["argv"] = argv
        return 42

    monkeypatch.setattr(main, "main", _fake_main)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        result = main.run_pipeline(["--help"])

    assert result == 42
    assert calls["argv"] == ["--help"]
    assert any(item.category is DeprecationWarning for item in caught)
