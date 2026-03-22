"""POST /api/export/docx — 校正済みテキストの .docx 生成 (§5.3, §6.2)."""
import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from starlette.responses import JSONResponse

# from dependencies import verify_token  # Auth disabled for localhost MVP
from schemas import ErrorResponse, ExportDocxRequest
from services.docx_exporter import generate_docx

logger = logging.getLogger("govassist")

router = APIRouter(prefix="/api", tags=["export"])

_DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_DOCX_FILENAME = "校正済み文書.docx"
_DOCX_FILENAME_ASCII = "corrected_document.docx"


@router.post("/export/docx")
async def export_docx(
    payload: ExportDocxRequest,
    # token: str = Depends(verify_token)  # Auth disabled
):
    """校正済みテキストから .docx を生成して返す (§5.3, §6.2)."""
    try:
        docx_bytes = generate_docx(
            corrected_text=payload.corrected_text,
            document_type=payload.document_type.value,
        )
    except Exception as e:
        logger.error(
            "Export docx error: %s",
            str(e),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                request_id="",
                error="internal_error",
                message="サーバー内部エラーが発生しました",
            ).model_dump(),
        )

    return Response(
        content=docx_bytes,
        media_type=_DOCX_CONTENT_TYPE,
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{_DOCX_FILENAME_ASCII}\"; "
                f"filename*=UTF-8''{quote(_DOCX_FILENAME)}"
            ),
        },
    )
