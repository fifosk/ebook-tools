"""Routes for playback analytics (heartbeat)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import RequestUserContext, get_analytics_service, get_request_user
from ..schemas.playback import PlaybackHeartbeatPayload, PlaybackHeartbeatResponse

router = APIRouter(prefix="/api/playback", tags=["playback"])


def _require_user(request_user: RequestUserContext) -> str:
    if not request_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session token",
        )
    return request_user.user_id


@router.post("/heartbeat", response_model=PlaybackHeartbeatResponse)
def playback_heartbeat(
    payload: PlaybackHeartbeatPayload,
    request_user: RequestUserContext = Depends(get_request_user),
    analytics_service=Depends(get_analytics_service),
) -> PlaybackHeartbeatResponse:
    """Record a playback heartbeat with listened seconds."""
    user_id = _require_user(request_user)
    if analytics_service is not None:
        analytics_service.record_playback_heartbeat(
            user_id=user_id,
            job_id=payload.job_id,
            language=payload.language,
            track_kind=payload.track_kind,
            delta_seconds=payload.delta_seconds,
        )
    return PlaybackHeartbeatResponse()
