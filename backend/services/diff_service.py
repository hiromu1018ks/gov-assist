"""Diff service for computing text differences between input and corrected text.

§4.4 ステップ5–11: diff計算・後処理・corrections照合・大幅書き換え検知
§4.5: diffとcorrectionsの対応付け戦略
"""

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass

import diff_match_patch

from schemas import (
    CorrectionItem,
    DiffBlock,
    DiffType,
    ProofreadStatus,
    StatusReason,
)

logger = logging.getLogger("govassist")

# §10: パフォーマンス要件
CHAR_DIFF_TIMEOUT = 5  # seconds
LINE_DIFF_TIMEOUT = 1  # seconds

# §4.4 ステップ10: 大幅書き換え検知
LARGE_REWRITE_THRESHOLD = 0.3

# §4.4 ステップ7: 短小ブロック吸収
SHORT_EQUAL_THRESHOLD = 2  # chars — equal blocks < this get absorbed
SHORT_CHANGE_THRESHOLD = 1  # chars — isolated changes this short get absorbed

# §4.5: 近傍マッチ
PROXIMITY_GUARD_LENGTH = 4  # chars — corrections shorter than this never match
PROXIMITY_BASE_WIDTH = 20  # chars — max match width

ENABLE_DIFF_COMPACTION_DEFAULT = True


class DiffTimeoutError(Exception):
    """Raised when diff computation exceeds timeout."""
    pass


@dataclass
class DiffResult:
    """Result of diff computation."""
    diffs: list[DiffBlock]
    warnings: list[str]
    status: ProofreadStatus
    status_reason: StatusReason | None
    corrections: list[CorrectionItem]


def _compute_raw_diffs(text1: str, text2: str) -> list[tuple[int, str]]:
    """Compute character-level diffs using diff-match-patch with timeout.

    Returns list of (operation, text) tuples:
    - 0 = EQUAL, -1 = DELETE, 1 = INSERT

    Raises DiffTimeoutError on timeout (CHAR_DIFF_TIMEOUT seconds).
    """
    if text1 == "" and text2 == "":
        return [(0, "")]

    dmp = diff_match_patch.diff_match_patch()

    def _compute():
        return dmp.diff_main(text1, text2)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_compute)
        try:
            return future.result(timeout=CHAR_DIFF_TIMEOUT)
        except FuturesTimeoutError:
            raise DiffTimeoutError()


def _compute_line_diff(text1: str, text2: str) -> list[tuple[int, str]]:
    """Compute line-level diffs using difflib as fallback.

    Returns same format as _compute_raw_diffs: [(operation, text), ...]
    Used when character-level diff times out.
    Raises DiffTimeoutError on timeout (LINE_DIFF_TIMEOUT seconds).
    """
    import difflib

    if text1 == "" and text2 == "":
        return [(0, "")]

    lines1 = text1.splitlines(keepends=True)
    lines2 = text2.splitlines(keepends=True)

    def _compute():
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        diffs: list[tuple[int, str]] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                diffs.append((0, "".join(lines1[i1:i2])))
            elif tag == "delete":
                diffs.append((-1, "".join(lines1[i1:i2])))
            elif tag == "insert":
                diffs.append((1, "".join(lines2[j1:j2])))
            elif tag == "replace":
                diffs.append((-1, "".join(lines1[i1:i2])))
                diffs.append((1, "".join(lines2[j1:j2])))
        return diffs

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_compute)
        try:
            return future.result(timeout=LINE_DIFF_TIMEOUT)
        except FuturesTimeoutError:
            raise DiffTimeoutError()


# §4.4 ステップ6: 連続する同種 diff ブロックをマージ
_OP_TO_TYPE = {-1: DiffType.DELETE, 0: DiffType.EQUAL, 1: DiffType.INSERT}


def _merge_consecutive(diffs: list[tuple[int, str]]) -> list[dict]:
    """Merge consecutive same-type diff blocks.

    §4.4 ステップ6: 連続する同種 diff ブロックをマージ
    例: [delete("く"), delete("だ")] → [delete("くだ")]

    Converts raw diff tuples to dicts with DiffType enum.
    """
    if not diffs:
        return []

    result: list[dict] = []
    current_type = _OP_TO_TYPE[diffs[0][0]]
    current_text = diffs[0][1]

    for op, text in diffs[1:]:
        block_type = _OP_TO_TYPE[op]
        if block_type == current_type:
            current_text += text
        else:
            result.append({"type": current_type, "text": current_text})
            current_type = block_type
            current_text = text

    result.append({"type": current_type, "text": current_text})
    return result


# --- Stubs for symbols not yet implemented (later tasks) ---


def compute_diffs(
    *,
    input_text: str,
    corrected_text: str,
    corrections: list[CorrectionItem],
    request_id: str,
    enable_diff_compaction: bool = ENABLE_DIFF_COMPACTION_DEFAULT,
) -> DiffResult:
    """Compute diffs between input and corrected text with full processing pipeline.

    S4.4 Step 5-11: diff computation, post-processing, corrections matching,
    and large rewrite detection.

    Pipeline:
    5.  diff-match-patch (5s timeout -> line-level fallback -> partial)
    6.  Merge consecutive same-type blocks
    7.  Absorb short blocks (if enable_diff_compaction=True)
    8.  Normalize order (4 rules)
    9.  Calculate start positions
    10. Match corrections via proximity
    11. Detect large rewrite
    """
    # Step 5: Compute raw diffs with timeout
    try:
        raw_diffs = _compute_raw_diffs(input_text, corrected_text)
    except DiffTimeoutError:
        logger.warning(
            "Character diff timeout, falling back to line diff: request_id=%s input_chars=%d",
            request_id, len(input_text),
        )
        try:
            raw_diffs = _compute_line_diff(input_text, corrected_text)
        except DiffTimeoutError:
            logger.warning(
                "Line diff also timed out: request_id=%s input_chars=%d",
                request_id, len(input_text),
            )
            return DiffResult(
                diffs=[],
                warnings=[],
                status=ProofreadStatus.PARTIAL,
                status_reason=StatusReason.DIFF_TIMEOUT,
                corrections=corrections,
            )

    # Step 6: Merge consecutive same-type blocks
    blocks = _merge_consecutive(raw_diffs)

    # Step 7: Absorb short blocks (optional)
    pre_compaction_count = len(blocks)
    if enable_diff_compaction:
        blocks = _absorb_short_blocks(blocks)
        if len(blocks) != pre_compaction_count:
            logger.info(
                "Diff compaction: request_id=%s before=%d after=%d",
                request_id, pre_compaction_count, len(blocks),
            )

    # Step 8: Normalize order
    blocks = _normalize_order(blocks)

    # Step 9 (partial): Calculate start positions
    blocks = _calculate_starts(blocks)

    # Step 10: Match corrections to diff blocks
    _match_corrections(blocks, corrections, input_text)

    # Step 11: Detect large rewrite
    warnings = _detect_large_rewrite(blocks, len(input_text))
    if warnings:
        logger.warning(
            "Large rewrite detected: request_id=%s input_chars=%d",
            request_id, len(input_text),
        )

    # Convert to DiffBlock objects
    diff_blocks = [
        DiffBlock(
            type=b["type"],
            text=b["text"],
            start=b["start"],
            position="after" if b["type"] == DiffType.INSERT else None,
            reason=b.get("reason"),
        )
        for b in blocks
    ]

    return DiffResult(
        diffs=diff_blocks,
        warnings=warnings,
        status=ProofreadStatus.SUCCESS,
        status_reason=None,
        corrections=corrections,
    )


def _absorb_short_blocks(blocks: list[dict]) -> list[dict]:
    """Absorb short blocks to reduce diff noise.

    §4.4 ステップ7: 短小ブロックの吸収
    - 2文字未満の equal ブロックは前後の変更ブロックとマージする
    - 1文字の孤立した delete/insert は隣接 equal に統合する

    Processes blocks in a single forward pass with 4 cases:
    1. Short equal between two change blocks → merge into preceding change
    2. Short equal after a change block (before equal/end) → merge into change
    3. Short equal before a change block (at start or after equal) → merge into change
    4. Isolated 1-char change between equals → merge into preceding equal
    """
    if len(blocks) <= 2:
        return [dict(b) for b in blocks]

    result: list[dict] = []
    i = 0
    while i < len(blocks):
        current = blocks[i]

        # Case 1: Short equal between two change blocks
        if (i + 2 < len(blocks)
                and current["type"] != DiffType.EQUAL
                and blocks[i + 1]["type"] == DiffType.EQUAL
                and len(blocks[i + 1]["text"]) < SHORT_EQUAL_THRESHOLD
                and blocks[i + 2]["type"] != DiffType.EQUAL):
            result.append({
                "type": current["type"],
                "text": current["text"] + blocks[i + 1]["text"],
            })
            i += 2  # skip absorbed equal
            continue

        # Case 2: Short equal after a change block (before equal or end)
        if (result
                and current["type"] == DiffType.EQUAL
                and len(current["text"]) < SHORT_EQUAL_THRESHOLD
                and result[-1]["type"] != DiffType.EQUAL):
            result[-1] = {
                "type": result[-1]["type"],
                "text": result[-1]["text"] + current["text"],
            }
            i += 1
            continue

        # Case 3: Short equal before a change block (at start or after equal)
        if (current["type"] == DiffType.EQUAL
                and len(current["text"]) < SHORT_EQUAL_THRESHOLD
                and i + 1 < len(blocks)
                and blocks[i + 1]["type"] != DiffType.EQUAL
                and (not result or result[-1]["type"] == DiffType.EQUAL)):
            result.append({
                "type": blocks[i + 1]["type"],
                "text": current["text"] + blocks[i + 1]["text"],
            })
            i += 2  # skip both absorbed equal and change
            continue

        # Case 4: Isolated 1-char change between equals
        if (current["type"] in (DiffType.DELETE, DiffType.INSERT)
                and len(current["text"]) == SHORT_CHANGE_THRESHOLD
                and result
                and result[-1]["type"] == DiffType.EQUAL
                and i + 1 < len(blocks)
                and blocks[i + 1]["type"] == DiffType.EQUAL):
            result[-1] = {
                "type": DiffType.EQUAL,
                "text": result[-1]["text"] + current["text"],
            }
            i += 1
            continue

        result.append(dict(current))
        i += 1

    return result


def _normalize_order(blocks: list[dict]) -> list[dict]:
    """Normalize diff block order.

    §4.4 ステップ8: 4つのルールを適用
    ルール1: 連続する delete ブロック群をひとつにまとめる
    ルール2: delete → insert の順で並べる
    ルール3: equal を跨ぐ場合は別の変更ブロックとして扱う（equal 跨ぎ結合禁止）
    ルール4: 同一 start の insert は配列の出現順を固定する

    Algorithm: Walk through blocks. When a change group is found
    (consecutive non-equal blocks), output deletes first (merged),
    then inserts in original order. Equal blocks act as separators.
    """
    result: list[dict] = []
    i = 0
    while i < len(blocks):
        if blocks[i]["type"] == DiffType.EQUAL:
            result.append(dict(blocks[i]))
            i += 1
            continue

        # Collect change group: all consecutive non-equal blocks
        group: list[dict] = []
        while i < len(blocks) and blocks[i]["type"] != DiffType.EQUAL:
            group.append(blocks[i])
            i += 1

        # Separate deletes and inserts
        deletes = [b for b in group if b["type"] == DiffType.DELETE]
        inserts = [b for b in group if b["type"] == DiffType.INSERT]

        # Rule 1: Merge consecutive deletes into one block
        if deletes:
            result.append({
                "type": DiffType.DELETE,
                "text": "".join(d["text"] for d in deletes),
            })

        # Rules 2 & 4: Inserts in original array order (not merged)
        result.extend([dict(ins) for ins in inserts])

    return result


def _calculate_starts(blocks: list[dict]) -> list[dict]:
    """Calculate start positions for diff blocks relative to input text.

    §4.6: start は元テキスト（入力テキスト）の文字位置を基準とする。
    - EQUAL: start = current_pos, advance by len(text)
    - DELETE: start = current_pos, advance by len(text)
    - INSERT: start = position of preceding DELETE if any, else current_pos.
      INSERT does NOT advance the position counter.

    After a DELETE, any following INSERTs share the same start as that DELETE.
    Once a non-INSERT block is encountered, the DELETE's start is no longer
    referenced.

    Modifies blocks in-place by adding "start" field. Returns the same list.
    """
    pos = 0
    last_delete_start: int | None = None
    for block in blocks:
        if block["type"] == DiffType.INSERT:
            block["start"] = last_delete_start if last_delete_start is not None else pos
        else:
            block["start"] = pos
            pos += len(block["text"])
            if block["type"] == DiffType.DELETE:
                last_delete_start = block["start"]
            else:
                last_delete_start = None
    return blocks


def _match_corrections(
    diffs: list[dict],
    corrections: list[CorrectionItem],
    input_text: str,
) -> None:
    """Match corrections to diff blocks via proximity matching.

    §4.5: 近傍マッチの定義
    - ガード条件: original < 4 chars → マッチしない
    - マッチ幅: min(20, original.length × 2) chars
    - original の完全一致位置を入力テキスト中から検索
    - 1 diff ブロック = max 1 reason（最長一致優先）
    - 1 correction = 消費型（1回のみ使用）

    Modifies diffs and corrections in-place.
    """
    used: set[int] = set()

    for diff in diffs:
        if diff["type"] == DiffType.EQUAL:
            continue

        best_idx: int | None = None
        best_distance: float = float("inf")
        best_original_len: int = 0

        for idx, corr in enumerate(corrections):
            if idx in used:
                continue
            if len(corr.original) < PROXIMITY_GUARD_LENGTH:
                continue

            match_width = min(PROXIMITY_BASE_WIDTH, len(corr.original) * 2)

            # Find all occurrences of original in input_text
            search_start = 0
            while True:
                pos = input_text.find(corr.original, search_start)
                if pos == -1:
                    break

                # Calculate distance from this occurrence to the diff block
                diff_start = diff["start"]
                if diff["type"] == DiffType.DELETE:
                    diff_end = diff_start + len(diff["text"])
                else:  # INSERT — has no extent in original text
                    diff_end = diff_start

                # Check if occurrence is within match width of diff block
                if pos + len(corr.original) > diff_start - match_width and pos < diff_end + match_width:
                    # Calculate actual distance
                    if pos + len(corr.original) <= diff_start:
                        dist = diff_start - (pos + len(corr.original))
                    elif pos >= diff_end:
                        dist = pos - diff_end
                    else:
                        dist = 0  # overlap

                    # Prefer closest distance, break ties by longest original
                    if (dist < best_distance
                            or (dist == best_distance and len(corr.original) > best_original_len)):
                        best_distance = dist
                        best_idx = idx
                        best_original_len = len(corr.original)

                search_start = pos + 1

        if best_idx is not None:
            used.add(best_idx)
            diff["reason"] = corrections[best_idx].reason
            corrections[best_idx].diff_matched = True

    # Mark all unused corrections as unmatched
    for idx, corr in enumerate(corrections):
        if idx not in used:
            corr.diff_matched = False


def _detect_large_rewrite(
    diffs: list[dict],
    input_length: int,
) -> list[str]:
    """Detect large-scale text rewriting.

    §4.4 ステップ10: 大幅書き換え検知
    - 変更文字数 = delete + insert ブロックの文字数合計（equal は除外）
    - 条件: (変更率 > 30%) AND (最大連続変更ブロック長 / 入力長 > 30%)
    - AND 条件により、改行正規化等の細かい修正積み上がりによる誤検知を防止

    Returns list of warning strings (empty if no large rewrite).
    """
    if input_length == 0 or not diffs:
        return []

    # Calculate total changed characters
    changed_chars = sum(
        len(d["text"]) for d in diffs if d["type"] != DiffType.EQUAL
    )
    change_rate = changed_chars / input_length

    # Find max consecutive change block length
    max_consecutive = 0
    current_consecutive = 0
    for d in diffs:
        if d["type"] != DiffType.EQUAL:
            current_consecutive += len(d["text"])
        else:
            max_consecutive = max(max_consecutive, current_consecutive)
            current_consecutive = 0
    max_consecutive = max(max_consecutive, current_consecutive)

    consecutive_rate = max_consecutive / input_length

    if change_rate > LARGE_REWRITE_THRESHOLD and consecutive_rate > LARGE_REWRITE_THRESHOLD:
        return ["large_rewrite"]

    return []
