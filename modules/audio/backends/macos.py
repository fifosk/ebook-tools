"""macOS ``say`` command backend."""

from __future__ import annotations

import os
import tempfile
from typing import Optional

from pydub import AudioSegment

from modules import config_manager as cfg
from modules.media.command_runner import run_command
from modules.media.exceptions import CommandExecutionError

from .base import BaseTTSBackend, TTSBackendError


class MacOSTTSBackend(BaseTTSBackend):
    """Backend using the macOS ``say`` command line utility."""

    name = "macos_say"

    def __init__(self, *, executable_path: Optional[str] = None) -> None:
        super().__init__(executable_path=executable_path)

    def _resolve_executable(self) -> str:
        if self.executable_path:
            return self.executable_path
        return "say"

    def synthesize(
        self,
        *,
        text: str,
        voice: str,
        speed: int,
        lang_code: str,
        output_path: Optional[str] = None,
    ) -> AudioSegment:
        tmp_file: Optional[str] = None
        destination = output_path

        if destination is None:
            runtime = cfg.get_runtime_context(None)
            tmp_dir = str(runtime.tmp_dir) if runtime is not None else None
            handle = tempfile.NamedTemporaryFile(
                suffix=".aiff", delete=False, dir=tmp_dir
            )
            tmp_file = handle.name
            handle.close()
            destination = tmp_file

        cmd = [
            self._resolve_executable(),
            "-v",
            voice,
            "-r",
            str(speed),
            "-o",
            destination,
            text,
        ]

        try:
            run_command(cmd)
        except CommandExecutionError as exc:
            raise TTSBackendError("macOS TTS synthesis failed") from exc

        try:
            return AudioSegment.from_file(destination, format="aiff")
        finally:
            if tmp_file and os.path.exists(tmp_file):
                os.remove(tmp_file)


__all__ = ["MacOSTTSBackend"]

