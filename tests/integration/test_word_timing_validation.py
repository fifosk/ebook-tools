import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.order("last")
def test_word_timing_validation_sample() -> None:
    storage_dir = Path("storage")
    if not storage_dir.exists():
        pytest.skip("storage directory not available for timing validation")
    sample_jobs = [path.name for path in storage_dir.iterdir() if path.is_dir() and path.name.startswith("job-")]
    if not sample_jobs:
        pytest.skip("no sample jobs found")

    job_id = sample_jobs[0]
    result = subprocess.run(
        [sys.executable, "scripts/validate_word_timing.py", job_id],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    assert "Timing OK" in output or "✅" in output
