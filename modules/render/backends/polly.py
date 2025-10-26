"""Amazon Polly-based implementation of :class:`AudioSynthesizer`."""
from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Mapping, Optional, TYPE_CHECKING

from pydub import AudioSegment

from modules import config_manager as cfg
from modules import logging_manager as log_mgr, observability
from modules.audio.backends import get_default_backend_name
from modules.audio.highlight import _compute_audio_highlight_metadata, _store_audio_metadata
from modules.audio.tts import generate_audio
from modules.core.translation import split_translation_and_transliteration

from .base import AudioSynthesizer

logger = log_mgr.logger

_DEFAULT_TTS_BACKEND = get_default_backend_name()

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from modules.integrations.audio_client import AudioAPIClient
else:  # pragma: no cover - runtime fallback when integrations are unavailable
    AudioAPIClient = Any  # type: ignore[assignment]


class PollyAudioSynthesizer(AudioSynthesizer):
    """Synthesize audio using the configured audio API or legacy helpers."""

    def __init__(
        self,
        *,
        audio_client: AudioAPIClient | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        poll_interval: float | None = None,
    ) -> None:
        self._client = audio_client
        self._client_base_url = base_url
        self._client_timeout = timeout
        self._client_poll_interval = poll_interval

    def _resolve_client(self) -> AudioAPIClient | None:
        if self._client is not None:
            return self._client
        base_url = self._client_base_url or os.environ.get("EBOOK_AUDIO_API_BASE_URL")
        if not base_url:
            return None
        timeout = self._client_timeout if self._client_timeout is not None else 60.0
        timeout_override = os.environ.get("EBOOK_AUDIO_API_TIMEOUT_SECONDS")
        if timeout_override:
            try:
                timeout = float(timeout_override)
            except (TypeError, ValueError):  # pragma: no cover - defensive log
                logger.warning(
                    "Ignoring invalid EBOOK_AUDIO_API_TIMEOUT_SECONDS value: %r",
                    timeout_override,
                    extra={"event": "audio.api.invalid_timeout"},
                )
        try:
            from modules.integrations.audio_client import AudioAPIClient as RuntimeAudioClient
        except ImportError as exc:  # pragma: no cover - optional dependency safeguard
            logger.warning(
                "Audio API client dependencies missing; using legacy synthesizer.",
                extra={"event": "audio.api.client_unavailable"},
                exc_info=exc,
            )
            return None
        self._client = RuntimeAudioClient(base_url, timeout=timeout)
        self._client_timeout = timeout
        return self._client

    def synthesize_sentence(
        self,
        sentence_number: int,
        input_sentence: str,
        fluent_translation: str,
        input_language: str,
        target_language: str,
        audio_mode: str,
        total_sentences: int,
        language_codes: Mapping[str, str],
        selected_voice: str,
        tempo: float,
        macos_reading_speed: int,
        *,
        tts_backend: str = _DEFAULT_TTS_BACKEND,
        tts_executable_path: Optional[str] = None,
    ) -> AudioSegment:
        def _lang_code(lang: str) -> str:
            return language_codes.get(lang, "en")

        silence = AudioSegment.silent(duration=100)

        translation_audio_text, _ = split_translation_and_transliteration(fluent_translation)
        translation_audio_text = (translation_audio_text or fluent_translation).strip()

        tasks = []
        segment_texts: Dict[str, str] = {}

        def enqueue(key: str, text: str, lang_code: str) -> None:
            tasks.append((key, text, lang_code))
            segment_texts[key] = text

        target_lang_code = _lang_code(target_language)
        source_lang_code = _lang_code(input_language)

        numbering_str = f"{sentence_number} - {(sentence_number / total_sentences * 100):.2f}%"

        if audio_mode == "1":
            enqueue("translation", translation_audio_text, target_lang_code)
            sequence = ["translation"]
        elif audio_mode == "2":
            enqueue("number", numbering_str, "en")
            enqueue("translation", translation_audio_text, target_lang_code)
            sequence = ["number", "translation"]
        elif audio_mode == "3":
            enqueue("number", numbering_str, "en")
            enqueue("input", input_sentence, source_lang_code)
            enqueue("translation", translation_audio_text, target_lang_code)
            sequence = ["number", "input", "translation"]
        elif audio_mode == "4":
            enqueue("input", input_sentence, source_lang_code)
            enqueue("translation", translation_audio_text, target_lang_code)
            sequence = ["input", "translation"]
        elif audio_mode == "5":
            enqueue("input", input_sentence, source_lang_code)
            sequence = ["input"]
        else:
            enqueue("input", input_sentence, source_lang_code)
            enqueue("translation", translation_audio_text, target_lang_code)
            sequence = ["input", "translation"]

        if not tasks:
            return self._change_audio_tempo(AudioSegment.silent(duration=0), tempo)

        worker_count = max(1, min(cfg.get_thread_count(), len(tasks)))
        segments: Dict[str, AudioSegment] = {}

        client = self._resolve_client()

        if client is None:
            backend_config = {
                "tts_backend": tts_backend,
                "tts_executable_path": tts_executable_path,
                "say_path": tts_executable_path,
            }

            if worker_count == 1:
                for key, text, lang_code in tasks:
                    segments[key] = generate_audio(
                        text,
                        lang_code,
                        selected_voice,
                        macos_reading_speed,
                        config=backend_config,
                    )
            else:
                with ThreadPoolExecutor(max_workers=worker_count) as executor:
                    future_map = {
                        executor.submit(
                            generate_audio,
                            text,
                            lang_code,
                            selected_voice,
                            macos_reading_speed,
                            config=backend_config,
                        ): key
                        for key, text, lang_code in tasks
                    }
                    for future in as_completed(future_map):
                        key = future_map[future]
                        try:
                            segments[key] = future.result()
                        except Exception as exc:  # pragma: no cover - defensive
                            logger.error(
                                "Audio synthesis failed for segment '%s': %s", key, exc
                            )
                            segments[key] = AudioSegment.silent(duration=0)
        else:
            def _synth(task: tuple[str, str, str]) -> tuple[str, AudioSegment]:
                key, text, lang_code = task
                attributes = {
                    "segment": key,
                    "language": lang_code,
                    "voice": selected_voice,
                    "has_speed": macos_reading_speed is not None,
                }
                logger.info(
                    "Dispatching audio API synthesis",
                    extra={
                        "event": "audio.api.synthesize.start",
                        "attributes": attributes,
                        "console_suppress": True,
                    },
                )
                start = time.perf_counter()
                try:
                    segment = client.synthesize(
                        text=text,
                        voice=selected_voice or None,
                        speed=macos_reading_speed or None,
                        language=lang_code,
                    )
                except Exception:
                    duration_ms = (time.perf_counter() - start) * 1000.0
                    observability.record_metric(
                        "audio.api.synthesize.duration",
                        duration_ms,
                        {**attributes, "status": "error"},
                    )
                    logger.error(
                        "Audio API synthesis failed",
                        extra={
                            "event": "audio.api.synthesize.error",
                            "attributes": attributes,
                            "console_suppress": True,
                        },
                        exc_info=True,
                    )
                    raise

                duration_ms = (time.perf_counter() - start) * 1000.0
                observability.record_metric(
                    "audio.api.synthesize.duration",
                    duration_ms,
                    {**attributes, "status": "success"},
                )
                logger.info(
                    "Audio API synthesis completed",
                    extra={
                        "event": "audio.api.synthesize.complete",
                        "attributes": {**attributes, "duration_ms": round(duration_ms, 2)},
                        "console_suppress": True,
                    },
                )
                return key, segment

            if worker_count == 1:
                for task in tasks:
                    key, segment = _synth(task)
                    segments[key] = segment
            else:
                with ThreadPoolExecutor(max_workers=worker_count) as executor:
                    future_map = {executor.submit(_synth, task): task[0] for task in tasks}
                    for future in as_completed(future_map):
                        key = future_map[future]
                        try:
                            _, segment = future.result()
                            segments[key] = segment
                        except Exception as exc:  # pragma: no cover - defensive
                            logger.error(
                                "Audio API synthesis failed for segment '%s': %s", key, exc
                            )
                            segments[key] = AudioSegment.silent(duration=0)

        audio = AudioSegment.silent(duration=0)
        for key in sequence:
            audio += segments.get(key, AudioSegment.silent(duration=0)) + silence

        tempo_adjusted = self._change_audio_tempo(audio, tempo)
        try:
            metadata = _compute_audio_highlight_metadata(
                tempo_adjusted, sequence, segments, tempo, segment_texts
            )
            _store_audio_metadata(tempo_adjusted, metadata)
        except Exception:  # pragma: no cover - metadata attachment best effort
            logger.debug("Failed to compute audio metadata for sentence %s", sentence_number)

        return tempo_adjusted

    @staticmethod
    def _change_audio_tempo(sound: AudioSegment, tempo: float = 1.0) -> AudioSegment:
        if tempo == 1.0:
            return sound
        new_frame_rate = int(sound.frame_rate * tempo)
        return sound._spawn(sound.raw_data, overrides={"frame_rate": new_frame_rate}).set_frame_rate(
            sound.frame_rate
        )


__all__ = ["PollyAudioSynthesizer"]
