"""Media analytics service — records generation stats and playback sessions."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from sqlalchemy import and_, func, select, text

from ..database.engine import get_db_session
from ..database.models.analytics import MediaGenerationStatModel, PlaybackSessionModel

logger = logging.getLogger(__name__).getChild("analytics_service")

# Window within which heartbeats extend an existing session rather than
# creating a new one.
_SESSION_CONTINUATION_WINDOW = timedelta(minutes=5)

# Track key aliases → canonical track_kind
_TRACK_KIND_MAP: Dict[str, str] = {
    "orig": "original",
    "original": "original",
    "translation": "translation",
    "trans": "translation",
}


@dataclass(frozen=True)
class _GenerationEntry:
    """One row to be inserted into media_generation_stats."""

    language: str
    track_kind: str
    duration_seconds: float
    sentence_count: int
    chunk_count: int


class MediaAnalyticsService:
    """Records media generation statistics and playback sessions.

    All methods are safe to call in fire-and-forget fashion — errors are
    logged but never propagated to the caller.
    """

    # ------------------------------------------------------------------
    # Generation stats
    # ------------------------------------------------------------------

    def record_generation_stats(self, job: Any) -> None:
        """Extract duration data from a completed job and persist.

        Parameters
        ----------
        job:
            A :class:`PipelineJob` (or duck-typed object) that has been
            marked COMPLETED.  Must expose ``job_id``, ``job_type``,
            ``generated_files``, ``request_payload``, and
            ``result_payload``.
        """
        try:
            self._record_generation_stats_impl(job)
        except Exception:
            logger.debug(
                "Failed to record generation stats for job %s",
                getattr(job, "job_id", "?"),
                exc_info=True,
            )

    def _record_generation_stats_impl(self, job: Any) -> None:
        generated_files = getattr(job, "generated_files", None) or {}
        if not generated_files:
            return

        job_id: str = job.job_id
        job_type: str = getattr(job, "job_type", "pipeline") or "pipeline"

        input_lang, target_langs = self._resolve_languages(job)
        entries = self._extract_audio_durations(
            generated_files, job_type, input_lang, target_langs
        )
        if not entries:
            return

        with get_db_session() as session:
            for entry in entries:
                existing = session.execute(
                    select(MediaGenerationStatModel).where(
                        and_(
                            MediaGenerationStatModel.job_id == job_id,
                            MediaGenerationStatModel.language == entry.language,
                            MediaGenerationStatModel.track_kind == entry.track_kind,
                        )
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    # Idempotent — already recorded.
                    continue
                session.add(
                    MediaGenerationStatModel(
                        job_id=job_id,
                        job_type=job_type,
                        language=entry.language,
                        track_kind=entry.track_kind,
                        duration_seconds=entry.duration_seconds,
                        sentence_count=entry.sentence_count,
                        chunk_count=entry.chunk_count,
                    )
                )
        logger.info(
            "Recorded %d generation stat entries for job %s",
            len(entries),
            job_id,
        )

    # ------------------------------------------------------------------
    # Audio duration extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_audio_durations(
        generated_files: Mapping[str, Any],
        job_type: str,
        input_language: Optional[str],
        target_languages: List[str],
    ) -> List[_GenerationEntry]:
        """Walk ``generated_files["chunks"]`` and sum audio durations.

        Returns one :class:`_GenerationEntry` per (language, track_kind)
        pair found.
        """
        chunks = generated_files.get("chunks")
        if not isinstance(chunks, list) or not chunks:
            return []

        # Accumulators: (track_kind, language) → [total_duration, sentence_count, chunk_count]
        acc: Dict[Tuple[str, str], List[float]] = {}

        for chunk in chunks:
            if not isinstance(chunk, Mapping):
                continue

            audio_tracks = chunk.get("audioTracks") or chunk.get("audio_tracks") or {}
            if not isinstance(audio_tracks, Mapping):
                continue

            sentence_count = 0
            sc_val = chunk.get("sentenceCount") or chunk.get("sentence_count")
            if sc_val is not None:
                try:
                    sentence_count = int(sc_val)
                except (TypeError, ValueError):
                    pass

            for track_key, track_meta in audio_tracks.items():
                kind = _TRACK_KIND_MAP.get(track_key)
                if kind is None:
                    continue

                # Resolve language for this track
                if kind == "original":
                    lang = (input_language or "").strip() or "unknown"
                else:
                    lang = (target_languages[0] if target_languages else "").strip() or "unknown"

                duration = 0.0
                if isinstance(track_meta, Mapping):
                    try:
                        duration = float(track_meta.get("duration", 0))
                    except (TypeError, ValueError):
                        pass

                key = (kind, lang)
                if key not in acc:
                    acc[key] = [0.0, 0, 0]
                acc[key][0] += duration
                acc[key][1] += sentence_count
                acc[key][2] += 1

        return [
            _GenerationEntry(
                language=lang,
                track_kind=kind,
                duration_seconds=round(vals[0], 6),
                sentence_count=vals[1],
                chunk_count=vals[2],
            )
            for (kind, lang), vals in acc.items()
            if vals[0] > 0
        ]

    # ------------------------------------------------------------------
    # Language resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_languages(job: Any) -> Tuple[Optional[str], List[str]]:
        """Extract (input_language, target_languages) from the job.

        Handles all three job types:
        - Pipeline: request_payload.inputs.{input_language, target_languages}
        - YouTube dub: result_payload.youtube_dub.{source_language, language}
        - Subtitle: request_payload.options.target_language
        """
        request_payload = getattr(job, "request_payload", None) or {}
        result_payload = getattr(job, "result_payload", None) or {}
        job_type = getattr(job, "job_type", "pipeline") or "pipeline"

        input_lang: Optional[str] = None
        target_langs: List[str] = []

        if job_type in ("pipeline", "book"):
            inputs = request_payload.get("inputs") or {}
            input_lang = inputs.get("input_language")
            raw_targets = inputs.get("target_languages")
            if isinstance(raw_targets, list):
                target_langs = [t for t in raw_targets if isinstance(t, str) and t.strip()]
            elif isinstance(raw_targets, str) and raw_targets.strip():
                target_langs = [raw_targets.strip()]

        elif job_type == "youtube_dub":
            yt = result_payload.get("youtube_dub") or {}
            input_lang = yt.get("source_language")
            lang = yt.get("language")
            if isinstance(lang, str) and lang.strip():
                target_langs = [lang.strip()]

        elif job_type == "subtitle":
            options = request_payload.get("options") or {}
            input_lang = options.get("source_language") or options.get("input_language")
            tl = options.get("target_language") or options.get("language")
            if isinstance(tl, str) and tl.strip():
                target_langs = [tl.strip()]

        return input_lang, target_langs

    # ------------------------------------------------------------------
    # Playback heartbeat
    # ------------------------------------------------------------------

    def record_playback_heartbeat(
        self,
        *,
        user_id: str,
        job_id: str,
        language: str,
        track_kind: str,
        delta_seconds: float,
    ) -> None:
        """Record a playback heartbeat.

        If a recent session exists for the same (user, job, language,
        track) combination whose ``ended_at`` is within the continuation
        window, the existing session is extended.  Otherwise a new
        session row is created.
        """
        if delta_seconds <= 0:
            return

        now = datetime.now(timezone.utc)
        cutoff = now - _SESSION_CONTINUATION_WINDOW

        with get_db_session() as session:
            # Try to find a recent continuable session.
            model = session.execute(
                select(PlaybackSessionModel)
                .where(
                    and_(
                        PlaybackSessionModel.user_id == user_id,
                        PlaybackSessionModel.job_id == job_id,
                        PlaybackSessionModel.language == language,
                        PlaybackSessionModel.track_kind == track_kind,
                        PlaybackSessionModel.ended_at > cutoff,
                    )
                )
                .order_by(PlaybackSessionModel.ended_at.desc())
                .limit(1)
            ).scalar_one_or_none()

            if model is not None:
                model.duration_seconds += delta_seconds
                model.ended_at = now
            else:
                session.add(
                    PlaybackSessionModel(
                        user_id=user_id,
                        job_id=job_id,
                        language=language,
                        track_kind=track_kind,
                        duration_seconds=delta_seconds,
                        started_at=now,
                        ended_at=now,
                    )
                )


def get_analytics_service() -> Optional[MediaAnalyticsService]:
    """Module-level accessor.

    Returns ``None`` when PostgreSQL is not configured (no ``DATABASE_URL``).
    """
    if not os.environ.get("DATABASE_URL", "").strip():
        return None
    return MediaAnalyticsService()
