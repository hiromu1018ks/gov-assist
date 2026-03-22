# Task 11: DOCX Export Route Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement POST /api/export/docx endpoint that generates a .docx file from corrected text using python-docx, with paragraph separation and bullet list detection.

**Architecture:** Service function `generate_docx()` in `services/docx_exporter.py` handles all python-docx logic (paragraph splitting, bullet detection). Router in `routers/export.py` delegates to the service and returns binary `Response` with proper Content-Type. No database dependency needed — this is a pure stateless transformation endpoint.

**Tech Stack:** FastAPI, python-docx, Starlette Response (binary), pytest

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `backend/services/docx_exporter.py` | `generate_docx()` — converts corrected text to .docx bytes |
| Create | `backend/routers/export.py` | POST /api/export/docx — validates request, calls service, returns binary |
| Create | `backend/tests/test_docx_exporter.py` | Unit tests for the service (paragraph splitting, bullet detection, empty input) |
| Create | `backend/tests/test_export.py` | Integration tests for the router endpoint |
| Modify | `backend/main.py:148` | Register export router (2 lines after history router) |
| Modify | `backend/requirements.txt` | Add `python-docx>=1.0` dependency |

### Key Interfaces (already implemented, do NOT modify)

**`schemas.py`**
- `ExportDocxRequest(corrected_text: str, document_type: DocumentType)` — Pydantic request model. `corrected_text` has `min_length=1`.
- `DocumentType` enum — EMAIL, REPORT, OFFICIAL, OTHER

**`dependencies.py`**
- `verify_token()` — FastAPI dependency, returns token string on success, raises HTTPException(401) on failure

### Export Service API (to be implemented)

```python
# services/docx_exporter.py
def generate_docx(corrected_text: str, document_type: str) -> bytes:
    """Generate .docx bytes from corrected text.

    Rules (§6.2):
    - Empty lines → paragraph separators
    - Lines starting with "・", "-", or "数字+." → list style
    - Plain text base, no original formatting reproduction

    Returns: .docx file content as bytes
    Raises: ValueError if corrected_text is empty
    """
```

### Router API (to be implemented)

```
POST /api/export/docx
  Auth: Bearer token required
  Request: ExportDocxRequest { corrected_text, document_type }
  Response: .docx binary
    Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
    Content-Disposition: attachment; filename="校正済み文書.docx"
  Errors:
    401 — unauthorized (missing/wrong token)
    422 — validation error (empty corrected_text, invalid document_type)
    500 — internal error (docx generation failure)
```

### Design Decisions (deviations from spec documented)

1. **Filename:** The spec doesn't specify a download filename. Using `"校正済み文書.docx"` as a sensible default. This is cosmetic and the frontend can override via the `Content-Disposition` header.

2. **Error response format:** The spec §5.5 defines JSON error responses with `request_id`. However, the export endpoint doesn't receive a `request_id` in its request body (`ExportDocxRequest` has no `request_id` field). For 500 errors, returning a plain JSON error without `request_id` is acceptable since the export endpoint is a simple stateless transformation with no async pipeline to trace.

---

## Task 1: Add python-docx dependency

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add python-docx to requirements.txt**

Add `python-docx>=1.0` to the end of `backend/requirements.txt`.

- [ ] **Step 2: Install the dependency**

Run: `cd backend && pip install python-docx>=1.0`
Expected: Successfully installs python-docx

- [ ] **Step 3: Verify import works**

Run: `cd backend && python -c "from docx import Document; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "build(backend): add python-docx dependency for .docx export"
```

---

## Task 2: DOCX exporter service

**Files:**
- Create: `backend/services/docx_exporter.py`
- Create: `backend/tests/test_docx_exporter.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_docx_exporter.py
"""Tests for services/docx_exporter.py — .docx generation service (§6.2)."""
import pytest
import re
from docx import Document

from services.docx_exporter import generate_docx


class TestGenerateDocxBasic:
    def test_returns_bytes(self):
        result = generate_docx("テスト", "official")
        assert isinstance(result, bytes)

    def test_valid_docx_structure(self):
        result = generate_docx("テスト", "official")
        # ZIP header (PK\x03\x04) indicates valid docx/zip
        assert result[:4] == b"PK"

    def test_single_paragraph(self):
        result = generate_docx("一つの段落です。", "official")
        doc = Document(bytearray(result))
        assert len(doc.paragraphs) == 1
        assert doc.paragraphs[0].text == "一つの段落です。"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            generate_docx("", "official")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            generate_docx("   \n\n  ", "official")


class TestParagraphSplitting:
    def test_empty_line_creates_new_paragraph(self):
        text = "第一段落\n\n第二段落"
        result = generate_docx(text, "official")
        doc = Document(bytearray(result))
        assert len(doc.paragraphs) == 2
        assert doc.paragraphs[0].text == "第一段落"
        assert doc.paragraphs[1].text == "第二段落"

    def test_multiple_empty_lines_collapsed(self):
        text = "第一段落\n\n\n\n第二段落"
        result = generate_docx(text, "official")
        doc = Document(bytearray(result))
        assert len(doc.paragraphs) == 2

    def test_single_newline_does_not_split(self):
        text = "一行目\n二行目"
        result = generate_docx(text, "official")
        doc = Document(bytearray(result))
        # Single \n within a paragraph should keep it as one paragraph
        assert len(doc.paragraphs) == 1

    def test_trailing_empty_lines_ignored(self):
        text = "本文\n\n\n"
        result = generate_docx(text, "official")
        doc = Document(bytearray(result))
        assert len(doc.paragraphs) == 1
        assert doc.paragraphs[0].text == "本文"


class TestBulletDetection:
    def test_katakana_middle_dot(self):
        text = "・項目1\n\n・項目2"
        result = generate_docx(text, "official")
        doc = Document(bytearray(result))
        assert doc.paragraphs[0].style.name.startswith("List")
        assert doc.paragraphs[1].style.name.startswith("List")

    def test_hyphen_bullet(self):
        text = "- 項目A\n\n- 項目B"
        result = generate_docx(text, "official")
        doc = Document(bytearray(result))
        assert doc.paragraphs[0].style.name.startswith("List")

    def test_numbered_list(self):
        text = "1. 第一項\n\n2. 第二項\n\n3. 第三項"
        result = generate_docx(text, "official")
        doc = Document(bytearray(result))
        for p in doc.paragraphs:
            assert p.style.name.startswith("List")

    def test_mixed_content(self):
        text = "見出し\n\n・箇条書き1\n\n・箇条書き2\n\n本文"
        result = generate_docx(text, "official")
        doc = Document(bytearray(result))
        assert doc.paragraphs[0].text == "見出し"
        assert not doc.paragraphs[0].style.name.startswith("List")
        assert doc.paragraphs[1].style.name.startswith("List")
        assert doc.paragraphs[2].style.name.startswith("List")
        assert doc.paragraphs[3].text == "本文"
        assert not doc.paragraphs[3].style.name.startswith("List")

    def test_bullet_stripped_from_text(self):
        """箇条書き記号は python-docx の List Bullet スタイルが付与するため、元テキストからは除去する"""
        text = "・項目テキスト"
        result = generate_docx(text, "official")
        doc = Document(bytearray(result))
        assert doc.paragraphs[0].text == "項目テキスト"

    def test_numbered_list_stripped(self):
        text = "1. 項目テキスト"
        result = generate_docx(text, "official")
        doc = Document(bytearray(result))
        assert doc.paragraphs[0].text == "項目テキスト"

    def test_double_hyphen_not_bullet(self):
        """「--」は箇条書きとして扱わない（「-」単体のみが箇条書き記号）"""
        text = "-- テスト"
        result = generate_docx(text, "official")
        doc = Document(bytearray(result))
        assert not doc.paragraphs[0].style.name.startswith("List")

    def test_digit_without_dot_not_numbered(self):
        """「数字のみ」（ドットなし）は箇条書きとして扱わない"""
        text = "123 テスト"
        result = generate_docx(text, "official")
        doc = Document(bytearray(result))
        assert not doc.paragraphs[0].style.name.startswith("List")


class TestDocumentTypeHandling:
    def test_all_document_types(self):
        for doc_type in ["email", "report", "official", "other"]:
            result = generate_docx("テスト", doc_type)
            assert isinstance(result, bytes)
            assert result[:4] == b"PK"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_docx_exporter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.docx_exporter'`

- [ ] **Step 3: Write the implementation**

```python
# backend/services/docx_exporter.py
"""Generate .docx from corrected text using python-docx (§6.2)."""
import re
import io

from docx import Document

# Bullet patterns (§6.2): three distinct patterns, each matched independently
# ・ (katakana middle dot): optional space after (Japanese convention: no space)
# - (hyphen): requires space after (to avoid matching "--" or "-text")
# N. (number + dot): requires space after
_BULLET_RE = re.compile(
    r"^(?:(?P<katakana>・)\s*|(?P<hyphen>-)\s+|(?P<number>\d+)\.\s+)(?P<text>.+)$"
)

# python-docx built-in list style names
_LIST_BULLET_STYLE = "List Bullet"
_LIST_NUMBER_STYLE = "List Number"


def _add_paragraph(doc, text: str) -> None:
    """Add a single paragraph to the document, detecting bullet/numbered style."""
    match = _BULLET_RE.match(text)
    if match:
        bullet_text = match.group("text")
        if match.group("number") is not None:
            doc.add_paragraph(bullet_text, style=_LIST_NUMBER_STYLE)
        else:
            # Both katakana dot and hyphen use List Bullet style
            doc.add_paragraph(bullet_text, style=_LIST_BULLET_STYLE)
    else:
        doc.add_paragraph(text)


def generate_docx(corrected_text: str, document_type: str) -> bytes:  # noqa: ARG001
    """Generate .docx bytes from corrected text.

    Rules (§6.2):
    - Empty lines (\\n\\n) → paragraph separators
    - Single newlines within a block → kept in the same paragraph
    - Lines starting with "・", "-", or "数字+." → list style applied
    - Bullet marker is stripped from the paragraph text (the style adds its own marker)
    - Plain text base, no original formatting reproduction

    Args:
        corrected_text: The proofread/corrected text content.
        document_type: Document type identifier (email/report/official/other).
                      Currently unused but kept for future per-type styling.

    Returns:
        .docx file content as bytes.

    Raises:
        ValueError: If corrected_text is empty or whitespace-only.
    """
    if not corrected_text or not corrected_text.strip():
        raise ValueError("corrected_text must not be empty")

    doc = Document()

    # Split on empty lines (paragraph boundaries)
    # A blank line = two consecutive newlines = paragraph separator
    blocks = re.split(r"\n\s*\n", corrected_text.strip())

    for block in blocks:
        # Each block becomes one paragraph.
        # Single \\n within a block is kept as-is in the paragraph text.
        _add_paragraph(doc, block.strip())

    # Write to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_docx_exporter.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/docx_exporter.py backend/tests/test_docx_exporter.py
git commit -m "feat(backend): implement docx exporter service with paragraph/bullet detection"
```

---

## Task 3: Export router

**Files:**
- Create: `backend/routers/export.py`
- Create: `backend/tests/test_export.py`
- Modify: `backend/main.py:148`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_export.py
"""Tests for POST /api/export/docx endpoint (§5.3, §6.2)."""
import pytest
from unittest.mock import patch

AUTH_HEADERS = {"Authorization": "Bearer test-secret-token"}

VALID_REQUEST = {
    "corrected_text": "校正済みテキストです。",
    "document_type": "official",
}


@pytest.fixture
def client(app_client):
    return app_client


class TestAuthAndValidation:
    def test_requires_auth(self, client):
        resp = client.post("/api/export/docx", json=VALID_REQUEST)
        assert resp.status_code == 401

    def test_rejects_wrong_token(self, client):
        resp = client.post(
            "/api/export/docx",
            json=VALID_REQUEST,
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    def test_empty_corrected_text_returns_422(self, client):
        resp = client.post(
            "/api/export/docx",
            json={"corrected_text": "", "document_type": "official"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422

    def test_invalid_document_type_returns_422(self, client):
        resp = client.post(
            "/api/export/docx",
            json={"corrected_text": "テスト", "document_type": "invalid"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422

    def test_missing_document_type_returns_422(self, client):
        resp = client.post(
            "/api/export/docx",
            json={"corrected_text": "テスト"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422


class TestSuccessPath:
    def test_returns_docx_binary(self, client):
        resp = client.post("/api/export/docx", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.content[:4] == b"PK"  # ZIP/docx header

    def test_content_type_is_docx(self, client):
        resp = client.post("/api/export/docx", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in resp.headers["content-type"]

    def test_content_disposition_attachment(self, client):
        resp = client.post("/api/export/docx", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        cd = resp.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert ".docx" in cd

    def test_multiline_text(self, client):
        request = {
            "corrected_text": "第一段落\n\n第二段落\n\n・箇条書き項目",
            "document_type": "email",
        }
        resp = client.post("/api/export/docx", json=request, headers=AUTH_HEADERS)
        assert resp.status_code == 200

    def test_all_document_types(self, client):
        for doc_type in ["email", "report", "official", "other"]:
            request = {"corrected_text": "テスト", "document_type": doc_type}
            resp = client.post("/api/export/docx", json=request, headers=AUTH_HEADERS)
            assert resp.status_code == 200, f"Failed for document_type={doc_type}"


class TestErrorHandling:
    @patch("routers.export.generate_docx")
    def test_service_error_returns_500(self, mock_generate, client):
        mock_generate.side_effect = RuntimeError("docx generation failed")
        resp = client.post("/api/export/docx", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"] == "internal_error"
        assert "内部エラー" in data["message"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_export.py -v`
Expected: FAIL — router not found (404)

- [ ] **Step 3: Write the router implementation**

```python
# backend/routers/export.py
"""POST /api/export/docx — 校正済みテキストの .docx 生成 (§5.3, §6.2)."""
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from starlette.responses import JSONResponse

from dependencies import verify_token
from schemas import ErrorResponse, ExportDocxRequest
from services.docx_exporter import generate_docx

logger = logging.getLogger("govassist")

router = APIRouter(prefix="/api", tags=["export"])

_DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_DOCX_FILENAME = "校正済み文書.docx"


@router.post("/export/docx")
async def export_docx(
    payload: ExportDocxRequest,
    token: str = Depends(verify_token),
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
            "Content-Disposition": f'attachment; filename="{_DOCX_FILENAME}"',
        },
    )
```

- [ ] **Step 4: Register the router in main.py**

Add the following 2 lines after the history router registration (after line 148) in `backend/main.py`:

```python
    from routers.export import router as export_router
    application.include_router(export_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_export.py -v`
Expected: All tests PASS

- [ ] **Step 6: Run all tests to verify no regressions**

Run: `cd backend && pytest -v`
Expected: All tests PASS (existing + new)

- [ ] **Step 7: Commit**

```bash
git add backend/routers/export.py backend/tests/test_export.py backend/main.py
git commit -m "feat(backend): implement DOCX export route with paragraph/bullet detection"
```

---

## Task 4: Verify end-to-end

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

Run: `cd backend && pytest -v`
Expected: All tests PASS

- [ ] **Step 2: Manual smoke test with curl (optional)**

Start the server and test the endpoint:

```bash
cd backend && uvicorn main:app --reload
# In another terminal:
curl -X POST http://localhost:8000/api/export/docx \
  -H "Authorization: Bearer test-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"corrected_text": "テスト段落\n\n・箇条書き1\n・箇条書き2\n\n1. 番号付き1\n2. 番号付き2", "document_type": "official"}' \
  --output test.docx
```

Expected: Downloads `test.docx` that opens correctly in Word/LibreOffice

- [ ] **Step 3: Verify docx content**

Open `test.docx` and confirm:
- 3 paragraphs: "テスト段落", 2 bullet items, 2 numbered items
- Bullet items have bullet style applied
- Numbered items have numbered list style applied
- Text content is correct
