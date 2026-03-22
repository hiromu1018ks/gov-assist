"""History CRUD service (§5.1, §5.4, §7)."""
import json
import logging
import os

from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from database import FTS5_NGRAM_SUPPORTED, get_database_url
from models import History

logger = logging.getLogger("govassist")

RESULT_JSON_MAX_BYTES = 100 * 1024  # 100KB (§7.1)
CAPACITY_LIMIT_BYTES = 20 * 1024 * 1024  # 20MB (§7.1)
DEFAULT_HISTORY_LIMIT = 50


def _truncate_result_json(result) -> tuple[str, bool]:
    """Serialize result to JSON, truncate if > 100KB.

    Returns (json_string, truncated_flag).
    Truncation: keep corrected_text + summary, remove corrections/diffs.
    """
    json_str = result.model_dump_json()
    if len(json_str.encode("utf-8")) <= RESULT_JSON_MAX_BYTES:
        return json_str, False

    logger.info("Result JSON exceeds 100KB, truncating corrections/diffs")
    truncated = result.model_copy(update={
        "corrections": [],
        "diffs": [],
    })
    return truncated.model_dump_json(), True


def _get_history_limit(db: Session) -> int:
    """Read history_limit from settings table."""
    from models import Settings
    row = db.query(Settings).filter_by(key="history_limit").first()
    if row:
        try:
            return int(row.value)
        except (ValueError, TypeError):
            pass
    return DEFAULT_HISTORY_LIMIT


def _get_db_file_size() -> int | None:
    """Get database file size in bytes. Returns None for in-memory DBs."""
    url = get_database_url()
    if ":memory:" in url:
        return None
    db_path = url.replace("sqlite:///", "")
    if not os.path.exists(db_path):
        return 0
    return os.path.getsize(db_path)


def _enforce_count_limit(db: Session) -> None:
    """Delete oldest records exceeding the configured count limit."""
    limit = _get_history_limit(db)
    count = db.query(History).count()
    if count <= limit:
        return

    excess = count - limit
    oldest_ids = (
        db.query(History.id)
        .order_by(History.created_at.asc())
        .limit(excess)
        .all()
    )
    if oldest_ids:
        ids_to_delete = [row[0] for row in oldest_ids]
        db.query(History).filter(History.id.in_(ids_to_delete)).delete(synchronize_session="fetch")
        db.flush()
        logger.info("Auto-deleted %d oldest history records (count limit: %d)", len(ids_to_delete), limit)


def _enforce_capacity_limit(db: Session) -> None:
    """Delete oldest records if DB file exceeds 20MB."""
    size = _get_db_file_size()
    if size is None or size <= CAPACITY_LIMIT_BYTES:
        return

    logger.warning(
        "DB size %.1fMB exceeds 20MB limit, auto-deleting oldest records",
        size / (1024 * 1024),
    )
    while _get_db_file_size() and _get_db_file_size() > CAPACITY_LIMIT_BYTES:
        oldest = db.query(History).order_by(History.created_at.asc()).first()
        if oldest is None:
            break
        db.delete(oldest)
        db.flush()


def create_history(
    db: Session,
    *,
    input_text: str,
    result,
    model: str,
    document_type: str,
    memo: str | None = None,
) -> History:
    """Save a proofread result to history. Enforces truncation and auto-cleanup."""
    result_json, truncated = _truncate_result_json(result)

    record = History(
        input_text=input_text,
        result_json=result_json,
        model=model,
        document_type=document_type,
        memo=memo,
        truncated=truncated,
    )
    db.add(record)
    db.flush()

    _enforce_count_limit(db)
    _enforce_capacity_limit(db)

    return record


def get_history_by_id(db: Session, history_id: int) -> History | None:
    """Fetch a single history record by ID."""
    return db.query(History).filter(History.id == history_id).first()
