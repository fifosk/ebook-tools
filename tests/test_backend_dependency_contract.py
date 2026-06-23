from __future__ import annotations

from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"


def test_backend_pins_torch_below_cuda_heavy_linux_aarch64_releases() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]

    assert "camel-tools>=1.5,<2" in dependencies
    assert "torch>=2.0,<2.11" in dependencies
