# Prompt Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the prompt builder service that generates system and user prompts for the AI proofreading endpoint, following the fixed system prompt and dynamic user prompt template defined in design spec §4.3.

**Architecture:** A pure-function module (`prompt_builder.py`) with no external dependencies. Exports a fixed `SYSTEM_PROMPT` constant and a `build_user_prompt()` function that maps `DocumentType` enum values and `ProofreadOptions` boolean fields to their Japanese display names, then assembles the user prompt template. A convenience `build_prompts()` function wraps both for the proofread router (Task 9).

**Tech Stack:** Python 3.12, Pydantic (existing schemas only — no new dependencies)

**Design spec reference:** §4.3 (prompt design — system prompt fixed, user prompt dynamic), §3.3.1 (document type labels), §3.3.3 (option labels)

**Interface contract with AIClient (Task 4):** The proofread router will call `AIClient.complete(system_prompt=..., user_prompt=..., ...)`. This module provides those two strings.

---

## Files

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/services/prompt_builder.py` | Create | `SYSTEM_PROMPT` constant, label mappings, `build_user_prompt()`, `build_prompts()` |
| `backend/tests/test_prompt_builder.py` | Create | Unit tests for system prompt content, user prompt generation, label mappings |

No existing files are modified. No new dependencies needed.

---

### Task 1: System Prompt Constant & Label Mappings

**Files:**
- Create: `backend/services/prompt_builder.py`
- Create: `backend/tests/test_prompt_builder.py`

- [ ] **Step 1: Write failing tests for system prompt and label mappings**

Create `backend/tests/test_prompt_builder.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_prompt_builder.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'services.prompt_builder'`

- [ ] **Step 3: Implement SYSTEM_PROMPT, label mappings, and stub build_user_prompt**

Create `backend/services/prompt_builder.py`:

```python
"""Prompt builder service for AI proofreading."""

from schemas import DocumentType, ProofreadOptions, ProofreadRequest

# §4.3 システムプロンプト（固定）
SYSTEM_PROMPT = """あなたは日本の地方自治体の公文書・業務文書を専門とする文章校正アシスタントです。
以下のルールを厳守してください。

【出力ルール】
- 必ず以下の JSON 形式のみで応答すること。JSON 以外のテキスト・説明・コードブロックは一切含めないこと。
- JSON のキー名・構造を変えないこと。

【校正ルール】
- 必要最小限の修正のみ行うこと。原文の表現・構成を大幅に書き換えることを禁止する。
- 1件の correction は1箇所の最小変更単位とすること（文字〜句単位）。文単位・段落単位の一括書き換えは禁止。
- original / corrected フィールドは各 50 文字以内とすること。
- 原文を尊重し、意味の変わる書き換えは行わないこと。"""

# §3.3.1 文書種別の表示名
DOCUMENT_TYPE_LABELS: dict[DocumentType, str] = {
    DocumentType.EMAIL: "メール",
    DocumentType.REPORT: "報告書",
    DocumentType.OFFICIAL: "公文書",
    DocumentType.OTHER: "その他",
}

# §3.3.3 校正オプションの表示名
OPTION_LABELS: dict[str, str] = {
    "typo": "誤字・脱字・変換ミスの検出",
    "keigo": "敬語・丁寧語の適切さチェック",
    "terminology": "公文書用語・表現への統一（例：「ください」→「くださいますよう」）",
    "style": "文体の統一（です・ます調 / である調）",
    "legal": "法令・条例用語の確認",
    "readability": "文章の読みやすさ・論理構成の改善提案",
}


def build_user_prompt(
    document_type: DocumentType,
    options: ProofreadOptions,
    text: str,
) -> str:
    """Build the user prompt from document type, options, and input text."""
    raise NotImplementedError


def build_prompts(request: ProofreadRequest) -> tuple[str, str]:
    """Build both system and user prompts from a ProofreadRequest."""
    raise NotImplementedError
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_prompt_builder.py -v`

Expected: All 20 tests PASS (8 system prompt + 5 document type + 7 option labels)

- [ ] **Step 5: Commit**

```bash
git add backend/services/prompt_builder.py backend/tests/test_prompt_builder.py
git commit -m "feat(backend): add prompt builder with system prompt and label mappings"
```

---

### Task 2: build_user_prompt() — Dynamic User Prompt Generation

**Files:**
- Modify: `backend/services/prompt_builder.py` (implement `build_user_prompt`)
- Modify: `backend/tests/test_prompt_builder.py` (add `TestBuildUserPrompt` class)

- [ ] **Step 1: Write failing tests for build_user_prompt()**

Add to `backend/tests/test_prompt_builder.py`:

```python
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
        assert "敬語" not in prompt

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_prompt_builder.py::TestBuildUserPrompt -v`

Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: Implement build_user_prompt()**

Replace the stub in `backend/services/prompt_builder.py` with:

```python
def build_user_prompt(
    document_type: DocumentType,
    options: ProofreadOptions,
    text: str,
) -> str:
    """Build the user prompt from document type, options, and input text.

    §4.3 ユーザープロンプト（動的生成）
    """
    doc_label = DOCUMENT_TYPE_LABELS[document_type]

    # 有効な校正オプションの表示名を取得
    active_labels = [
        OPTION_LABELS[field]
        for field, label in OPTION_LABELS.items()
        if getattr(options, field, False)
    ]
    options_text = "\n".join(f"- {label}" for label in active_labels)

    return f"""文書種別：{doc_label}
チェック項目：
{options_text}
入力文書：
{text}

以下の JSON 形式のみで返答してください：
{{
  "corrected_text": "校正済み全文（原文からの最小変更のみ）",
  "summary": "校正のサマリー（修正件数・主要な指摘）",
  "corrections": [
    {{
      "original": "修正前テキスト（原文から抜粋、50文字以内）",
      "corrected": "修正後テキスト（50文字以内）",
      "reason": "修正理由",
      "category": "誤字脱字 | 敬語 | 用語 | 文体 | 法令 | 読みやすさ"
    }}
  ]
}}"""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_prompt_builder.py::TestBuildUserPrompt -v`

Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/prompt_builder.py backend/tests/test_prompt_builder.py
git commit -m "feat(backend): implement build_user_prompt() with dynamic option mapping"
```

---

### Task 3: build_prompts() — Convenience Wrapper

**Files:**
- Modify: `backend/services/prompt_builder.py` (implement `build_prompts`)
- Modify: `backend/tests/test_prompt_builder.py` (add `TestBuildPrompts` class)

- [ ] **Step 1: Write failing tests for build_prompts()**

Add to `backend/tests/test_prompt_builder.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_prompt_builder.py::TestBuildPrompts -v`

Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: Implement build_prompts()**

Replace the stub in `backend/services/prompt_builder.py` with:

```python
def build_prompts(request: ProofreadRequest) -> tuple[str, str]:
    """Build both system and user prompts from a ProofreadRequest."""
    user_prompt = build_user_prompt(
        document_type=request.document_type,
        options=request.options,
        text=request.text,
    )
    return SYSTEM_PROMPT, user_prompt
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_prompt_builder.py::TestBuildPrompts -v`

Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/prompt_builder.py backend/tests/test_prompt_builder.py
git commit -m "feat(backend): add build_prompts() convenience wrapper"
```

---

### Task 4: Full Test Suite Verification

**Files:** None (verification only)

- [ ] **Step 1: Run new prompt builder tests**

Run: `cd backend && python -m pytest tests/test_prompt_builder.py -v`

Expected: All 35 tests PASS (8 system prompt + 5 document type labels + 7 option labels + 11 build_user_prompt + 4 build_prompts)

- [ ] **Step 2: Run entire test suite to check for regressions**

Run: `cd backend && python -m pytest -v`

Expected: All tests PASS (existing tests + 35 new prompt builder tests)

- [ ] **Step 3: Final commit (only if fixes were needed)**

```bash
git add backend/services/prompt_builder.py backend/tests/test_prompt_builder.py
git commit -m "fix: resolve test regressions from prompt builder addition"
```

Skip this step if no fixes were needed.
