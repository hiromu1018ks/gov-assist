"""POST /api/proofread — AI 文書校正の実行 (§4.4, §5.2, §5.5)."""
import logging

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

# from dependencies import verify_token  # Auth disabled for localhost MVP
from schemas import (
    ErrorResponse,
    ProofreadRequest,
    ProofreadResponse,
    ProofreadStatus,
)
from services.ai_client import (
    AIClientError,
    create_ai_client,
    get_model_config,
)
from services.diff_service import compute_diffs
from services.prompt_builder import build_prompts
from services.response_parser import parse_ai_response

logger = logging.getLogger("govassist")

router = APIRouter(prefix="/api", tags=["proofread"])

LARGE_REWRITE_SUMMARY = "⚠️ AI が広範囲を書き換えました。内容を十分ご確認ください。"

# §5.5: AI エラーの HTTP ステータスコード・メッセージ対応
_AI_ERROR_MAP: dict[str, tuple[int, str]] = {
    "ai_timeout": (504, "AI応答がタイムアウトしました（60秒）"),
    "ai_rate_limit": (502, "AI APIのレート制限に達しました"),
    "ai_invalid_response": (502, "AI API エラーが発生しました"),
}


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
    # token: str = Depends(verify_token)  # Auth disabled
):
    """AI 文書校正を実行する (§4.4, §5.2)."""
    request_id = payload.request_id

    # Validate model exists
    try:
        config = get_model_config(payload.model)
    except KeyError:
        return _error_json(
            request_id,
            "validation_error",
            f"指定されたモデルが見つかりません: {payload.model}",
            400,
        )

    try:
        # Build prompts
        system_prompt, user_prompt = build_prompts(payload)

        # Call AI
        ai_client = create_ai_client()
        raw_response = await ai_client.complete(
            model=payload.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            request_id=request_id,
        )

        # Parse AI response
        parse_result = await parse_ai_response(
            raw_response=raw_response,
            ai_client=ai_client,
            model=payload.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            request_id=request_id,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )

        # Parse complete failure → HTTP 502
        if parse_result.status == ProofreadStatus.ERROR:
            return _error_json(
                request_id,
                "ai_parse_error",
                "校正結果を解析できませんでした",
                502,
            )

        # Parse partial (fallback) → return without diffs
        if parse_result.status == ProofreadStatus.PARTIAL:
            return ProofreadResponse(
                request_id=request_id,
                status=ProofreadStatus.PARTIAL,
                status_reason=parse_result.status_reason,
                warnings=[],
                corrected_text=parse_result.corrected_text,
                summary=parse_result.summary,
                corrections=parse_result.corrections,
                diffs=[],
            )

        # Compute diffs
        diff_result = compute_diffs(
            input_text=payload.text,
            corrected_text=parse_result.corrected_text,
            corrections=parse_result.corrections,
            request_id=request_id,
        )

        # Append large_rewrite warning to summary
        summary = parse_result.summary
        if "large_rewrite" in diff_result.warnings:
            if summary:
                summary = summary + "\n\n" + LARGE_REWRITE_SUMMARY
            else:
                summary = LARGE_REWRITE_SUMMARY

        return ProofreadResponse(
            request_id=request_id,
            status=diff_result.status,
            status_reason=diff_result.status_reason,
            warnings=diff_result.warnings,
            corrected_text=parse_result.corrected_text,
            summary=summary,
            corrections=diff_result.corrections,
            diffs=diff_result.diffs,
        )

    except AIClientError as e:
        status_code, message = _AI_ERROR_MAP.get(
            e.error_code, (502, "AI API エラーが発生しました"),
        )
        # Sanitize unknown error codes to prevent leaking undocumented codes
        error_code = e.error_code if e.error_code in _AI_ERROR_MAP else "ai_invalid_response"
        logger.error(
            "Proofread AI error: request_id=%s error=%s message=%s",
            request_id, e.error_code, e.message,
        )
        return _error_json(request_id, error_code, message, status_code)

    except Exception as e:
        logger.error(
            "Proofread internal error: request_id=%s error=%s",
            request_id, str(e),
            exc_info=True,
        )
        return _error_json(
            request_id,
            "internal_error",
            "サーバー内部エラーが発生しました",
            500,
        )
