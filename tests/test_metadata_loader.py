from __future__ import annotations

import json
from pathlib import Path

from modules.metadata_manager import MetadataLoader


def _write_manifest(job_root: Path, payload: dict) -> None:
    metadata_dir = job_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / "job.json").write_text(json.dumps(payload), encoding="utf-8")


def test_metadata_loader_reads_chunk_files(tmp_path: Path) -> None:
    job_root = tmp_path / "job-new"
    metadata_dir = job_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    chunk_payload = {
        "version": 1,
        "chunk_id": "chunk-001",
        "range_fragment": "0001-0010",
        "start_sentence": 1,
        "end_sentence": 3,
        "sentence_count": 1,
        "sentences": [
            {
                "sentence_number": 1,
                "original": {"text": "Hello", "tokens": ["Hello"]},
                "timeline": [],
                "counts": {"original": 1},
            }
        ],
    }

    chunk_file = metadata_dir / "chunk_0000.json"
    chunk_file.write_text(json.dumps(chunk_payload), encoding="utf-8")

    manifest = {
        "job_id": "job-new",
        "generated_files": {
            "chunks": [
                {
                    "chunk_id": "chunk-001",
                    "metadata_path": "metadata/chunk_0000.json",
                    "metadata_url": "https://example.invalid/jobs/job-new/metadata/chunk_0000.json",
                    "sentence_count": 1,
                    "files": [],
                }
            ],
            "files": [],
        },
    }

    _write_manifest(job_root, manifest)

    loader = MetadataLoader(job_root)

    chunk_manifest = loader.build_chunk_manifest()
    assert chunk_manifest["chunk_count"] == 1

    summaries = loader.load_chunks(include_sentences=False)
    assert summaries[0]["sentence_count"] == 1
    assert "sentences" not in summaries[0]

    detailed = loader.load_chunks(include_sentences=True)
    assert detailed[0]["sentences"][0]["original"]["text"] == "Hello"


def test_metadata_loader_handles_legacy_sentences(tmp_path: Path) -> None:
    job_root = tmp_path / "job-legacy"
    manifest = {
        "job_id": "job-legacy",
        "generated_files": {
            "chunks": [
                {
                    "chunk_id": "chunk-legacy",
                    "sentences": [
                        {
                            "sentence_number": 99,
                            "original": {"text": "Legacy", "tokens": ["Legacy"]},
                            "timeline": [],
                        }
                    ],
                    "files": [],
                }
            ],
        },
    }

    _write_manifest(job_root, manifest)

    loader = MetadataLoader(job_root)

    summaries = loader.load_chunks(include_sentences=False)
    assert summaries[0]["sentence_count"] == 1

    detailed = loader.load_chunks(include_sentences=True)
    sentences = detailed[0]["sentences"]
    assert sentences and sentences[0]["original"]["text"] == "Legacy"
