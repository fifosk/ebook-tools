"""Unit tests for translation_workers module."""

import asyncio
from unittest.mock import patch

from modules import translation_workers as tw

import pytest

pytestmark = pytest.mark.translation


class TestThreadWorkerPool:
    def test_initialization_default_workers(self):
        with patch('modules.translation_workers.cfg.get_thread_count', return_value=4):
            with patch('modules.observability.worker_pool_event') as mock_event:
                pool = tw.ThreadWorkerPool()

                assert pool.max_workers == 4
                assert pool.mode == "thread"
                assert pool._executor is None
                assert pool._shutdown is False
                mock_event.assert_called_once_with(
                    "created", mode="thread", max_workers=4
                )

    def test_initialization_custom_workers(self):
        with patch('modules.observability.worker_pool_event'):
            pool = tw.ThreadWorkerPool(max_workers=8)

            assert pool.max_workers == 8

    def test_initialization_zero_workers_uses_minimum(self):
        with patch('modules.translation_workers.cfg.get_thread_count', return_value=5):
            with patch('modules.observability.worker_pool_event'):
                pool = tw.ThreadWorkerPool(max_workers=0)

                # max(1, 0 or cfg.get_thread_count()) = max(1, 5) = 5
                assert pool.max_workers == 5

    def test_ensure_executor_creates_on_first_call(self):
        with patch('modules.observability.worker_pool_event'):
            pool = tw.ThreadWorkerPool(max_workers=2)

            assert pool._executor is None
            executor = pool._ensure_executor()

            assert executor is not None
            assert pool._executor is executor
            assert isinstance(executor, type(pool._executor))

    def test_ensure_executor_returns_same_instance(self):
        with patch('modules.observability.worker_pool_event'):
            pool = tw.ThreadWorkerPool(max_workers=2)

            executor1 = pool._ensure_executor()
            executor2 = pool._ensure_executor()

            assert executor1 is executor2

    def test_submit_task(self):
        with patch('modules.observability.worker_pool_event'):
            with patch('modules.observability.record_metric') as mock_metric:
                pool = tw.ThreadWorkerPool(max_workers=2)

                def simple_task(x):
                    return x * 2

                future = pool.submit(simple_task, 5)
                result = future.result(timeout=1)

                assert result == 10
                mock_metric.assert_called_once()

    def test_iter_completed(self):
        with patch('modules.observability.worker_pool_event'):
            with patch('modules.observability.record_metric'):
                pool = tw.ThreadWorkerPool(max_workers=2)

                futures = [
                    pool.submit(lambda x: x * 2, i)
                    for i in range(3)
                ]

                results = []
                for future in pool.iter_completed(futures):
                    results.append(future.result())

                assert sorted(results) == [0, 2, 4]

    def test_shutdown(self):
        with patch('modules.observability.worker_pool_event') as mock_event:
            pool = tw.ThreadWorkerPool(max_workers=2)
            pool._ensure_executor()

            mock_event.reset_mock()
            pool.shutdown()

            assert pool._shutdown is True
            mock_event.assert_called_once_with(
                "shutdown", mode="thread", max_workers=2
            )

    def test_shutdown_idempotent(self):
        with patch('modules.observability.worker_pool_event') as mock_event:
            pool = tw.ThreadWorkerPool(max_workers=2)
            pool._ensure_executor()

            pool.shutdown()
            mock_event.reset_mock()
            pool.shutdown()  # Second call

            # Should not emit event again
            mock_event.assert_not_called()

    def test_context_manager(self):
        with patch('modules.observability.worker_pool_event'):
            with patch('modules.observability.record_metric'):
                with tw.ThreadWorkerPool(max_workers=2) as pool:
                    future = pool.submit(lambda: 42)
                    result = future.result()
                    assert result == 42

                # Pool should be shut down after exiting context
                assert pool._shutdown is True


class TestAsyncWorkerPool:
    def test_initialization_default_workers(self):
        with patch('modules.translation_workers.cfg.get_thread_count', return_value=4):
            with patch('modules.observability.worker_pool_event') as mock_event:
                loop = asyncio.new_event_loop()
                pool = tw.AsyncWorkerPool(loop=loop)

                assert pool.max_workers == 4
                assert pool.mode == "async"
                assert pool.loop is loop
                assert pool._shutdown is False
                mock_event.assert_called_once_with(
                    "created", mode="async", max_workers=4
                )
                loop.close()

    def test_initialization_custom_workers(self):
        with patch('modules.observability.worker_pool_event'):
            loop = asyncio.new_event_loop()
            pool = tw.AsyncWorkerPool(max_workers=8, loop=loop)

            assert pool.max_workers == 8
            loop.close()

    def test_initialization_zero_workers_uses_minimum(self):
        with patch('modules.translation_workers.cfg.get_thread_count', return_value=5):
            with patch('modules.observability.worker_pool_event'):
                loop = asyncio.new_event_loop()
                pool = tw.AsyncWorkerPool(max_workers=0, loop=loop)

                # max(1, 0 or cfg.get_thread_count()) = max(1, 5) = 5
                assert pool.max_workers == 5
                loop.close()

    def test_loop_property(self):
        with patch('modules.observability.worker_pool_event'):
            loop = asyncio.new_event_loop()
            pool = tw.AsyncWorkerPool(loop=loop)

            assert pool.loop is loop
            loop.close()

    def test_submit_sync_function(self):
        with patch('modules.observability.worker_pool_event'):
            with patch('modules.observability.record_metric'):
                loop = asyncio.new_event_loop()
                pool = tw.AsyncWorkerPool(loop=loop)

                def sync_task(x):
                    return x * 2

                future = pool.submit(sync_task, 5)
                result = loop.run_until_complete(future)

                assert result == 10
                loop.close()

    def test_submit_async_function(self):
        with patch('modules.observability.worker_pool_event'):
            with patch('modules.observability.record_metric'):
                loop = asyncio.new_event_loop()
                pool = tw.AsyncWorkerPool(loop=loop)

                async def async_task(x):
                    await asyncio.sleep(0.01)
                    return x * 3

                future = pool.submit(async_task, 5)
                result = loop.run_until_complete(future)

                assert result == 15
                loop.close()

    def test_iter_completed(self):
        with patch('modules.observability.worker_pool_event'):
            with patch('modules.observability.record_metric'):
                loop = asyncio.new_event_loop()
                pool = tw.AsyncWorkerPool(loop=loop)

                async def async_task(x):
                    await asyncio.sleep(0.01)
                    return x * 2

                futures = [
                    pool.submit(async_task, i)
                    for i in range(3)
                ]

                async def collect_results():
                    results = []
                    async for result in pool.iter_completed(futures):
                        results.append(result)
                    return results

                results = loop.run_until_complete(collect_results())
                assert sorted(results) == [0, 2, 4]
                loop.close()

    def test_shutdown(self):
        with patch('modules.observability.worker_pool_event') as mock_event:
            loop = asyncio.new_event_loop()
            pool = tw.AsyncWorkerPool(loop=loop)

            mock_event.reset_mock()
            pool.shutdown()

            assert pool._shutdown is True
            mock_event.assert_called_once_with(
                "shutdown", mode="async", max_workers=pool.max_workers
            )
            loop.close()

    def test_shutdown_idempotent(self):
        with patch('modules.observability.worker_pool_event') as mock_event:
            loop = asyncio.new_event_loop()
            pool = tw.AsyncWorkerPool(loop=loop)

            pool.shutdown()
            mock_event.reset_mock()
            pool.shutdown()  # Second call

            # Should not emit event again
            mock_event.assert_not_called()
            loop.close()

    def test_context_manager(self):
        with patch('modules.observability.worker_pool_event'):
            with patch('modules.observability.record_metric'):
                loop = asyncio.new_event_loop()

                with tw.AsyncWorkerPool(loop=loop) as pool:
                    def task():
                        return 42

                    future = pool.submit(task)
                    result = loop.run_until_complete(future)
                    assert result == 42

                # Pool should be shut down after exiting context
                assert pool._shutdown is True
                loop.close()
