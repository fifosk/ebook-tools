"""Serialization helpers for pipeline job metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

from .job import PipelineJobStatus


def _stable_copy(value: Any) -> Any:
    """Return a deterministically ordered, JSON-serializable copy of ``value``."""

    if isinstance(value, Mapping):
        return {key: _stable_copy(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_stable_copy(item) for item in value]
    if isinstance(value, set):
        return [_stable_copy(item) for item in sorted(value, key=lambda item: repr(item))]
    return value


@dataclass
class PipelineJobMetadata:
    """Serializable metadata describing a pipeline job."""

    job_id: str
    job_type: str
    status: PipelineJobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    last_event: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    request_payload: Optional[Dict[str, Any]] = None
    resume_context: Optional[Dict[str, Any]] = None
    tuning_summary: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    access: Optional[Dict[str, Any]] = None
    generated_files: Optional[Dict[str, Any]] = None
    media_completed: Optional[bool] = None
    timing_tracks: Optional[Dict[str, Any]] = None
    retry_summary: Optional[Dict[str, Dict[str, int]]] = None

    def to_dict(self) -> Dict[str, Any]:
        def _dt(value: Optional[datetime]) -> Optional[str]:
            return value.isoformat() if value is not None else None

        payload: Dict[str, Any] = {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status.value,
            "created_at": _dt(self.created_at),
            "started_at": _dt(self.started_at),
            "completed_at": _dt(self.completed_at),
            "error_message": self.error_message,
            "last_event": _stable_copy(self.last_event) if self.last_event is not None else None,
            "result": _stable_copy(self.result) if self.result is not None else None,
            "resume_context": _stable_copy(self.resume_context)
            if self.resume_context is not None
            else None,
            "tuning_summary": _stable_copy(self.tuning_summary)
            if self.tuning_summary is not None
            else None,
            "retry_summary": _stable_copy(self.retry_summary)
            if self.retry_summary is not None
            else None,
        }
        if self.request_payload is not None:
            payload["request"] = _stable_copy(self.request_payload)
        if self.user_id is not None:
            payload["user_id"] = self.user_id
        if self.user_role is not None:
            payload["user_role"] = self.user_role
        if self.access is not None:
            payload["access"] = _stable_copy(self.access)
        if self.generated_files is not None:
            payload["generated_files"] = _stable_copy(self.generated_files)
        if self.media_completed is not None:
            payload["media_completed"] = bool(self.media_completed)
        if self.timing_tracks is not None:
            payload["timing_tracks"] = _stable_copy(self.timing_tracks)
        return payload

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        if value is None:
            return None
        return datetime.fromisoformat(value)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PipelineJobMetadata":
        return cls(
            job_id=str(data["job_id"]),
            job_type=str(data.get("job_type") or "pipeline"),
            status=PipelineJobStatus(str(data["status"])),
            created_at=cls._parse_datetime(data.get("created_at")) or datetime.now(timezone.utc),
            started_at=cls._parse_datetime(data.get("started_at")),
            completed_at=cls._parse_datetime(data.get("completed_at")),
            error_message=data.get("error_message"),
            last_event=data.get("last_event"),
            result=data.get("result"),
            request_payload=data.get("request"),
            resume_context=data.get("resume_context") or data.get("request"),
            tuning_summary=data.get("tuning_summary"),
            user_id=data.get("user_id"),
            user_role=data.get("user_role"),
            access=data.get("access"),
            generated_files=data.get("generated_files"),
            media_completed=data.get("media_completed"),
            timing_tracks=data.get("timing_tracks"),
            retry_summary=data.get("retry_summary"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "PipelineJobMetadata":
        return cls.from_dict(json.loads(payload))


__all__ = ["PipelineJobMetadata", "_stable_copy"]
