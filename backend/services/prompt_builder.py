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
    """Build the user prompt from document type, options, and input text.

    §4.3 ユーザープロンプト（動的生成）
    """
    doc_label = DOCUMENT_TYPE_LABELS[document_type]

    # 有効な校正オプションの表示名を取得
    active_labels = [
        label
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


def build_prompts(request: ProofreadRequest) -> tuple[str, str]:
    """Build both system and user prompts from a ProofreadRequest."""
    user_prompt = build_user_prompt(
        document_type=request.document_type,
        options=request.options,
        text=request.text,
    )
    return SYSTEM_PROMPT, user_prompt
