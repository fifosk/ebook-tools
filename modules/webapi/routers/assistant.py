"""Assistant HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from modules.services.assistant import lookup_dictionary_entry
from modules.webapi.dependencies import RequestUserContext, get_request_user
from modules.webapi.schemas import AssistantLookupRequest, AssistantLookupResponse

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/lookup", response_model=AssistantLookupResponse, status_code=status.HTTP_200_OK)
async def lookup(
    payload: AssistantLookupRequest,
    request_user: RequestUserContext = Depends(get_request_user),
) -> AssistantLookupResponse:
    """Perform a single-turn dictionary lookup using the configured LLM backends."""

    if not request_user.user_id:
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return AssistantLookupResponse(
        answer=result.answer,
        model=result.model,
        token_usage=result.token_usage,
        source=result.source,
    )


__all__ = ["router"]
