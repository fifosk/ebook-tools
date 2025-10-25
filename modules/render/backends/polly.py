"""Amazon Polly-based implementation of :class:`AudioSynthesizer`."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Mapping

from pydub import AudioSegment

from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules.audio.highlight import _compute_audio_highlight_metadata, _store_audio_metadata
from modules.audio.tts import synthesize_segment
from modules.core.translation import split_translation_and_transliteration

from .base import AudioSynthesizer

logger = log_mgr.logger


class PollyAudioSynthesizer(AudioSynthesizer):
    """Synthesize audio using the built-in Amazon Polly helper."""

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

        if worker_count == 1:
            for key, text, lang_code in tasks:
                segments[key] = synthesize_segment(text, lang_code, selected_voice, macos_reading_speed)
        else:
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                future_map = {
                    executor.submit(
                        synthesize_segment, text, lang_code, selected_voice, macos_reading_speed
                    ): key
                    for key, text, lang_code in tasks
                }
                for future in as_completed(future_map):
                    key = future_map[future]
                    try:
                        segments[key] = future.result()
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.error("Audio synthesis failed for segment '%s': %s", key, exc)
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
