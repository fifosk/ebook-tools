"""Lightweight in-process API client used for integration tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from uuid import uuid4
import zipfile


@dataclass
class _JobRecord:
    job_id: str
    state: str
    output_dir: Path
    error: Optional[str] = None

    def to_status(self) -> Dict[str, str]:
        payload = {"job_id": self.job_id, "state": self.state}
        if self.error:
            payload["error"] = self.error
        return payload


class EbookToolsClient:
    """Simple client that simulates the ebook-tools job API locally."""

    def __init__(self, *, output_dir: str | Path = "output/ebook") -> None:
        self._output_root = Path(output_dir).expanduser().resolve()
        self._output_root.mkdir(parents=True, exist_ok=True)
        self._jobs: Dict[str, _JobRecord] = {}

    def create_job(self, epub_path: str | Path, job_params: Optional[Dict[str, object]] = None) -> str:
        """Create a new job by synthesising expected pipeline artifacts."""

        job_id = uuid4().hex
        job_dir = self._output_root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        sentences = self._extract_sentences(epub_path)
        self._write_html(job_dir / "output.html", sentences)
        self._write_placeholder(job_dir / "output.mp3", header=b"ID3\x03\x00\x00\x00\x00\x00\x21")
        self._write_placeholder(job_dir / "output.mp4", header=b"\x00\x00\x00\x18ftypisom")

        record = _JobRecord(job_id=job_id, state="completed", output_dir=job_dir)
        self._jobs[job_id] = record
        return job_id

    def get_job_status(self, job_id: str) -> Dict[str, str]:
        """Return the current status for ``job_id``."""

        try:
            record = self._jobs[job_id]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise KeyError(f"Unknown job_id: {job_id}") from exc
        return record.to_status()

    def _extract_sentences(self, epub_path: str | Path) -> List[str]:
        path = Path(epub_path)
        if not path.is_file():
            raise FileNotFoundError(path)

        with zipfile.ZipFile(path, "r") as zf:
            if "OEBPS/sentences.json" in zf.namelist():
                payload = json.loads(zf.read("OEBPS/sentences.json").decode("utf-8"))
                data = payload.get("sentences", [])
                sentences = [str(item) for item in data if str(item).strip()]
                if sentences:
                    return sentences

            sentences: List[str] = []
            for name in zf.namelist():
                if name.lower().endswith(('.xhtml', '.html', '.htm')):
                    try:
                        content = zf.read(name).decode("utf-8")
                    except UnicodeDecodeError:
                        continue
                    sentences.extend(self._extract_from_markup(content))
        if not sentences:
            raise ValueError("Unable to extract sentences from EPUB")
        return sentences

    @staticmethod
    def _extract_from_markup(content: str) -> List[str]:
        import re

        text = re.sub(r"<[^>]+>", " ", content)
        chunks = [chunk.strip() for chunk in text.splitlines() if chunk.strip()]
        sentences: List[str] = []
        for chunk in chunks:
            for part in re.split(r"(?<=[.!?])\s+", chunk):
                if part:
                    sentences.append(part)
        return sentences

    @staticmethod
    def _write_html(target: Path, sentences: Iterable[str]) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        body = "\n".join(f"    <p>{sentence}</p>" for sentence in sentences)
        html = (
            "<!DOCTYPE html>\n"
            "<html lang=\"en\">\n"
            "  <head>\n"
            "    <meta charset=\"utf-8\">\n"
            "    <title>Processed EPUB</title>\n"
            "  </head>\n"
            "  <body>\n"
            f"{body}\n"
            "  </body>\n"
            "</html>\n"
        )
        target.write_text(html, encoding="utf-8")

    @staticmethod
    def _write_placeholder(target: Path, *, header: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = header + b"Synthetic media placeholder generated for tests.\n"
        target.write_bytes(payload)
