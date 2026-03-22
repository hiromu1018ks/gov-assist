"""GET/PUT /api/settings — サーバー側設定 CRUD (§3.4, §5.1)."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependencies import verify_token
from models import Settings
from schemas import SettingsResponse, SettingsUpdateRequest

logger = logging.getLogger("govassist")

router = APIRouter(prefix="/api", tags=["settings"])

DEFAULT_HISTORY_LIMIT = 50


def _get_setting(db: Session, key: str, default: str) -> str:
    """Get a setting value from DB, or return default."""
    row = db.query(Settings).filter_by(key=key).first()
    return row.value if row else default


def _set_setting(db: Session, key: str, value: str) -> None:
    """Set a setting value in DB (upsert)."""
    row = db.query(Settings).filter_by(key=key).first()
    if row:
        row.value = value
    else:
        db.add(Settings(key=key, value=value))


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    token: str = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get server-side settings. Returns defaults for unset values."""
    raw = _get_setting(db, "history_limit", str(DEFAULT_HISTORY_LIMIT))
    try:
        history_limit = int(raw)
    except (ValueError, TypeError):
        logger.warning("Invalid history_limit value in DB: %r, using default", raw)
        history_limit = DEFAULT_HISTORY_LIMIT
    return SettingsResponse(history_limit=history_limit)


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdateRequest,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Update server-side settings."""
    _set_setting(db, "history_limit", str(payload.history_limit))
    db.commit()
    return SettingsResponse(history_limit=payload.history_limit)
