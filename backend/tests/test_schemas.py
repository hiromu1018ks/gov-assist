import pytest
from schemas import (
    DocumentType,
    ProofreadOptions,
    ProofreadRequest,
    CorrectionItem,
    DiffBlock,
    DiffType,
    ProofreadResponse,
    ProofreadStatus,
    StatusReason,
    ErrorResponse,
    ExportDocxRequest,
)


class TestDocumentType:
    def test_valid_types(self):
        assert DocumentType.EMAIL == "email"
        assert DocumentType.REPORT == "report"
        assert DocumentType.OFFICIAL == "official"
        assert DocumentType.OTHER == "other"

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            DocumentType("invalid")


class TestProofreadOptions:
    def test_all_true(self):
        opts = ProofreadOptions(
            typo=True, keigo=True, terminology=True,
            style=True, legal=True, readability=True,
        )
        assert opts.typo is True
        assert opts.legal is True

    def test_defaults(self):
        opts = ProofreadOptions()
        assert opts.typo is True
        assert opts.keigo is True
        assert opts.terminology is True
        assert opts.style is True
        assert opts.legal is False
        assert opts.readability is True


class TestProofreadRequest:
    def test_valid_request(self):
        req = ProofreadRequest(
            request_id="test-uuid",
            text="テスト文章",
            document_type=DocumentType.OFFICIAL,
            model="kimi-k2.5",
        )
        assert req.text == "テスト文章"
        assert req.document_type == DocumentType.OFFICIAL
        assert req.model == "kimi-k2.5"
        assert req.request_id == "test-uuid"

    def test_default_model(self):
        req = ProofreadRequest(
            request_id="test-uuid",
            text="テスト",
            document_type=DocumentType.EMAIL,
        )
        assert req.model == "kimi-k2.5"

    def test_text_max_length(self):
        long_text = "あ" * 8001
        with pytest.raises(ValueError):
            ProofreadRequest(
                request_id="test-uuid",
                text=long_text,
                document_type=DocumentType.EMAIL,
            )

    def test_text_empty_raises(self):
        with pytest.raises(ValueError):
            ProofreadRequest(
                request_id="test-uuid",
                text="",
                document_type=DocumentType.EMAIL,
            )


class TestProofreadResponse:
    def test_success_response(self):
        resp = ProofreadResponse(
            request_id="test-uuid",
            status=ProofreadStatus.SUCCESS,
            corrected_text="校正済みテキスト",
            summary="3件の修正を行いました。",
            corrections=[],
            diffs=[],
        )
        assert resp.status == "success"
        assert resp.status_reason is None
        assert resp.warnings == []

    def test_partial_response(self):
        resp = ProofreadResponse(
            request_id="test-uuid",
            status=ProofreadStatus.PARTIAL,
            status_reason=StatusReason.DIFF_TIMEOUT,
            corrected_text="テキスト",
        )
        assert resp.status == "partial"
        assert resp.status_reason == "diff_timeout"

    def test_error_response(self):
        resp = ProofreadResponse(
            request_id="test-uuid",
            status=ProofreadStatus.ERROR,
            status_reason=StatusReason.PARSE_FALLBACK,
            corrected_text="",
        )
        assert resp.status == "error"
        assert resp.status_reason == "parse_fallback"

    def test_large_rewrite_warning(self):
        resp = ProofreadResponse(
            request_id="test-uuid",
            status=ProofreadStatus.SUCCESS,
            corrected_text="テキスト",
            warnings=["large_rewrite"],
        )
        assert resp.warnings == ["large_rewrite"]


class TestCorrectionItem:
    def test_valid_correction(self):
        item = CorrectionItem(
            original="修正前",
            corrected="修正後",
            reason="誤字のため",
            category="誤字脱字",
            diff_matched=True,
        )
        assert item.diff_matched is True

    def test_defaults(self):
        item = CorrectionItem(
            original="修正前",
            corrected="修正後",
            reason="理由",
            category="用語",
        )
        assert item.diff_matched is False


class TestDiffBlock:
    def test_equal_block(self):
        block = DiffBlock(
            type=DiffType.EQUAL,
            text="テキスト",
            start=0,
        )
        assert block.position is None
        assert block.reason is None

    def test_insert_block(self):
        block = DiffBlock(
            type=DiffType.INSERT,
            text="追加",
            start=5,
            position="after",
            reason="理由",
        )
        assert block.position == "after"

    def test_delete_block(self):
        block = DiffBlock(
            type=DiffType.DELETE,
            text="削除",
            start=5,
            reason="理由",
        )
        assert block.position is None

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            DiffBlock(
                type="invalid",
                text="テキスト",
                start=0,
            )


class TestErrorResponse:
    def test_error_response(self):
        err = ErrorResponse(
            request_id="test-uuid",
            error="text_too_long",
            message="入力文字数が上限を超えています。",
        )
        assert err.error == "text_too_long"


class TestExportDocxRequest:
    def test_valid_request(self):
        req = ExportDocxRequest(
            corrected_text="校正済みテキスト",
            document_type=DocumentType.OFFICIAL,
        )
        assert req.corrected_text == "校正済みテキスト"

    def test_empty_text_raises(self):
        with pytest.raises(ValueError):
            ExportDocxRequest(
                corrected_text="",
                document_type=DocumentType.OFFICIAL,
            )


class TestModelInfoResponse:
    def test_model_info_response_valid(self):
        from schemas import ModelInfoResponse
        m = ModelInfoResponse(
            model_id="kimi-k2.5",
            display_name="Kimi K2.5",
            max_tokens=4096,
            temperature=0.3,
            max_input_chars=8000,
            json_forced=True,
        )
        assert m.model_id == "kimi-k2.5"
        assert m.display_name == "Kimi K2.5"

    def test_models_response_list(self):
        from schemas import ModelInfoResponse, ModelsResponse
        models = ModelsResponse(models=[
            ModelInfoResponse(
                model_id="kimi-k2.5",
                display_name="Kimi K2.5",
                max_tokens=4096,
                temperature=0.3,
                max_input_chars=8000,
                json_forced=True,
            )
        ])
        assert len(models.models) == 1
        assert models.models[0].model_id == "kimi-k2.5"


class TestSettingsResponse:
    def test_settings_response_valid(self):
        from schemas import SettingsResponse
        s = SettingsResponse(history_limit=50)
        assert s.history_limit == 50

    def test_settings_response_defaults(self):
        from schemas import SettingsResponse
        s = SettingsResponse()
        assert s.history_limit == 50


class TestSettingsUpdateRequest:
    def test_settings_update_valid(self):
        from schemas import SettingsUpdateRequest
        s = SettingsUpdateRequest(history_limit=100)
        assert s.history_limit == 100

    def test_settings_update_below_minimum(self):
        from schemas import SettingsUpdateRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SettingsUpdateRequest(history_limit=0)

    def test_settings_update_above_maximum(self):
        from schemas import SettingsUpdateRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SettingsUpdateRequest(history_limit=201)
