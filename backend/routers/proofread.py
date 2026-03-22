"""POST /api/proofread — AI 文書校正の実行 (§4.4, §5.2, §5.5)."""
import logging

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from dependencies import verify_token
from schemas import (
    ErrorResponse,
    ProofreadRequest,
    ProofreadResponse,
)
from services.ai_client import get_model_config

logger = logging.getLogger("govassist")

router = APIRouter(prefix="/api", tags=["proofread"])


def _error_json(request_id: str, error: str, message: str, status: int) -> JSONResponse:
    """Build a JSON error response per §5.5."""
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(
            request_id=request_id,
            error=error,
            message=message,
        ).model_dump(),
    )


@router.post("/proofread", response_model=ProofreadResponse)
async def proofread(
    payload: ProofreadRequest,
    token: str = Depends(verify_token),
):
    """AI 文書校正を実行する (§4.4, §5.2)."""
    request_id = payload.request_id

    # Validate model exists
    try:
        get_model_config(payload.model)
    except KeyError:
        return _error_json(
            request_id,
            "validation_error",
            f"指定されたモデルが見つかりません: {payload.model}",
            400,
        )

    # TODO: implement pipeline (Task 2+)
    return ProofreadResponse(
        request_id=request_id,
        status="success",
        corrected_text=payload.text,
    )
