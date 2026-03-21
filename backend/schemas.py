from enum import Enum
from pydantic import BaseModel, Field


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
