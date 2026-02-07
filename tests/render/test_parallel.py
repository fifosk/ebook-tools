import asyncio
import sys
import time

import pytest

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="asyncio.TaskGroup requires Python 3.11+",
)

from modules.render.parallel import (
    RenderManifest,
    RenderTask,
    RenderingConcurrency,
    dispatch_render_manifest,
)


def test_mixed_media_concurrency() -> None:
    async def run_test():
        nonlocal start
        manifest = RenderManifest()
        concurrency = RenderingConcurrency(video=1, audio=3, text=2)
        counters_lock = asyncio.Lock()
        active_counts = {"video": 0, "audio": 0, "text": 0}
        peak_counts = {"video": 0, "audio": 0, "text": 0}
        completions: list[tuple[str, float, str]] = []
        expected_labels: list[str] = []
        order = 0

        def register(media: str, delay: float, repeat: int = 1) -> None:
            nonlocal order
            for _ in range(repeat):
                label = f"{media}-{order}"

                async def action(label=label, media=media, delay=delay):
                    async with counters_lock:
                        active_counts[media] += 1
                        peak_counts[media] = max(
                            peak_counts[media], active_counts[media]
                        )
                    await asyncio.sleep(delay)
                    elapsed = time.perf_counter() - start
                    async with counters_lock:
                        active_counts[media] -= 1
                        completions.append((media, elapsed, label))
                    return label

                manifest.add_task(
                    RenderTask(order=order, media_type=media, action=action, label=label)
                )
                expected_labels.append(label)
                order += 1

        register("video", 0.2, repeat=2)
        register("text", 0.01, repeat=4)
        register("audio", 0.05, repeat=4)

        # Update the shared start time used inside the action closures.
        start = time.perf_counter()

        results = await dispatch_render_manifest(manifest, concurrency=concurrency)
        return results, completions, peak_counts, expected_labels

    start = 0.0
    results, completions, peak_counts, expected = asyncio.run(run_test())

    assert results == expected

    video_finish = [elapsed for media, elapsed, _ in completions if media == "video"]
    fast_finish = [elapsed for media, elapsed, _ in completions if media != "video"]
    assert fast_finish
    assert video_finish
    assert min(fast_finish) < min(video_finish)

    assert peak_counts["video"] <= 1
    assert peak_counts["audio"] <= 3
    assert peak_counts["text"] <= 2
