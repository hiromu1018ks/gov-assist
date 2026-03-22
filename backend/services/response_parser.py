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
    - All failures: Fallback extraction (regex -> plain text -> error)
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
