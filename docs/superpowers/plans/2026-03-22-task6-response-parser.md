# Response Parser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the response parser service that validates and extracts structured data from AI JSON responses, with retry logic and fallback extraction, following design spec §4.4 steps 1–4 and §9.2.

**Architecture:** A module (`response_parser.py`) with pure synchronous helper functions for preprocessing, validation, and fallback extraction, plus one async orchestrator (`parse_ai_response()`) that calls `AIClient.complete()` for retries. The orchestrator returns a `ParseResult` dataclass containing `corrected_text`, `summary`, `corrections`, `status`, and `status_reason`. Logging uses the existing `"govassist"` logger with SHA-256 hashed raw responses on parse failure.

**Tech Stack:** Python 3.12, Pydantic (existing schemas), `json`/`re`/`hashlib` (stdlib), `unittest.mock.AsyncMock` for tests

**Design spec reference:** §4.4 (AI response processing flow, steps 1–4), §4.6 (response JSON structure), §5.5 (error codes), §9.2 (logging events)

**Interface contract:**
- **Input:** Raw AI response string from `AIClient.complete()` (Task 4), plus the AI client instance and prompts for retries
- **Output:** `ParseResult` dataclass consumed by the proofread router (Task 9) and diff service (Task 7)
- **Depends on:** `services.ai_client.AIClient`, `services.ai_client.AIClientError`, `schemas.CorrectionItem`, `schemas.ProofreadStatus`, `schemas.StatusReason`

---

## Files

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/services/response_parser.py` | Create | `ParseResult` dataclass, `preprocess_response()`, `validate_parsed_data()`, `_fallback_extract()`, `parse_ai_response()`, `RETRY_PROMPT_TEMPLATE`, logging helpers |
| `backend/tests/test_response_parser.py` | Create | Unit tests for all functions — preprocessing, validation, fallback, retry orchestrator, logging |

No existing files are modified. No new dependencies needed.

---

### Task 1: ParseResult Dataclass & preprocess_response()

**Files:**
- Create: `backend/services/response_parser.py`
- Create: `backend/tests/test_response_parser.py`

- [ ] **Step 1: Write failing tests for ParseResult and preprocess_response()**

Create `backend/tests/test_response_parser.py`:

```python
"""Tests for response parser service."""

import hashlib
import pytest
from unittest.mock import AsyncMock, patch

from services.response_parser import (
    ParseResult,
    preprocess_response,
    validate_parsed_data,
    _fallback_extract,
    RETRY_PROMPT_TEMPLATE,
    parse_ai_response,
)
from services.ai_client import AIClient, AIClientError
from schemas import CorrectionItem, ProofreadStatus, StatusReason


class TestParseResult:
    def test_create_success_result(self):
        result = ParseResult(
            corrected_text="校正済み",
            summary="3件修正",
            corrections=[],
            status=ProofreadStatus.SUCCESS,
            status_reason=None,
        )
        assert result.corrected_text == "校正済み"
        assert result.status == ProofreadStatus.SUCCESS
        assert result.status_reason is None

    def test_create_partial_result(self):
        result = ParseResult(
            corrected_text="一部抽出",
            summary=None,
            corrections=[],
            status=ProofreadStatus.PARTIAL,
            status_reason=StatusReason.PARSE_FALLBACK,
        )
        assert result.status_reason == StatusReason.PARSE_FALLBACK

    def test_create_error_result(self):
        result = ParseResult(
            corrected_text="",
            summary=None,
            corrections=[],
            status=ProofreadStatus.ERROR,
            status_reason=StatusReason.PARSE_FALLBACK,
        )
        assert result.status == ProofreadStatus.ERROR


class TestPreprocessResponse:
    def test_plain_json_unchanged(self):
        text = '{"corrected_text": "校正済みテキスト"}'
        assert preprocess_response(text) == text

    def test_trims_whitespace(self):
        text = '  {"corrected_text": "校正済み"}  \n  '
        assert preprocess_response(text) == '{"corrected_text": "校正済み"}'

    def test_strips_json_code_block(self):
        text = '```json\n{"corrected_text": "校正済み"}\n```'
        assert preprocess_response(text) == '{"corrected_text": "校正済み"}'

    def test_strips_plain_code_block(self):
        text = '```\n{"corrected_text": "校正済み"}\n```'
        assert preprocess_response(text) == '{"corrected_text": "校正済み"}'

    def test_strips_code_block_with_surrounding_text(self):
        text = '以下のJSONです。\n```json\n{"corrected_text": "校正済み"}\n```\n以上です。'
        result = preprocess_response(text)
        assert '"corrected_text"' in result
        assert "以下のJSONです" not in result

    def test_code_block_with_extra_spaces(self):
        text = '```json   \n{"corrected_text": "校正済み"}\n   ```'
        result = preprocess_response(text)
        assert '"corrected_text"' in result

    def test_empty_string(self):
        assert preprocess_response("") == ""

    def test_only_whitespace(self):
        assert preprocess_response("   \n\t  ") == ""

    def test_multiline_json_in_code_block(self):
        text = '```json\n{\n  "corrected_text": "校正済み",\n  "summary": "3件"\n}\n```'
        result = preprocess_response(text)
        assert '"corrected_text"' in result
        assert '"summary"' in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_response_parser.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'services.response_parser'`

- [ ] **Step 3: Implement ParseResult dataclass and preprocess_response()**

Create `backend/services/response_parser.py`:

```python
"""Response parser service for AI proofreading responses."""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field

from schemas import CorrectionItem, ProofreadStatus, StatusReason
from services.ai_client import AIClient, AIClientError

logger = logging.getLogger("govassist")


@dataclass
class ParseResult:
    """Result of parsing an AI response."""
    corrected_text: str
    summary: str | None
    corrections: list[CorrectionItem]
    status: ProofreadStatus
    status_reason: StatusReason | None


# §4.4 ステップ3 再プロンプト（固定文言）
RETRY_PROMPT_TEMPLATE = """あなたの前回の出力はJSONとして解析できませんでした。
以下のJSONを正しいJSON形式に修正して出力してください。
JSON以外のテキスト・説明・コードブロック記法は一切含めないでください。

修正対象：
{previous_response}"""


def preprocess_response(text: str) -> str:
    """Remove markdown code blocks and trim whitespace.

    §4.4 ステップ2: レスポンステキストの前処理
    """
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, flags=re.DOTALL)
    if match:
        text = match.group(1)
    return text.strip()


def validate_parsed_data(data: dict) -> tuple[str, str | None, list[CorrectionItem]]:
    """Validate parsed JSON data with tolerant correction handling.

    §4.4 ステップ4: Pydantic スキーマバリデーション
    """
    raise NotImplementedError


def _fallback_extract(text: str) -> tuple[str, bool]:
    """Fallback extraction when JSON parsing fails.

    §4.4 fallback 抽出
    """
    raise NotImplementedError


async def parse_ai_response(
    *,
    raw_response: str,
    ai_client: AIClient,
    model: str,
    system_prompt: str,
    user_prompt: str,
    request_id: str,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> ParseResult:
    """Parse AI response with retry logic and fallback extraction.

    §4.4 ステップ1–4 + fallback
    """
    raise NotImplementedError
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_response_parser.py -v`

Expected: All 11 tests PASS (3 ParseResult + 8 preprocess_response)

- [ ] **Step 5: Commit**

```bash
git add backend/services/response_parser.py backend/tests/test_response_parser.py
git commit -m "feat(backend): add response parser with ParseResult and preprocess_response()"
```

---

### Task 2: validate_parsed_data() — Tolerant Pydantic Validation

**Files:**
- Modify: `backend/services/response_parser.py` (implement `validate_parsed_data`)
- Modify: `backend/tests/test_response_parser.py` (add `TestValidateParsedData` class)

- [ ] **Step 1: Write failing tests for validate_parsed_data()**

Add to `backend/tests/test_response_parser.py`:

```python
class TestValidateParsedData:
    def test_valid_complete_data(self):
        data = {
            "corrected_text": "校正済みテキスト",
            "summary": "3件の修正を行いました。",
            "corrections": [
                {
                    "original": "修正前",
                    "corrected": "修正後",
                    "reason": "タイポ修正",
                    "category": "誤字脱字",
                }
            ],
        }
        text, summary, corrections = validate_parsed_data(data)
        assert text == "校正済みテキスト"
        assert summary == "3件の修正を行いました。"
        assert len(corrections) == 1
        assert corrections[0].original == "修正前"
        assert corrections[0].corrected == "修正後"
        assert corrections[0].reason == "タイポ修正"
        assert corrections[0].category == "誤字脱字"
        assert corrections[0].diff_matched is False

    def test_missing_summary_defaults_to_none(self):
        data = {
            "corrected_text": "校正済み",
            "corrections": [],
        }
        text, summary, corrections = validate_parsed_data(data)
        assert summary is None

    def test_null_summary_defaults_to_none(self):
        data = {
            "corrected_text": "校正済み",
            "summary": None,
            "corrections": [],
        }
        text, summary, corrections = validate_parsed_data(data)
        assert summary is None

    def test_missing_corrections_defaults_to_empty_list(self):
        data = {
            "corrected_text": "校正済み",
            "summary": "テスト",
        }
        text, summary, corrections = validate_parsed_data(data)
        assert corrections == []

    def test_missing_corrected_text_defaults_to_empty_string(self):
        data = {}
        text, summary, corrections = validate_parsed_data(data)
        assert text == ""

    def test_correction_missing_required_field_is_dropped(self):
        data = {
            "corrected_text": "校正済み",
            "corrections": [
                {
                    "original": "修正前",
                    "corrected": "修正後",
                    "reason": "理由",
                    # "category" missing
                }
            ],
        }
        text, summary, corrections = validate_parsed_data(data)
        assert len(corrections) == 0

    def test_correction_with_non_string_field_is_dropped(self):
        data = {
            "corrected_text": "校正済み",
            "corrections": [
                {
                    "original": 123,
                    "corrected": "修正後",
                    "reason": "理由",
                    "category": "誤字脱字",
                }
            ],
        }
        text, summary, corrections = validate_parsed_data(data)
        assert len(corrections) == 0

    def test_correction_original_over_50_chars_is_dropped(self):
        data = {
            "corrected_text": "校正済み",
            "corrections": [
                {
                    "original": "あ" * 51,
                    "corrected": "修正後",
                    "reason": "理由",
                    "category": "誤字脱字",
                }
            ],
        }
        text, summary, corrections = validate_parsed_data(data)
        assert len(corrections) == 0

    def test_correction_corrected_over_50_chars_is_dropped(self):
        data = {
            "corrected_text": "校正済み",
            "corrections": [
                {
                    "original": "修正前",
                    "corrected": "い" * 51,
                    "reason": "理由",
                    "category": "誤字脱字",
                }
            ],
        }
        text, summary, corrections = validate_parsed_data(data)
        assert len(corrections) == 0

    def test_correction_exactly_50_chars_is_accepted(self):
        data = {
            "corrected_text": "校正済み",
            "corrections": [
                {
                    "original": "あ" * 50,
                    "corrected": "い" * 50,
                    "reason": "理由",
                    "category": "誤字脱字",
                }
            ],
        }
        text, summary, corrections = validate_parsed_data(data)
        assert len(corrections) == 1

    def test_mix_of_valid_and_invalid_corrections(self):
        data = {
            "corrected_text": "校正済み",
            "corrections": [
                {
                    "original": "修正前1",
                    "corrected": "修正後1",
                    "reason": "理由1",
                    "category": "誤字脱字",
                },
                {
                    "original": "修正前2",
                    # "corrected" missing
                    "reason": "理由2",
                    "category": "敬語",
                },
                {
                    "original": "修正前3",
                    "corrected": "修正後3",
                    "reason": "理由3",
                    "category": "用語",
                },
            ],
        }
        text, summary, corrections = validate_parsed_data(data)
        assert len(corrections) == 2
        assert corrections[0].original == "修正前1"
        assert corrections[1].original == "修正前3"

    def test_all_corrections_invalid_returns_empty_list(self):
        data = {
            "corrected_text": "校正済み",
            "corrections": [
                {"original": "x" * 51, "corrected": "y", "reason": "r", "category": "c"},
                {"not_valid": True},
                42,
            ],
        }
        text, summary, corrections = validate_parsed_data(data)
        assert corrections == []

    def test_corrections_field_not_list_returns_empty_list(self):
        data = {
            "corrected_text": "校正済み",
            "corrections": "not a list",
        }
        text, summary, corrections = validate_parsed_data(data)
        assert corrections == []

    def test_non_dict_items_in_corrections_list_are_skipped(self):
        data = {
            "corrected_text": "校正済み",
            "corrections": [
                "string item",
                42,
                None,
                {"original": "OK", "corrected": "OK", "reason": "OK", "category": "OK"},
            ],
        }
        text, summary, corrections = validate_parsed_data(data)
        assert len(corrections) == 1

    def test_summary_non_string_defaults_to_none(self):
        data = {
            "corrected_text": "校正済み",
            "summary": 123,
        }
        text, summary, corrections = validate_parsed_data(data)
        assert summary is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_response_parser.py::TestValidateParsedData -v`

Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: Implement validate_parsed_data()**

Replace the stub in `backend/services/response_parser.py`:

```python
def validate_parsed_data(data: dict) -> tuple[str, str | None, list[CorrectionItem]]:
    """Validate parsed JSON data with tolerant correction handling.

    §4.4 ステップ4: Pydantic スキーマバリデーション

    - Missing summary → None
    - Missing corrections → []
    - Individual invalid corrections → dropped (not the whole response)
    - All corrections invalid → []
    """
    corrected_text = str(data.get("corrected_text", ""))
    summary = data.get("summary") if isinstance(data.get("summary"), str) else None

    raw_corrections = data.get("corrections", [])
    if not isinstance(raw_corrections, list):
        corrections = []
    else:
        corrections = _validate_corrections(raw_corrections)

    return corrected_text, summary, corrections


def _validate_corrections(raw_corrections: list) -> list[CorrectionItem]:
    """Validate individual correction entries, dropping invalid ones."""
    corrections = []
    for item in raw_corrections:
        if not isinstance(item, dict):
            continue
        try:
            original = item["original"]
            corrected = item["corrected"]
            reason = item["reason"]
            category = item["category"]
        except (KeyError, TypeError):
            continue

        if not all(isinstance(v, str) for v in (original, corrected, reason, category)):
            continue
        if len(original) > 50 or len(corrected) > 50:
            continue

        corrections.append(CorrectionItem(
            original=original,
            corrected=corrected,
            reason=reason,
            category=category,
            diff_matched=False,
        ))
    return corrections
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_response_parser.py::TestValidateParsedData -v`

Expected: All 14 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/response_parser.py backend/tests/test_response_parser.py
git commit -m "feat(backend): implement validate_parsed_data() with tolerant correction handling"
```

---

### Task 3: _fallback_extract() — Regex & Plain Text Fallback

**Files:**
- Modify: `backend/services/response_parser.py` (implement `_fallback_extract`)
- Modify: `backend/tests/test_response_parser.py` (add `TestFallbackExtract` class)

- [ ] **Step 1: Write failing tests for _fallback_extract()**

Add to `backend/tests/test_response_parser.py`:

```python
class TestFallbackExtract:
    def test_regex_extracts_corrected_text_field(self):
        text = '{"corrected_text": "校正済みテキストです", "summary": "3件修正"}'
        extracted, success = _fallback_extract(text)
        assert success is True
        assert extracted == "校正済みテキストです"

    def test_regex_extracts_with_whitespace_around_colon(self):
        text = '{"corrected_text"  :  "校正済みテキスト"}'
        extracted, success = _fallback_extract(text)
        assert success is True
        assert extracted == "校正済みテキスト"

    def test_regex_extracts_multiline_value(self):
        text = '{"corrected_text": "第1行\n第2行\n第3行"}'
        extracted, success = _fallback_extract(text)
        assert success is True
        assert "第1行" in extracted
        assert "第3行" in extracted

    def test_no_corrected_text_finds_longest_string(self):
        text = '{"other_field": "短い", "content": "これは長いテキストです。校正結果として抽出されるべき内容です。"}'
        extracted, success = _fallback_extract(text)
        assert success is True
        assert "長いテキスト" in extracted

    def test_no_strings_at_all_strips_json_syntax(self):
        text = '{ "key": value, "arr": [1, 2, 3] }'
        extracted, success = _fallback_extract(text)
        assert success is True

    def test_empty_string_returns_failure(self):
        extracted, success = _fallback_extract("")
        assert success is False
        assert extracted == ""

    def test_very_short_text_after_stripping_returns_failure(self):
        extracted, success = _fallback_extract("abc")
        assert success is False

    def test_plain_text_without_json_structure(self):
        text = "これはAIが返したテキストです。JSONではないですが内容があります。"
        extracted, success = _fallback_extract(text)
        assert success is True
        assert len(extracted) > 0

    def test_corrected_text_with_empty_value(self):
        text = '{"corrected_text": "", "summary": "テスト"}'
        extracted, success = _fallback_extract(text)
        # Empty string from regex is still a match — but should it be?
        # Yes: regex matched, even if value is empty
        assert success is True
        assert extracted == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_response_parser.py::TestFallbackExtract -v`

Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: Implement _fallback_extract()**

Replace the stub in `backend/services/response_parser.py`:

```python
def _fallback_extract(text: str) -> tuple[str, bool]:
    """Fallback extraction when JSON parsing fails completely.

    §4.4 fallback 抽出:
    1. Regex: "corrected_text"\\s*:\\s*"(.*?)" でフィールドを抽出
    2. JSON 構造を除いた平文テキスト部分を表示
    3. 上記すべて失敗 → 空文字、失敗
    """
    # Step 1: Regex extraction of corrected_text field
    match = re.search(r'"corrected_text"\s*:\s*"(.*?)"', text, flags=re.DOTALL)
    if match:
        return match.group(1), True

    # Step 2a: Find all string values, return the longest one
    strings = re.findall(r'"((?:[^"\\]|\\.)*)"', text)
    if strings:
        longest = max(strings, key=len)
        if len(longest) > 10:
            return longest, True

    # Step 2b: Strip JSON structure characters, return remaining text
    cleaned = re.sub(r'[\{\}\[\]"\'\\:,]', ' ', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if cleaned and len(cleaned) > 5:
        return cleaned, True

    # Step 3: Complete failure
    return "", False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_response_parser.py::TestFallbackExtract -v`

Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/response_parser.py backend/tests/test_response_parser.py
git commit -m "feat(backend): implement _fallback_extract() with regex and plain text fallback"
```

---

### Task 4: RETRY_PROMPT_TEMPLATE Verification

**Files:**
- Modify: `backend/tests/test_response_parser.py` (add `TestRetryPrompt` class)

- [ ] **Step 1: Write tests for RETRY_PROMPT_TEMPLATE**

Add to `backend/tests/test_response_parser.py`:

```python
class TestRetryPrompt:
    def test_contains_fixed_instruction(self):
        assert "JSONとして解析できませんでした" in RETRY_PROMPT_TEMPLATE

    def test_instructs_no_code_blocks(self):
        assert "コードブロック記法は一切含めない" in RETRY_PROMPT_TEMPLATE

    def test_has_placeholder_for_previous_response(self):
        assert "{previous_response}" in RETRY_PROMPT_TEMPLATE

    def test_format_with_previous_response(self):
        result = RETRY_PROMPT_TEMPLATE.format(previous_response="broken json")
        assert "broken json" in result
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_response_parser.py::TestRetryPrompt -v`

Expected: All 4 tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_response_parser.py
git commit -m "test(backend): add RETRY_PROMPT_TEMPLATE verification tests"
```

---

### Task 5: parse_ai_response() — Async Orchestrator with Retry Logic

**Files:**
- Modify: `backend/services/response_parser.py` (implement `parse_ai_response`)
- Modify: `backend/tests/test_response_parser.py` (add `TestParseAIResponse` class)

- [ ] **Step 1: Write failing tests for parse_ai_response()**

Add to `backend/tests/test_response_parser.py`:

```python
class TestParseAIResponse:
    def _make_mock_client(self):
        return AsyncMock(spec=AIClient)

    def _valid_json_response(self, **overrides):
        data = {
            "corrected_text": "校正済みテキスト",
            "summary": "3件修正",
            "corrections": [
                {
                    "original": "修正前",
                    "corrected": "修正後",
                    "reason": "タイポ",
                    "category": "誤字脱字",
                }
            ],
        }
        data.update(overrides)
        return json.dumps(data, ensure_ascii=False)

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        client = self._make_mock_client()
        raw = self._valid_json_response()

        result = await parse_ai_response(
            raw_response=raw,
            ai_client=client,
            model="kimi-k2.5",
            system_prompt="system",
            user_prompt="user",
            request_id="req-001",
        )

        assert result.status == ProofreadStatus.SUCCESS
        assert result.status_reason is None
        assert result.corrected_text == "校正済みテキスト"
        assert result.summary == "3件修正"
        assert len(result.corrections) == 1
        # AI client should NOT be called on success
        client.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_retry_same_prompt_on_first_failure(self):
        client = self._make_mock_client()
        bad = "これはJSONではありません"
        good = self._valid_json_response()
        client.complete.return_value = good

        result = await parse_ai_response(
            raw_response=bad,
            ai_client=client,
            model="kimi-k2.5",
            system_prompt="system",
            user_prompt="user",
            request_id="req-002",
        )

        assert result.status == ProofreadStatus.SUCCESS
        # Should have called complete once (retry with same prompt)
        assert client.complete.call_count == 1
        call_kwargs = client.complete.call_args.kwargs
        assert call_kwargs["user_prompt"] == "user"
        assert call_kwargs["system_prompt"] == "system"

    @pytest.mark.asyncio
    async def test_re_prompt_on_second_failure(self):
        client = self._make_mock_client()
        bad = "broken"
        good = self._valid_json_response()
        # First call: same prompt retry. Second call: re-prompt.
        client.complete.side_effect = [good, good]

        result = await parse_ai_response(
            raw_response=bad,
            ai_client=client,
            model="kimi-k2.5",
            system_prompt="system",
            user_prompt="user",
            request_id="req-003",
        )

        assert result.status == ProofreadStatus.SUCCESS
        assert client.complete.call_count == 2
        # Second call should use re-prompt, not original user_prompt
        second_call_kwargs = client.complete.call_args_list[1].kwargs
        assert "JSONとして解析できませんでした" in second_call_kwargs["user_prompt"]
        assert "broken" in second_call_kwargs["user_prompt"]

    @pytest.mark.asyncio
    async def test_fallback_regex_on_all_failures(self):
        client = self._make_mock_client()
        bad = '{"corrected_text": "regex抽出テスト", bad json'
        # Retries also fail
        client.complete.return_value = bad

        result = await parse_ai_response(
            raw_response=bad,
            ai_client=client,
            model="kimi-k2.5",
            system_prompt="system",
            user_prompt="user",
            request_id="req-004",
        )

        assert result.status == ProofreadStatus.PARTIAL
        assert result.status_reason == StatusReason.PARSE_FALLBACK
        assert result.corrected_text == "regex抽出テスト"
        assert result.summary is None
        assert result.corrections == []

    @pytest.mark.asyncio
    async def test_fallback_plain_text_on_all_failures(self):
        client = self._make_mock_client()
        bad = "これはAIが返したテキストです。JSONではありません。"
        client.complete.return_value = bad

        result = await parse_ai_response(
            raw_response=bad,
            ai_client=client,
            model="kimi-k2.5",
            system_prompt="system",
            user_prompt="user",
            request_id="req-005",
        )

        assert result.status == ProofreadStatus.PARTIAL
        assert result.status_reason == StatusReason.PARSE_FALLBACK
        assert len(result.corrected_text) > 0

    @pytest.mark.asyncio
    async def test_error_status_on_complete_failure(self):
        client = self._make_mock_client()
        bad = "abc"
        client.complete.return_value = bad

        result = await parse_ai_response(
            raw_response=bad,
            ai_client=client,
            model="kimi-k2.5",
            system_prompt="system",
            user_prompt="user",
            request_id="req-006",
        )

        assert result.status == ProofreadStatus.ERROR
        assert result.status_reason == StatusReason.PARSE_FALLBACK
        assert result.corrected_text == ""

    @pytest.mark.asyncio
    async def test_ai_client_error_during_retry_falls_to_fallback(self):
        client = self._make_mock_client()
        bad = '{"corrected_text": "抽出されるテキスト", bad json'
        client.complete.side_effect = AIClientError("ai_timeout", "timeout")

        result = await parse_ai_response(
            raw_response=bad,
            ai_client=client,
            model="kimi-k2.5",
            system_prompt="system",
            user_prompt="user",
            request_id="req-007",
        )

        # Should fall through to fallback, not crash
        assert result.status in (ProofreadStatus.PARTIAL, ProofreadStatus.ERROR)

    @pytest.mark.asyncio
    async def test_code_block_wrapped_json_parsed_successfully(self):
        client = self._make_mock_client()
        raw = '```json\n' + self._valid_json_response() + '\n```'

        result = await parse_ai_response(
            raw_response=raw,
            ai_client=client,
            model="kimi-k2.5",
            system_prompt="system",
            user_prompt="user",
            request_id="req-008",
        )

        assert result.status == ProofreadStatus.SUCCESS
        assert result.corrected_text == "校正済みテキスト"

    @pytest.mark.asyncio
    async def test_invalid_corrections_dropped_but_result_still_success(self):
        client = self._make_mock_client()
        raw = json.dumps({
            "corrected_text": "校正済み",
            "summary": "テスト",
            "corrections": [
                {"original": "x" * 51, "corrected": "y", "reason": "r", "category": "c"},
                {"original": "OK", "corrected": "OK", "reason": "OK", "category": "OK"},
            ],
        }, ensure_ascii=False)

        result = await parse_ai_response(
            raw_response=raw,
            ai_client=client,
            model="kimi-k2.5",
            system_prompt="system",
            user_prompt="user",
            request_id="req-009",
        )

        assert result.status == ProofreadStatus.SUCCESS
        assert len(result.corrections) == 1
        assert result.corrections[0].original == "OK"

    @pytest.mark.asyncio
    async def test_logging_on_parse_failure(self):
        client = self._make_mock_client()
        bad = "not json at all"
        client.complete.return_value = bad

        with patch("services.response_parser.logger") as mock_logger:
            result = await parse_ai_response(
                raw_response=bad,
                ai_client=client,
                model="kimi-k2.5",
                system_prompt="system",
                user_prompt="user",
                request_id="req-010",
            )

        # Should have logged parse failures (3 attempts total)
        warning_calls = [
            c for c in mock_logger.warning.call_args_list
        ]
        assert len(warning_calls) >= 1

    @pytest.mark.asyncio
    async def test_passes_model_and_tokens_to_ai_client(self):
        client = self._make_mock_client()
        bad = "broken"
        good = self._valid_json_response()
        client.complete.return_value = good

        result = await parse_ai_response(
            raw_response=bad,
            ai_client=client,
            model="kimi-k2.5",
            system_prompt="system",
            user_prompt="user",
            request_id="req-011",
            max_tokens=2048,
            temperature=0.5,
        )

        call_kwargs = client.complete.call_args.kwargs
        assert call_kwargs["model"] == "kimi-k2.5"
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["request_id"] == "req-011"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_response_parser.py::TestParseAIResponse -v`

Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: Implement parse_ai_response() and logging helper**

Add the logging helper and replace the stub in `backend/services/response_parser.py`:

```python
def _log_parse_failure(request_id: str, model: str, attempt: int, raw_response: str) -> None:
    """Log a JSON parse failure with SHA-256 hash of the response.

    §9.2: JSON パース失敗時のログ記録
    ログには生テキストではなく SHA-256 ハッシュを記録する
    """
    response_hash = hashlib.sha256(raw_response.encode()).hexdigest()
    logger.warning(
        "JSON parse failed: request_id=%s model=%s attempt=%d sha256=%s length=%d",
        request_id, model, attempt, response_hash, len(raw_response),
    )


async def parse_ai_response(
    *,
    raw_response: str,
    ai_client: AIClient,
    model: str,
    system_prompt: str,
    user_prompt: str,
    request_id: str,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> ParseResult:
    """Parse AI response with retry logic and fallback extraction.

    §4.4 ステップ1–4 + fallback

    Retry strategy (max 3 attempts total):
    - Attempt 1: Parse initial response
    - Attempt 2 (on failure): Retry with same prompt
    - Attempt 3 (on failure): Re-prompt with fixed text asking AI to fix JSON
    - All failures: Fallback extraction (regex → plain text → error)
    """
    last_response = raw_response

    for attempt in range(3):
        # Step 2: Preprocess
        preprocessed = preprocess_response(last_response)

        # Step 3: Parse JSON
        try:
            data = json.loads(preprocessed)
        except json.JSONDecodeError:
            _log_parse_failure(request_id, model, attempt + 1, last_response)

            if attempt >= 2:
                break

            # Attempt retry via AI client
            try:
                if attempt == 0:
                    # Retry with same prompt
                    last_response = await ai_client.complete(
                        model=model,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        request_id=request_id,
                    )
                else:
                    # Re-prompt with fixed text
                    retry_prompt = RETRY_PROMPT_TEMPLATE.format(
                        previous_response=last_response,
                    )
                    last_response = await ai_client.complete(
                        model=model,
                        system_prompt=system_prompt,
                        user_prompt=retry_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        request_id=request_id,
                    )
            except AIClientError:
                # AI client error during retry — fall through to fallback
                break
            continue

        # Step 4: Validate parsed data
        corrected_text, summary, corrections = validate_parsed_data(data)
        return ParseResult(
            corrected_text=corrected_text,
            summary=summary,
            corrections=corrections,
            status=ProofreadStatus.SUCCESS,
            status_reason=None,
        )

    # Fallback extraction
    logger.warning(
        "Fallback extraction triggered: request_id=%s",
        request_id,
    )
    extracted, success = _fallback_extract(last_response)

    if success and extracted:
        return ParseResult(
            corrected_text=extracted,
            summary=None,
            corrections=[],
            status=ProofreadStatus.PARTIAL,
            status_reason=StatusReason.PARSE_FALLBACK,
        )

    return ParseResult(
        corrected_text="",
        summary=None,
        corrections=[],
        status=ProofreadStatus.ERROR,
        status_reason=StatusReason.PARSE_FALLBACK,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_response_parser.py::TestParseAIResponse -v`

Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/response_parser.py backend/tests/test_response_parser.py
git commit -m "feat(backend): implement parse_ai_response() with retry logic and fallback"
```

---

### Task 6: Full Test Suite Verification

**Files:** None (verification only)

- [ ] **Step 1: Run new response parser tests**

Run: `cd backend && python -m pytest tests/test_response_parser.py -v`

Expected: All tests PASS (3 ParseResult + 8 preprocess + 14 validate + 9 fallback + 4 retry_prompt + 12 parse_ai_response = 50 tests)

- [ ] **Step 2: Run entire test suite to check for regressions**

Run: `cd backend && python -m pytest -v`

Expected: All tests PASS (existing + 50 new response parser tests)

- [ ] **Step 3: Final commit (only if fixes were needed)**

```bash
git add backend/services/response_parser.py backend/tests/test_response_parser.py
git commit -m "fix: resolve test regressions from response parser addition"
```

Skip this step if no fixes were needed.
