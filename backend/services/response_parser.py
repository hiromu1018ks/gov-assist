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
    cleaned = re.sub(r'[\{\}\[\]\"\'\\:,]', ' ', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if cleaned and len(cleaned) > 5:
        return cleaned, True

    # Step 3: Complete failure
    return "", False


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
