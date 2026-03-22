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


# --- Stubs for symbols not yet implemented (later tasks) ---


def compute_diffs(
    text1: str,
    text2: str,
    corrections: list[CorrectionItem] | None = None,
    enable_compaction: bool = ENABLE_DIFF_COMPACTION_DEFAULT,
) -> DiffResult:
    """Main entry point — orchestrates full diff pipeline."""
    raise NotImplementedError("compute_diffs will be implemented in a later task")


def _merge_consecutive(diffs: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Merge consecutive same-type blocks (Task 2)."""
    raise NotImplementedError("_merge_consecutive will be implemented in a later task")


def _absorb_short_blocks(
    diffs: list[tuple[int, str]],
) -> list[tuple[int, str]]:
    """Absorb short blocks into neighbors (Task 3)."""
    raise NotImplementedError("_absorb_short_blocks will be implemented in a later task")


def _normalize_order(
    diffs: list[tuple[int, str]],
) -> list[tuple[int, str]]:
    """Normalize operation order: EQUAL before DELETE/INSERT (Task 4)."""
    raise NotImplementedError("_normalize_order will be implemented in a later task")


def _calculate_starts(
    diffs: list[tuple[int, str]],
) -> list[DiffBlock]:
    """Convert raw diffs to DiffBlocks with start positions (Task 5)."""
    raise NotImplementedError("_calculate_starts will be implemented in a later task")


def _match_corrections(
    diffs: list[DiffBlock],
    corrections: list[CorrectionItem],
) -> list[CorrectionItem]:
    """Match AI corrections to diff blocks (Task 6)."""
    raise NotImplementedError("_match_corrections will be implemented in a later task")


def _detect_large_rewrite(
    text1: str,
    text2: str,
    diffs: list[tuple[int, str]],
) -> bool:
    """Detect if text was largely rewritten (Task 7)."""
    raise NotImplementedError("_detect_large_rewrite will be implemented in a later task")
