"""Tests for response parser service."""

import hashlib
import json
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
        # First call: same prompt retry (fails). Second call: re-prompt (succeeds).
        client.complete.side_effect = [bad, good]

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
