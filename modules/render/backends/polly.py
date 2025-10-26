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
from modules.audio.tts import generate_audio, get_voice_display_name
from modules.media.exceptions import MediaBackendError
from modules.core.translation import split_translation_and_transliteration

from .base import AudioSynthesizer, SynthesisResult

logger = log_mgr.logger

_DEFAULT_TTS_BACKEND = get_default_backend_name()


def _normalize_api_voice(
    selected_voice: Optional[str], *, language: Optional[str] = None, sample_text: Optional[str] = None
) -> Optional[str]:
    """Return a voice identifier that the remote API can understand."""

    if not selected_voice:
        return None

    voice = selected_voice.strip()
    if not voice:
        return None

    lowered = voice.lower()

    def _looks_english() -> bool:
        normalized_lang = (language or "").strip().lower().replace("_", "-")
        has_non_ascii_text = False
        if sample_text:
            for char in sample_text:
                if char.isspace():
                    continue
                if not char.isascii():
                    has_non_ascii_text = True
                    break
        if has_non_ascii_text:
            return False

        if not normalized_lang:
            return bool(sample_text and sample_text.strip() and all(ch.isascii() for ch in sample_text))

        english_aliases = {"en", "english", "en-us", "en-gb", "en-au", "en-ca"}
        if normalized_lang in english_aliases:
            return True
        if normalized_lang.startswith("en-"):
            return True
        return False

    if lowered.startswith("macos-auto"):
        if _looks_english():
            return "0"
        return None
    if lowered == "gtts":
        return None
    return voice


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
        segment_languages: Dict[str, tuple[str, str]] = {}
        voice_map: Dict[str, Dict[str, str]] = {}

        def _language_label(role: str, lang_code: str, explicit: str | None = None) -> str:
            candidate = (explicit or "").strip()
            if candidate:
                return candidate
            if lang_code:
                if len(lang_code) == 2:
                    return lang_code.upper()
                return lang_code
            return "Unknown"

        def _record_voice(key: str, voice_identifier: Optional[str]) -> Optional[str]:
            language_label, lang_code = segment_languages.get(key, ("", ""))
            resolved_voice = (voice_identifier or "").strip()
            if not resolved_voice or resolved_voice == "0":
                resolved_voice = selected_voice
            label = language_label or _language_label(key, lang_code)
            display_name = get_voice_display_name(resolved_voice, label, language_codes)
            if not display_name:
                return None
            if key == "translation":
                role = "translation"
            elif key == "input":
                role = "source"
            else:
                role = key
            role_map = voice_map.setdefault(role, {})
            role_map[label] = display_name
            return display_name

        def enqueue(
            key: str, text: str, lang_code: str, language_label: str | None = None
        ) -> None:
            tasks.append((key, text, lang_code))
            segment_texts[key] = text
            segment_languages[key] = (
                _language_label(key, lang_code, language_label),
                lang_code,
            )

        target_lang_code = _lang_code(target_language)
        source_lang_code = _lang_code(input_language)

        numbering_str = f"{sentence_number} - {(sentence_number / total_sentences * 100):.2f}%"

        if audio_mode == "1":
            enqueue("translation", translation_audio_text, target_lang_code, target_language)
            sequence = ["translation"]
        elif audio_mode == "2":
            enqueue("number", numbering_str, "en", "English")
            enqueue("translation", translation_audio_text, target_lang_code, target_language)
            sequence = ["number", "translation"]
        elif audio_mode == "3":
            enqueue("number", numbering_str, "en", "English")
            enqueue("input", input_sentence, source_lang_code, input_language)
            enqueue("translation", translation_audio_text, target_lang_code, target_language)
            sequence = ["number", "input", "translation"]
        elif audio_mode == "4":
            enqueue("input", input_sentence, source_lang_code, input_language)
            enqueue("translation", translation_audio_text, target_lang_code, target_language)
            sequence = ["input", "translation"]
        elif audio_mode == "5":
            enqueue("input", input_sentence, source_lang_code, input_language)
            sequence = ["input"]
        else:
            enqueue("input", input_sentence, source_lang_code, input_language)
            enqueue("translation", translation_audio_text, target_lang_code, target_language)
            sequence = ["input", "translation"]

        if not tasks:
            silent_audio = self._change_audio_tempo(
                AudioSegment.silent(duration=0), tempo
            )
            return SynthesisResult(audio=silent_audio, voice_metadata={})

        worker_count = max(1, min(cfg.get_thread_count(), len(tasks)))
        segments: Dict[str, AudioSegment] = {}

        client = self._resolve_client()

        backend_config = {
            "tts_backend": tts_backend,
            "tts_executable_path": tts_executable_path,
            "say_path": tts_executable_path,
        }

        def _generate_with_legacy(key: str, text: str, lang_code: str) -> AudioSegment:
            segment = generate_audio(
                text,
                lang_code,
                selected_voice,
                macos_reading_speed,
                config=backend_config,
            )
            _record_voice(key, selected_voice)
            return segment

        def _extract_voice(headers: Mapping[str, str] | None) -> Optional[str]:
            if not headers:
                return None
            for header in ("X-Selected-Voice", "x-selected-voice"):
                value = headers.get(header)
                if value:
                    return str(value)
            return None

        if client is None:

            if worker_count == 1:
                for key, text, lang_code in tasks:
                    segments[key] = _generate_with_legacy(key, text, lang_code)
            else:
                with ThreadPoolExecutor(max_workers=worker_count) as executor:
                    future_map = {
                        executor.submit(
                            _generate_with_legacy,
                            key,
                            text,
                            lang_code,
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
                api_voice = _normalize_api_voice(
                    selected_voice, language=lang_code, sample_text=text
                )
                attributes = {
                    "segment": key,
                    "language": lang_code,
                    "voice": selected_voice,
                    "has_speed": macos_reading_speed is not None,
                }
                if api_voice and api_voice != selected_voice:
                    attributes["resolved_voice"] = api_voice
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
                    synth_response = client.synthesize(
                        text=text,
                        voice=api_voice,
                        speed=macos_reading_speed or None,
                        language=lang_code,
                        return_metadata=True,
                    )
                    if isinstance(synth_response, tuple):
                        segment, response_headers = synth_response
                    else:  # pragma: no cover - defensive safeguard
                        segment = synth_response
                        response_headers = {}
                except MediaBackendError:
                    duration_ms = (time.perf_counter() - start) * 1000.0
                    observability.record_metric(
                        "audio.api.synthesize.duration",
                        duration_ms,
                        {**attributes, "status": "error"},
                    )
                    logger.warning(
                        "Audio API synthesis failed; falling back to local backend",
                        extra={
                            "event": "audio.api.synthesize.fallback",
                            "attributes": attributes,
                            "console_suppress": True,
                        },
                        exc_info=True,
                    )
                    return key, _generate_with_legacy(key, text, lang_code)
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
                resolved_voice = (
                    _extract_voice(response_headers) or api_voice or selected_voice
                )
                voice_name = _record_voice(key, resolved_voice)
                if resolved_voice:
                    attributes["resolved_voice"] = resolved_voice
                if voice_name:
                    attributes["voice_name"] = voice_name
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

        normalized_voice_map = {
            role: dict(language_map)
            for role, language_map in voice_map.items()
            if language_map
        }

        return SynthesisResult(
            audio=tempo_adjusted,
            voice_metadata=normalized_voice_map,
        )

    @staticmethod
    def _change_audio_tempo(sound: AudioSegment, tempo: float = 1.0) -> AudioSegment:
        if tempo == 1.0:
            return sound
        new_frame_rate = int(sound.frame_rate * tempo)
        return sound._spawn(sound.raw_data, overrides={"frame_rate": new_frame_rate}).set_frame_rate(
            sound.frame_rate
        )


__all__ = ["PollyAudioSynthesizer"]
