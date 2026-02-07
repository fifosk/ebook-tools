"""Helper utilities for running external commands consistently."""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, MutableMapping, Sequence

from modules import logging_manager as log_mgr

from .exceptions import CommandExecutionError

logger = log_mgr.logger


@dataclass(slots=True)
class CommandResult:
    """Container describing a completed command execution."""

    command: tuple[str, ...]
    returncode: int
    stdout: str | bytes | None
    stderr: str | bytes | None
    duration: float


def _prepare_environment(env: Mapping[str, str] | None) -> Mapping[str, str]:
    if not env:
        return os.environ.copy()
    merged: MutableMapping[str, str] = os.environ.copy()
    merged.update({str(key): str(value) for key, value in env.items()})
    return merged


def _coerce_command(command: Sequence[str] | str) -> tuple[str, ...]:
    if isinstance(command, (str, bytes)):
        return (str(command),)
    return tuple(str(part) for part in command)


RetryPredicate = Callable[[CommandResult | None, BaseException | None], bool]


def run_command(
    command: Sequence[str] | str,
    *,
    timeout: float | None = None,
    env: Mapping[str, str] | None = None,
    retries: int = 0,
    retry_check: RetryPredicate | None = None,
    cwd: str | None = None,
    capture_output: bool = True,
    text: bool = True,
    check: bool = True,
    logger_obj=logger,
    **kwargs: Any,
) -> CommandResult:
    """Execute ``command`` and return a :class:`CommandResult`.

    Parameters mirror :func:`subprocess.run`, but the function standardises logging,
    retries and error handling. ``retry_check`` can be supplied to control whether
    a failed attempt should be retried; by default non-zero exit codes and raised
    exceptions are retried until ``retries`` is exhausted.
    """

    attempts = max(0, int(retries)) + 1
    env_vars = _prepare_environment(env)
    coerced_command = _coerce_command(command)

    run_kwargs: dict[str, Any] = dict(kwargs)
    run_kwargs.setdefault("cwd", cwd)
    run_kwargs.setdefault("timeout", timeout)
    run_kwargs.setdefault("env", env_vars)
    run_kwargs.setdefault("check", False)

    if capture_output:
        run_kwargs.setdefault("stdout", subprocess.PIPE)
        run_kwargs.setdefault("stderr", subprocess.PIPE)
        run_kwargs.setdefault("text", bool(text))
    else:
        if "text" not in run_kwargs:
            run_kwargs["text"] = bool(text)

    last_exception: BaseException | None = None

    for attempt in range(1, attempts + 1):
        start = time.monotonic()
        if logger_obj:
            logger_obj.debug(
                "Executing command (attempt %s/%s)",
                attempt,
                attempts,
                extra={"event": "media.command.execute", "command": coerced_command},
            )
        try:
            completed = subprocess.run(command, **run_kwargs)
            duration = time.monotonic() - start
            result = CommandResult(
                command=coerced_command,
                returncode=completed.returncode,
                stdout=getattr(completed, "stdout", None),
                stderr=getattr(completed, "stderr", None),
                duration=duration,
            )

            if check and completed.returncode != 0:
                error = CommandExecutionError(
                    command,
                    returncode=completed.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                )
                last_exception = error
                should_retry = attempt < attempts and (
                    retry_check(result, error) if retry_check else True
                )
                if logger_obj:
                    logger_obj.warning(
                        "Command returned non-zero status %s",
                        completed.returncode,
                        extra={
                            "event": "media.command.failed",
                            "command": coerced_command,
                            "attempt": attempt,
                            "returncode": completed.returncode,
                        },
                    )
                if should_retry:
                    continue
                raise error

            if logger_obj:
                logger_obj.debug(
                    "Command completed successfully in %.3fs",
                    duration,
                    extra={
                        "event": "media.command.success",
                        "command": coerced_command,
                        "returncode": completed.returncode,
                    },
                )
            return result
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - start
            result = CommandResult(
                command=coerced_command,
                returncode=-1,
                stdout=exc.stdout,
                stderr=exc.stderr,
                duration=duration,
            )
            error = CommandExecutionError(
                command,
                stdout=exc.stdout,
                stderr=exc.stderr,
                cause=exc,
                timeout=True,
            )
            last_exception = error
            if logger_obj:
                logger_obj.warning(
                    "Command timed out after %.3fs",
                    duration,
                    extra={
                        "event": "media.command.timeout",
                        "command": coerced_command,
                    },
                )
            should_retry = attempt < attempts and (
                retry_check(result, error) if retry_check else True
            )
            if should_retry:
                continue
            raise error from exc
        except FileNotFoundError as exc:
            duration = time.monotonic() - start
            error = CommandExecutionError(command, cause=exc)
            last_exception = error
            if logger_obj:
                logger_obj.error(
                    "Command executable not found",
                    extra={
                        "event": "media.command.not_found",
                        "command": coerced_command,
                    },
                )
            should_retry = attempt < attempts and (
                retry_check(None, error) if retry_check else False
            )
            if should_retry:
                continue
            raise last_exception from exc
        except CommandExecutionError:
            raise
        except OSError as exc:  # pragma: no cover - defensive (e.g. permission errors)
            duration = time.monotonic() - start
            error = CommandExecutionError(command, cause=exc)
            last_exception = error
            if logger_obj:
                logger_obj.error(
                    "Command execution failed due to OS error",
                    extra={
                        "event": "media.command.os_error",
                        "command": coerced_command,
                    },
                )
            should_retry = attempt < attempts and (
                retry_check(None, error) if retry_check else False
            )
            if should_retry:
                continue
            raise last_exception from exc
        except Exception as exc:  # pragma: no cover - unexpected failures
            duration = time.monotonic() - start
            error = CommandExecutionError(command, cause=exc)
            last_exception = error
            if logger_obj:
                logger_obj.error(
                    "Unexpected error running command",
                    extra={
                        "event": "media.command.error",
                        "command": coerced_command,
                    },
                )
            should_retry = attempt < attempts and (
                retry_check(None, error) if retry_check else False
            )
            if should_retry:
                continue
            raise last_exception from exc

    assert last_exception is not None  # pragma: no cover - logically unreachable
    raise last_exception


__all__ = ["CommandResult", "run_command"]
