"""Private, validated translation checkpoints; never a cross-job response cache."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from modules import config_manager as cfg

# Changes to validation/normalization invalidate previously accepted responses.
_VALIDATOR_VERSION = hashlib.sha256(b"".join(
    (Path(__file__).parent / name).read_bytes()
    for name in ("translation_validation.py", "translation_batch.py", "translation_engine.py",
                 "text_normalization.py", "language_policies.py", "prompt_templates.py")
)).hexdigest()


def checkpoint_path(client: Any, request: Any, *, kind: str) -> Path | None:
    """Key the complete request (including prompts/context), without storing keys.

    Managed jobs use <job>/media as output_dir. Their data directory survives
    pause/restart cleanup and is deleted with the job. CLI/unscoped calls do not
    persist responses. No legacy output or other user's job is ever imported.
    """
    context = cfg.get_runtime_context(None)
    output = getattr(context, "output_dir", None)
    if not isinstance(output, (str, Path)) or os.environ.get("EBOOK_TRANSLATION_CHECKPOINTS", "1") == "0":
        return None
    output = Path(output)
    if output.name != "media" or not (output.parent / "data").is_dir():
        return None
    settings = getattr(client, "settings", None)
    # Endpoint fallback is not a model identity. Do not reuse a result unless
    # its provider is fixed; account failover inside the pool keeps it fixed.
    if (getattr(settings, "fallback_sources", ())
            or (client.llm_source == "local" and getattr(settings, "allow_fallback", False))):
        return None
    identity = {
        "version": 1, "validator": _VALIDATOR_VERSION, "kind": kind,
        "model": client.model, "source": client.llm_source,
        "endpoint": getattr(client, "api_url", None), "request": request,
    }
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return output.parent / "data" / "translation_checkpoints" / f"{digest}.json"


def read_checkpoint(path: Path | None) -> Any:
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_checkpoint(path: Path | None, value: Any) -> None:
    """Best-effort atomic writes: an interrupted write must be a cache miss."""
    if path is None:
        return
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".checkpoint-", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        pass  # Storage pressure must not discard an otherwise valid translation.
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
