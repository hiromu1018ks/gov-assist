"""GET/POST/PATCH/DELETE /api/history — 履歴 CRUD (§5.1, §5.4, §7)."""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
# from dependencies import verify_token  # Auth disabled for localhost MVP
from schemas import (
    HistoryCreateRequest,
    HistoryDetailResponse,
    HistoryListItemResponse,
    HistoryListResponse,
    HistoryUpdateRequest,
    ProofreadResponse,
)
from services.history_service import (
    create_history,
    delete_all_history,
    delete_history,
    get_history_by_id,
    get_history_list,
    update_history_memo,
)

logger = logging.getLogger("govassist")

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history", response_model=HistoryListResponse)
async def list_history(
    q: str | None = Query(None, description="キーワード検索"),
    document_type: str | None = Query(None, description="文書種別フィルタ"),
    date_from: datetime | None = Query(None, description="開始日 (ISO 8601)"),
    date_to: datetime | None = Query(None, description="終了日 (ISO 8601)"),
    limit: int = Query(20, ge=1, le=200, description="取得件数"),
    offset: int = Query(0, ge=0, description="オフセット"),
    # token: str = Depends(verify_token)  # Auth disabled
    db: Session = Depends(get_db),
):
    """履歴一覧を取得する (§5.4)."""
    items, total = get_history_list(
        db,
        q=q,
        document_type=document_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return HistoryListResponse(
        items=[
            HistoryListItemResponse(
                id=h.id,
                preview=h.input_text[:50],
                document_type=h.document_type,
                model=h.model,
                created_at=h.created_at,
                truncated=h.truncated,
                memo=h.memo,
            )
            for h in items
        ],
        total=total,
    )


@router.post("/history", response_model=HistoryDetailResponse, status_code=201)
async def save_history(
    payload: HistoryCreateRequest,
    # token: str = Depends(verify_token)  # Auth disabled
    db: Session = Depends(get_db),
):
    """校正結果を履歴に保存する (§7.1)."""
    record = create_history(
        db,
        input_text=payload.input_text,
        result=payload.result,
        model=payload.model,
        document_type=payload.document_type,
        memo=payload.memo,
    )
    return _to_detail(record)


@router.get("/history/{history_id}", response_model=HistoryDetailResponse)
async def get_history(
    history_id: int,
    # token: str = Depends(verify_token)  # Auth disabled
    db: Session = Depends(get_db),
):
    """履歴の詳細を取得する."""
    record = get_history_by_id(db, history_id)
    if record is None:
        raise HTTPException(status_code=404, detail="指定された履歴が見つかりません")
    return _to_detail(record)


@router.patch("/history/{history_id}", response_model=HistoryDetailResponse)
async def patch_history(
    history_id: int,
    payload: HistoryUpdateRequest,
    # token: str = Depends(verify_token)  # Auth disabled
    db: Session = Depends(get_db),
):
    """履歴のメモを更新する."""
    record = update_history_memo(db, history_id, payload.memo)
    if record is None:
        raise HTTPException(status_code=404, detail="指定された履歴が見つかりません")
    return _to_detail(record)


@router.delete("/history/{history_id}")
async def delete_history_endpoint(
    history_id: int,
    # token: str = Depends(verify_token)  # Auth disabled
    db: Session = Depends(get_db),
):
    """履歴を1件削除する."""
    if not delete_history(db, history_id):
        raise HTTPException(status_code=404, detail="指定された履歴が見つかりません")
    return {"message": "削除しました"}


@router.delete("/history")
async def delete_all_history_endpoint(
    # token: str = Depends(verify_token)  # Auth disabled
    db: Session = Depends(get_db),
):
    """履歴を全件削除する."""
    count = delete_all_history(db)
    return {"message": f"{count}件の履歴を削除しました"}


def _to_detail(record) -> HistoryDetailResponse:
    """Convert ORM History to HistoryDetailResponse."""
    result_data = json.loads(record.result_json)
    return HistoryDetailResponse(
        id=record.id,
        input_text=record.input_text,
        result=ProofreadResponse(**result_data),
        model=record.model,
        document_type=record.document_type,
        created_at=record.created_at,
        truncated=record.truncated,
        memo=record.memo,
    )
