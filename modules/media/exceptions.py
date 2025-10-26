"""Exception hierarchy for media backends and command execution."""

from __future__ import annotations

from typing import Iterable, Sequence


class MediaBackendError(RuntimeError):
    """Base exception raised by media-related backends."""


class CommandExecutionError(MediaBackendError):
    """Raised when an external command fails to execute successfully."""

    def __init__(
        self,
        command: Sequence[str] | str,
        *,
        returncode: int | None = None,
        stdout: str | bytes | None = None,
        stderr: str | bytes | None = None,
        cause: BaseException | None = None,
        timeout: bool = False,
    ) -> None:
        if isinstance(command, (str, bytes)):
            coerced: Sequence[str] = (str(command),)
        elif isinstance(command, Iterable):
            coerced = tuple(str(part) for part in command)
        else:
            coerced = (str(command),)

        self.command = coerced
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.cause = cause
        self.timeout = timeout

        detail = []
        if returncode is not None:
            detail.append(f"return code {returncode}")
        if timeout:
            detail.append("timeout")
        if cause and not timeout:
            detail.append(cause.__class__.__name__)
        detail_str = f" ({', '.join(detail)})" if detail else ""
        message = f"Command execution failed{detail_str}: {command}"
        super().__init__(message)


__all__ = ["MediaBackendError", "CommandExecutionError"]
