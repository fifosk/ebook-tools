import asyncio
import sys

import pytest

from modules.config.loader import get_rendering_config
from modules.render.parallel import RenderManifest, RenderingConcurrency, dispatch_render_manifest
from modules.render.text_pipeline import batch_text_chapters, build_text_tasks

pytestmark = pytest.mark.render


def test_batching_uses_concurrency_limit() -> None:
    chapters = [f"chapter-{i}" for i in range(7)]
    batches = batch_text_chapters(chapters, concurrency=3)
    assert len(batches) == 3
    assert batches[0] == ["chapter-0", "chapter-1", "chapter-2"]
    assert sum(len(batch) for batch in batches) == len(chapters)


def test_batching_rejects_invalid_limit() -> None:
    try:
        batch_text_chapters(["chapter-1"], concurrency=0)
    except ValueError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ValueError for non-positive concurrency")


def test_build_text_tasks_respects_configured_concurrency() -> None:
    config = get_rendering_config()
    chapters = [f"chapter-{i}" for i in range(5)]
    tasks = build_text_tasks(chapters)
    expected_batches = batch_text_chapters(chapters, concurrency=config.text_concurrency)
    assert len(tasks) == len(expected_batches)


@pytest.mark.skipif(sys.version_info < (3, 11), reason="asyncio.TaskGroup requires Python 3.11+")
def test_build_text_tasks_execution() -> None:
    async def run_test():
        concurrency = RenderingConcurrency(video=1, audio=1, text=2)
        chapters = ["alpha", "beta", "gamma", "delta"]

        async def factory(batch: list[str]):
            await asyncio.sleep(0)
            return [value.upper() for value in batch]

        tasks = build_text_tasks(
            chapters,
            concurrency=concurrency,
            task_factory=factory,
        )
        manifest = RenderManifest(tasks)
        results = await dispatch_render_manifest(manifest, concurrency=concurrency)
        return results

    results = asyncio.run(run_test())
    assert results == [["ALPHA", "BETA"], ["GAMMA", "DELTA"]]
