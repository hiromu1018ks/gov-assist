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
