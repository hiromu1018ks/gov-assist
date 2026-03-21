"""Tests for prompt builder service."""

import pytest

from services.prompt_builder import (
    SYSTEM_PROMPT,
    DOCUMENT_TYPE_LABELS,
    OPTION_LABELS,
    build_user_prompt,
    build_prompts,
)
from schemas import DocumentType, ProofreadOptions, ProofreadRequest


class TestSystemPrompt:
    def test_is_non_empty_string(self):
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 0

    def test_contains_role_description(self):
        assert "校正アシスタント" in SYSTEM_PROMPT

    def test_contains_output_rule(self):
        assert "JSON 形式のみで応答" in SYSTEM_PROMPT

    def test_contains_minimal_correction_rule(self):
        assert "必要最小限の修正" in SYSTEM_PROMPT

    def test_contains_no_large_rewrite_rule(self):
        assert "大幅に書き換えることを禁止" in SYSTEM_PROMPT

    def test_contains_granularity_rule(self):
        assert "最小変更単位" in SYSTEM_PROMPT

    def test_contains_50char_limit_rule(self):
        assert "50 文字以内" in SYSTEM_PROMPT

    def test_does_not_contain_position_field(self):
        assert "position" not in SYSTEM_PROMPT


class TestDocumentTypeLabels:
    def test_email_label(self):
        assert DOCUMENT_TYPE_LABELS[DocumentType.EMAIL] == "メール"

    def test_report_label(self):
        assert DOCUMENT_TYPE_LABELS[DocumentType.REPORT] == "報告書"

    def test_official_label(self):
        assert DOCUMENT_TYPE_LABELS[DocumentType.OFFICIAL] == "公文書"

    def test_other_label(self):
        assert DOCUMENT_TYPE_LABELS[DocumentType.OTHER] == "その他"

    def test_covers_all_document_types(self):
        assert set(DOCUMENT_TYPE_LABELS.keys()) == set(DocumentType)


class TestOptionLabels:
    def test_typo_label(self):
        assert OPTION_LABELS["typo"] == "誤字・脱字・変換ミスの検出"

    def test_keigo_label(self):
        assert OPTION_LABELS["keigo"] == "敬語・丁寧語の適切さチェック"

    def test_terminology_label(self):
        assert OPTION_LABELS["terminology"] == "公文書用語・表現への統一（例：「ください」→「くださいますよう」）"

    def test_style_label(self):
        assert OPTION_LABELS["style"] == "文体の統一（です・ます調 / である調）"

    def test_legal_label(self):
        assert OPTION_LABELS["legal"] == "法令・条例用語の確認"

    def test_readability_label(self):
        assert OPTION_LABELS["readability"] == "文章の読みやすさ・論理構成の改善提案"

    def test_covers_all_option_fields(self):
        assert set(OPTION_LABELS.keys()) == set(ProofreadOptions.model_fields)
