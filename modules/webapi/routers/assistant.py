"""Assistant HTTP routes."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, status

from modules import logging_manager as log_mgr
from modules.services.assistant import lookup_dictionary_entry
from modules.webapi.dependencies import RequestUserContext, get_request_user
from modules.webapi.route_telemetry import log_started_route_result
from modules.webapi.schemas import AssistantLookupRequest, AssistantLookupResponse

router = APIRouter(prefix="/api/assistant", tags=["assistant"])
logger = log_mgr.get_logger().getChild("webapi.assistant")

ASSISTANT_LOOKUP_BAD_REQUEST_MESSAGE = "Assistant lookup request is invalid."
ASSISTANT_LOOKUP_UNAVAILABLE_MESSAGE = "Unable to complete assistant lookup."


def _log_assistant_lookup_result(result: str, started_at: float) -> None:
    log_started_route_result(
        logger,
        metric_name="ASSISTANT_LOOKUP_ROUTE_DURATION",
        message="Assistant lookup route",
        operation="lookup",
        result=result,
        started_at=started_at,
    )


@router.post("/lookup", response_model=AssistantLookupResponse, status_code=status.HTTP_200_OK)
async def lookup(
    payload: AssistantLookupRequest,
    request_user: RequestUserContext = Depends(get_request_user),
) -> AssistantLookupResponse:
    """Perform a single-turn dictionary lookup using the configured LLM backends."""

    started_at = time.perf_counter()
    if not request_user.user_id:
        _log_assistant_lookup_result("unauthorized", started_at)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session token")

    try:
        result = lookup_dictionary_entry(
            query=payload.query,
            input_language=payload.input_language,
            lookup_language=payload.lookup_language,
            llm_model=payload.llm_model,
            system_prompt=payload.system_prompt,
            history=[message.model_dump() for message in payload.history],
        )
    except ValueError as exc:
        _log_assistant_lookup_result("bad_request", started_at)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ASSISTANT_LOOKUP_BAD_REQUEST_MESSAGE,
        ) from exc
    except Exception as exc:
        _log_assistant_lookup_result("error", started_at)
        logger.warning(
            "Assistant lookup route failed unexpectedly; response detail suppressed"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ASSISTANT_LOOKUP_UNAVAILABLE_MESSAGE,
        ) from exc

    try:
        response_payload = AssistantLookupResponse(
            answer=result.answer,
            model=result.model,
            token_usage=result.token_usage,
            source=result.source,
        )
    except Exception as exc:
        _log_assistant_lookup_result("error", started_at)
        logger.warning(
            "Assistant lookup route failed unexpectedly; response detail suppressed"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ASSISTANT_LOOKUP_UNAVAILABLE_MESSAGE,
        ) from exc

    _log_assistant_lookup_result("success", started_at)
    return response_payload


__all__ = ["router"]
