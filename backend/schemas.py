from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class DocumentType(str, Enum):
    EMAIL = "email"
    REPORT = "report"
    OFFICIAL = "official"
    OTHER = "other"


class ProofreadStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"


class StatusReason(str, Enum):
    DIFF_TIMEOUT = "diff_timeout"
    PARSE_FALLBACK = "parse_fallback"


class DiffType(str, Enum):
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"


class ProofreadOptions(BaseModel):
    typo: bool = True
    keigo: bool = True
    terminology: bool = True
    style: bool = True
    legal: bool = False
    readability: bool = True


class ProofreadRequest(BaseModel):
    request_id: str
    text: str = Field(min_length=1, max_length=8000)
    document_type: DocumentType
    options: ProofreadOptions = ProofreadOptions()
    model: str = "kimi-k2.5"


class CorrectionItem(BaseModel):
    original: str
    corrected: str
    reason: str
    category: str
    diff_matched: bool = False


class DiffBlock(BaseModel):
    type: DiffType
    text: str
    start: int
    position: str | None = None
    reason: str | None = None


class ProofreadResponse(BaseModel):
    request_id: str
    status: ProofreadStatus
    status_reason: StatusReason | None = None
    warnings: list[str] = []
    corrected_text: str
    summary: str | None = None
    corrections: list[CorrectionItem] = []
    diffs: list[DiffBlock] = []


class ErrorResponse(BaseModel):
    request_id: str
    error: str
    message: str


class ExportDocxRequest(BaseModel):
    corrected_text: str = Field(min_length=1)
    document_type: DocumentType


class ModelInfoResponse(BaseModel):
    model_id: str
    display_name: str
    max_tokens: int
    temperature: float
    max_input_chars: int
    json_forced: bool


class ModelsResponse(BaseModel):
    models: list[ModelInfoResponse]


class SettingsResponse(BaseModel):
    history_limit: int = 50


class SettingsUpdateRequest(BaseModel):
    history_limit: int = Field(ge=1, le=200)


# === History schemas (§5.1, §7) ===


class HistoryCreateRequest(BaseModel):
    input_text: str = Field(min_length=1, max_length=8000)
    result: ProofreadResponse
    model: str = Field(min_length=1, max_length=50)
    document_type: str = Field(min_length=1, max_length=20)
    memo: str | None = None


class HistoryUpdateRequest(BaseModel):
    memo: str | None = None


class HistoryListItemResponse(BaseModel):
    id: int
    preview: str
    document_type: str
    model: str
    created_at: datetime
    truncated: bool
    memo: str | None = None

    @field_validator("preview")
    @classmethod
    def truncate_preview(cls, v: str) -> str:
        return v[:50]


class HistoryDetailResponse(BaseModel):
    id: int
    input_text: str
    result: ProofreadResponse
    model: str
    document_type: str
    created_at: datetime
    truncated: bool
    memo: str | None = None


class HistoryListResponse(BaseModel):
    items: list[HistoryListItemResponse]
    total: int
