"""Tests for prompt builder service."""

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


class TestBuildUserPrompt:
    def _default_options(self, **overrides) -> ProofreadOptions:
        return ProofreadOptions(**overrides)

    def test_includes_document_type_label(self):
        prompt = build_user_prompt(
            document_type=DocumentType.OFFICIAL,
            options=self._default_options(),
            text="テスト文書",
        )
        assert "文書種別：公文書" in prompt

    def test_includes_enabled_options(self):
        prompt = build_user_prompt(
            document_type=DocumentType.EMAIL,
            options=self._default_options(typo=True, keigo=True, legal=False),
            text="テスト",
        )
        assert "誤字・脱字・変換ミスの検出" in prompt
        assert "敬語・丁寧語の適切さチェック" in prompt
        assert "法令・条例用語の確認" not in prompt

    def test_excludes_disabled_options(self):
        prompt = build_user_prompt(
            document_type=DocumentType.EMAIL,
            options=self._default_options(typo=False, keigo=False),
            text="テスト",
        )
        assert "誤字・脱字" not in prompt
        assert "敬語・丁寧語の適切さチェック" not in prompt

    def test_includes_input_text(self):
        prompt = build_user_prompt(
            document_type=DocumentType.EMAIL,
            options=self._default_options(),
            text="これはテスト文書です。",
        )
        assert "これはテスト文書です。" in prompt

    def test_includes_json_template(self):
        prompt = build_user_prompt(
            document_type=DocumentType.EMAIL,
            options=self._default_options(),
            text="テスト",
        )
        assert "corrected_text" in prompt
        assert "summary" in prompt
        assert "corrections" in prompt
        assert "original" in prompt
        assert "corrected" in prompt
        assert "reason" in prompt
        assert "category" in prompt

    def test_json_template_does_not_include_position(self):
        prompt = build_user_prompt(
            document_type=DocumentType.EMAIL,
            options=self._default_options(),
            text="テスト",
        )
        # position は JSON テンプレートに含めない（§4.3 注記）
        assert '"position"' not in prompt

    def test_all_document_types(self):
        for doc_type in DocumentType:
            prompt = build_user_prompt(
                document_type=doc_type,
                options=self._default_options(),
                text="テスト",
            )
            expected_label = DOCUMENT_TYPE_LABELS[doc_type]
            assert f"文書種別：{expected_label}" in prompt

    def test_all_options_disabled(self):
        prompt = build_user_prompt(
            document_type=DocumentType.OTHER,
            options=self._default_options(
                typo=False, keigo=False, terminology=False,
                style=False, legal=False, readability=False,
            ),
            text="テスト",
        )
        assert "チェック項目：" in prompt
        # No option labels should appear
        for label in OPTION_LABELS.values():
            assert label not in prompt

    def test_all_options_enabled(self):
        prompt = build_user_prompt(
            document_type=DocumentType.OFFICIAL,
            options=self._default_options(
                typo=True, keigo=True, terminology=True,
                style=True, legal=True, readability=True,
            ),
            text="テスト",
        )
        for label in OPTION_LABELS.values():
            assert label in prompt

    def test_options_are_separated_by_line(self):
        """有効オプションが改行区切りで出力されること"""
        prompt = build_user_prompt(
            document_type=DocumentType.EMAIL,
            options=self._default_options(typo=True, keigo=True),
            text="テスト",
        )
        lines = prompt.split("\n")
        typo_found = keigo_found = False
        for line in lines:
            if "誤字・脱字" in line:
                typo_found = True
            if "敬語" in line:
                keigo_found = True
        assert typo_found and keigo_found

    def test_multiline_input_text(self):
        prompt = build_user_prompt(
            document_type=DocumentType.EMAIL,
            options=self._default_options(),
            text="第1行\n第2行\n第3行",
        )
        assert "第1行\n第2行\n第3行" in prompt


class TestBuildPrompts:
    def test_returns_system_and_user_prompts(self):
        request = ProofreadRequest(
            request_id="test-123",
            text="テスト文書",
            document_type=DocumentType.OFFICIAL,
        )
        system, user = build_prompts(request)
        assert isinstance(system, str)
        assert isinstance(user, str)
        assert len(system) > 0
        assert len(user) > 0

    def test_system_prompt_matches_constant(self):
        request = ProofreadRequest(
            request_id="test-123",
            text="テスト",
            document_type=DocumentType.EMAIL,
        )
        system, _ = build_prompts(request)
        assert system == SYSTEM_PROMPT

    def test_user_prompt_matches_build_user_prompt(self):
        request = ProofreadRequest(
            request_id="test-123",
            text="テスト文書",
            document_type=DocumentType.REPORT,
            options=ProofreadOptions(typo=True, legal=True),
        )
        _, user = build_prompts(request)
        expected = build_user_prompt(
            document_type=DocumentType.REPORT,
            options=ProofreadOptions(typo=True, legal=True),
            text="テスト文書",
        )
        assert user == expected

    def test_uses_request_defaults(self):
        """ProofreadRequest のデフォルトオプションが正しく渡されること"""
        request = ProofreadRequest(
            request_id="test-123",
            text="テスト",
            document_type=DocumentType.OTHER,
        )
        _, user = build_prompts(request)
        # デフォルトでは typo=True, legal=False
        assert "誤字・脱字" in user
        assert "法令・条例" not in user
