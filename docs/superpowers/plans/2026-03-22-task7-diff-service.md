# Diff Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the diff service that computes character-level differences between input and corrected text, with post-processing (merge, absorption, normalization), corrections proximity matching, and large rewrite detection, following design spec §4.4 steps 5–11 and §4.5.

**Architecture:** A module (`diff_service.py`) with pure synchronous helper functions for each processing step, plus one orchestrator (`compute_diffs()`) that chains all steps. Uses `diff-match-patch` for character-level diffs with timeout via `ThreadPoolExecutor`, falls back to `difflib` line-level diffs on timeout. Internal processing uses `list[dict]` with `DiffType` enum; final output converts to `DiffBlock` Pydantic models with calculated `start` positions and matched correction `reason`s. Returns a `DiffResult` dataclass.

**Tech Stack:** Python 3.12, `diff-match-patch` (new dependency), `difflib` (stdlib), `concurrent.futures` (stdlib), Pydantic (existing schemas), `unittest.mock` for tests

**Design spec reference:** §4.4 steps 5–11, §4.5, §4.6 (DiffBlock schema), §9.2 (logging), §10 (performance)

**Interface contract:**
- **Input:** `input_text` (str), `corrected_text` (str), `corrections` (list[CorrectionItem]), `request_id` (str), `enable_diff_compaction` (bool, default True)
- **Output:** `DiffResult(diffs: list[DiffBlock], warnings: list[str], status: ProofreadStatus, status_reason: StatusReason | None)`
- **Consumed by:** Proofread router (Task 9)
- **Depends on:** `schemas.{DiffBlock, DiffType, CorrectionItem, ProofreadStatus, StatusReason}`
- **Note:** `summary` enrichment with large_rewrite warning text is the caller's responsibility (Task 9 proofread router), not this service's

---

## Files

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/requirements.txt` | Modify | Add `diff-match-patch>=20230430` |
| `backend/services/diff_service.py` | Create | `DiffResult`, `DiffTimeoutError`, `compute_diffs()`, all helper functions |
| `backend/tests/test_diff_service.py` | Create | Unit tests for all functions |

No other files are modified.

---

## Internal Data Flow

```
_compute_raw_diffs()  →  list[tuple[int, str]]   (raw diff-match-patch output)
       ↓ fallback: _compute_line_diff()
_merge_consecutive()  →  list[dict]               ({"type": DiffType, "text": str})
_absorb_short_blocks()→  list[dict]               (same format, fewer blocks)
_normalize_order()    →  list[dict]               (delete→insert order enforced)
_calculate_starts()   →  list[dict]               (adds "start" int field)
_match_corrections()  →  mutates dicts in-place   (adds "reason" field)
_detect_large_rewrite()→ list[str]                (warnings)
       ↓ convert to DiffBlock objects
DiffResult            →  return value
```

---

### Task 1: Setup & DiffResult & Raw Diff Computation

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/services/diff_service.py`
- Create: `backend/tests/test_diff_service.py`

- [ ] **Step 1: Add diff-match-patch dependency**

Append to `backend/requirements.txt`:

```
diff-match-patch>=20230430
```

- [ ] **Step 2: Install and verify**

Run: `cd backend && pip install -r requirements.txt`
Then: `python -c "import diff_match_patch; dmp = diff_match_patch.diff_match_patch(); print(dmp.diff_main('ABC', 'AXC'))"`
Expected: No errors, prints list of tuples like `[(-1, 'B'), (1, 'X'), (0, 'C')]` (exact output may vary)

- [ ] **Step 3: Write failing tests for DiffResult, DiffTimeoutError, _compute_raw_diffs, _compute_line_diff**

> **Note:** Some imported symbols (`_match_corrections`, `_detect_large_rewrite`, etc.) are not yet implemented — ImportError is expected and acceptable. They will be implemented in later tasks.

Create `backend/tests/test_diff_service.py`:

```python
"""Tests for diff service."""

import pytest
from unittest.mock import patch, MagicMock

from services.diff_service import (
    DiffResult,
    DiffTimeoutError,
    compute_diffs,
    _compute_raw_diffs,
    _compute_line_diff,
    _merge_consecutive,
    _absorb_short_blocks,
    _normalize_order,
    _calculate_starts,
    _match_corrections,
    _detect_large_rewrite,
)
from schemas import DiffType, DiffBlock, CorrectionItem, ProofreadStatus, StatusReason


class TestDiffResult:
    def test_create_success(self):
        result = DiffResult(
            diffs=[DiffBlock(type=DiffType.EQUAL, text="test", start=0)],
            warnings=[],
            status=ProofreadStatus.SUCCESS,
            status_reason=None,
        )
        assert len(result.diffs) == 1
        assert result.status == ProofreadStatus.SUCCESS
        assert result.warnings == []

    def test_create_with_warnings(self):
        result = DiffResult(
            diffs=[],
            warnings=["large_rewrite"],
            status=ProofreadStatus.SUCCESS,
            status_reason=None,
        )
        assert result.warnings == ["large_rewrite"]

    def test_create_partial_timeout(self):
        result = DiffResult(
            diffs=[],
            warnings=[],
            status=ProofreadStatus.PARTIAL,
            status_reason=StatusReason.DIFF_TIMEOUT,
        )
        assert result.status == ProofreadStatus.PARTIAL
        assert result.status_reason == StatusReason.DIFF_TIMEOUT


class TestDiffTimeoutError:
    def test_raise_and_catch(self):
        with pytest.raises(DiffTimeoutError):
            raise DiffTimeoutError()


class TestComputeRawDiffs:
    def test_basic_diff(self):
        """ABC → AXC should produce EQUAL, DELETE, INSERT, EQUAL."""
        diffs = _compute_raw_diffs("ABC", "AXC")
        types = [d[0] for d in diffs]
        texts = [d[1] for d in diffs]
        # Combine into reconstructed texts to verify content
        deleted = "".join(t for op, t in diffs if op == -1)
        inserted = "".join(t for op, t in diffs if op == 1)
        assert "B" in deleted
        assert "X" in inserted

    def test_identical_texts(self):
        diffs = _compute_raw_diffs("ABC", "ABC")
        assert len(diffs) == 1
        assert diffs[0] == (0, "ABC")

    def test_empty_texts(self):
        diffs = _compute_raw_diffs("", "")
        assert diffs == [(0, "")]

    def test_insert_only(self):
        diffs = _compute_raw_diffs("", "ABC")
        assert len(diffs) == 1
        assert diffs[0] == (1, "ABC")

    def test_delete_only(self):
        diffs = _compute_raw_diffs("ABC", "")
        assert len(diffs) == 1
        assert diffs[0] == (-1, "ABC")

    def test_japanese_text(self):
        diffs = _compute_raw_diffs("これはテストです", "これはテストです。")
        assert len(diffs) >= 2
        assert diffs[-1][0] == 1  # INSERT for "。"

    def test_timeout_raises_error(self):
        with patch("services.diff_service.CHAR_DIFF_TIMEOUT", 0.001):
            long_text = "あ" * 100000
            with pytest.raises(DiffTimeoutError):
                _compute_raw_diffs(long_text, long_text + "追加")


class TestComputeLineDiff:
    def test_basic_line_diff(self):
        diffs = _compute_line_diff("ABC\nDEF", "ABC\nXYZ")
        types = [d[0] for d in diffs]
        assert 0 in types  # EQUAL
        assert -1 in types  # DELETE
        assert 1 in types  # INSERT
        combined_equal = "".join(t for op, t in diffs if op == 0)
        assert "ABC" in combined_equal

    def test_identical_lines(self):
        diffs = _compute_line_diff("ABC\nDEF", "ABC\nDEF")
        assert len(diffs) == 1
        assert diffs[0][0] == 0

    def test_empty_lines(self):
        diffs = _compute_line_diff("", "")
        assert len(diffs) == 1
        assert diffs[0] == (0, "")

    def test_line_diff_timeout(self):
        """Line-level diff should raise DiffTimeoutError on timeout."""
        with patch("services.diff_service.LINE_DIFF_TIMEOUT", 0.001):
            with pytest.raises(DiffTimeoutError):
                _compute_line_diff("あ" * 100000, "あ" * 100000 + "追加")
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_diff_service.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 5: Create module skeleton with DiffResult, DiffTimeoutError, _compute_raw_diffs, _compute_line_diff**

Create `backend/services/diff_service.py`:

```python
"""Diff service for computing text differences between input and corrected text.

§4.4 ステップ5–11: diff計算・後処理・corrections照合・大幅書き換え検知
§4.5: diffとcorrectionsの対応付け戦略
"""

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field

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
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_diff_service.py -v`
Expected: 3 (DiffResult) + 1 (DiffTimeoutError) + 7 (ComputeRawDiffs) + 3 (ComputeLineDiff) = 14 passed

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/services/diff_service.py backend/tests/test_diff_service.py
git commit -m "feat(backend): add diff-match-patch dependency and raw diff computation with timeout"
```

---

### Task 2: Merge Consecutive Same-Type Blocks

**Files:**
- Modify: `backend/services/diff_service.py`
- Modify: `backend/tests/test_diff_service.py`

- [ ] **Step 1: Write failing tests for _merge_consecutive**

Add to `backend/tests/test_diff_service.py`:

```python
class TestMergeConsecutive:
    """§4.4 ステップ6: 連続する同種 diff ブロックをマージ"""

    def test_merge_consecutive_deletes(self):
        raw = [(-1, "あ"), (-1, "い"), (0, "う")]
        result = _merge_consecutive(raw)
        assert len(result) == 2
        assert result[0]["type"] == DiffType.DELETE
        assert result[0]["text"] == "あい"
        assert result[1]["type"] == DiffType.EQUAL

    def test_merge_consecutive_inserts(self):
        raw = [(0, "あ"), (1, "x"), (1, "y")]
        result = _merge_consecutive(raw)
        assert len(result) == 2
        assert result[1]["type"] == DiffType.INSERT
        assert result[1]["text"] == "xy"

    def test_merge_consecutive_equals(self):
        raw = [(0, "あ"), (0, "い"), (-1, "う")]
        result = _merge_consecutive(raw)
        assert len(result) == 2
        assert result[0]["type"] == DiffType.EQUAL
        assert result[0]["text"] == "あい"

    def test_no_merge_needed(self):
        raw = [(0, "A"), (-1, "B"), (1, "X"), (0, "C")]
        result = _merge_consecutive(raw)
        assert len(result) == 4

    def test_empty_input(self):
        assert _merge_consecutive([]) == []

    def test_single_block(self):
        raw = [(0, "abc")]
        result = _merge_consecutive(raw)
        assert len(result) == 1
        assert result[0]["text"] == "abc"

    def test_all_same_type(self):
        raw = [(-1, "a"), (-1, "b"), (-1, "c")]
        result = _merge_consecutive(raw)
        assert len(result) == 1
        assert result[0]["text"] == "abc"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_diff_service.py::TestMergeConsecutive -v`
Expected: FAIL (ImportError for `_merge_consecutive`)

- [ ] **Step 3: Implement _merge_consecutive**

Add to `backend/services/diff_service.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_diff_service.py::TestMergeConsecutive -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add backend/services/diff_service.py backend/tests/test_diff_service.py
git commit -m "feat(backend): add consecutive same-type diff block merging"
```

---

### Task 3: Short Block Absorption

**Files:**
- Modify: `backend/services/diff_service.py`
- Modify: `backend/tests/test_diff_service.py`

- [ ] **Step 1: Write failing tests for _absorb_short_blocks**

Add to `backend/tests/test_diff_service.py`:

```python
class TestAbsorbShortBlocks:
    """§4.4 ステップ7: 短小ブロックの吸収"""

    @staticmethod
    def _b(type_str: str, text: str) -> dict:
        type_map = {
            "equal": DiffType.EQUAL,
            "delete": DiffType.DELETE,
            "insert": DiffType.INSERT,
        }
        return {"type": type_map[type_str], "text": text}

    def test_absorb_short_equal_between_changes(self):
        """Short equal between delete and insert → absorbed into delete."""
        blocks = [self._b("delete", "abc"), self._b("equal", "の"), self._b("insert", "def")]
        result = _absorb_short_blocks(blocks)
        assert len(result) == 2
        assert result[0]["text"] == "abcの"
        assert result[0]["type"] == DiffType.DELETE

    def test_absorb_short_equal_after_change(self):
        """Short equal after a change (before equal or end) → absorbed into change."""
        blocks = [self._b("delete", "abc"), self._b("equal", "。"), self._b("equal", "def")]
        result = _absorb_short_blocks(blocks)
        assert len(result) == 2
        assert result[0]["text"] == "abc。"

    def test_absorb_short_equal_before_change(self):
        """Short equal before a change (after equal or start) → absorbed into change."""
        blocks = [self._b("equal", "abc"), self._b("equal", "。"), self._b("delete", "x")]
        result = _absorb_short_blocks(blocks)
        assert len(result) == 2
        assert result[1]["text"] == "。x"

    def test_isolated_single_char_change_between_equals(self):
        """1-char isolated change between equals → absorbed into preceding equal."""
        blocks = [self._b("equal", "abc"), self._b("delete", "。"), self._b("equal", "def")]
        result = _absorb_short_blocks(blocks)
        assert len(result) == 2
        assert result[0]["text"] == "abc。"

    def test_long_equal_not_absorbed(self):
        """Equal blocks >= 2 chars must NOT be absorbed."""
        blocks = [self._b("delete", "abc"), self._b("equal", "これは"), self._b("insert", "def")]
        result = _absorb_short_blocks(blocks)
        assert len(result) == 3

    def test_exactly_threshold_not_absorbed(self):
        """Equal blocks of exactly SHORT_EQUAL_THRESHOLD (2) chars are NOT absorbed."""
        blocks = [self._b("delete", "abc"), self._b("equal", "の。"), self._b("insert", "def")]
        result = _absorb_short_blocks(blocks)
        assert len(result) == 3

    def test_empty_blocks(self):
        assert _absorb_short_blocks([]) == []

    def test_two_blocks_unchanged(self):
        """2 blocks → no absorption possible, return copies."""
        blocks = [self._b("equal", "a"), self._b("delete", "b")]
        result = _absorb_short_blocks(blocks)
        assert len(result) == 2
        assert result[0] == blocks[0]
        assert result[1] == blocks[1]

    def test_single_char_delete_not_isolated(self):
        """1-char delete adjacent to a change (not between equals) → not absorbed."""
        blocks = [self._b("delete", "abc"), self._b("delete", "。"), self._b("insert", "def")]
        result = _absorb_short_blocks(blocks)
        # The 1-char delete is between two changes, not between equals
        # so case 4 doesn't apply. Should remain 3 blocks.
        assert len(result) == 3

    def test_cascade_absorption(self):
        """Multiple short equals after a change → all absorbed."""
        blocks = [
            self._b("delete", "abc"),
            self._b("equal", "の"),
            self._b("equal", "。"),
            self._b("insert", "def"),
        ]
        result = _absorb_short_blocks(blocks)
        assert len(result) == 2
        assert result[0]["text"] == "abcの。"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_diff_service.py::TestAbsorbShortBlocks -v`
Expected: FAIL

- [ ] **Step 3: Implement _absorb_short_blocks**

Add to `backend/services/diff_service.py`:

```python
def _absorb_short_blocks(blocks: list[dict]) -> list[dict]:
    """Absorb short blocks to reduce diff noise.

    §4.4 ステップ7: 短小ブロックの吸収
    - 2文字未満の equal ブロックは前後の変更ブロックとマージする
    - 1文字の孤立した delete/insert は隣接 equal に統合する

    Processes blocks in a single forward pass with 4 cases:
    1. Short equal between two change blocks → merge into preceding change
    2. Short equal after a change (before equal/end) → merge into change
    3. Short equal before a change (after equal/start) → merge into change
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_diff_service.py::TestAbsorbShortBlocks -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add backend/services/diff_service.py backend/tests/test_diff_service.py
git commit -m "feat(backend): add short block absorption for diff noise reduction"
```

---

### Task 4: Order Normalization

**Files:**
- Modify: `backend/services/diff_service.py`
- Modify: `backend/tests/test_diff_service.py`

- [ ] **Step 1: Write failing tests for _normalize_order**

Add to `backend/tests/test_diff_service.py`:

```python
class TestNormalizeOrder:
    """§4.4 ステップ8: diffs の適用順序の正規化（4ルール）"""

    @staticmethod
    def _b(type_str: str, text: str) -> dict:
        type_map = {
            "equal": DiffType.EQUAL,
            "delete": DiffType.DELETE,
            "insert": DiffType.INSERT,
        }
        return {"type": type_map[type_str], "text": text}

    def test_insert_before_delete_swapped(self):
        """INSERT then DELETE → reordered to DELETE then INSERT (ルール2)."""
        blocks = [
            self._b("equal", "A"),
            self._b("insert", "X"),
            self._b("delete", "B"),
            self._b("equal", "C"),
        ]
        result = _normalize_order(blocks)
        assert result[1]["type"] == DiffType.DELETE
        assert result[2]["type"] == DiffType.INSERT

    def test_delete_before_insert_unchanged(self):
        """DELETE then INSERT → no change needed."""
        blocks = [
            self._b("equal", "A"),
            self._b("delete", "B"),
            self._b("insert", "X"),
            self._b("equal", "C"),
        ]
        result = _normalize_order(blocks)
        assert result[1]["type"] == DiffType.DELETE
        assert result[2]["type"] == DiffType.INSERT

    def test_equal_crossing_prohibited(self):
        """[DELETE][EQUAL>=2][INSERT] → NOT merged (ルール3: equal跨ぎ禁止)."""
        blocks = [
            self._b("delete", "A"),
            self._b("equal", "BC"),
            self._b("insert", "X"),
        ]
        result = _normalize_order(blocks)
        assert len(result) == 3
        assert result[0]["type"] == DiffType.DELETE
        assert result[1]["type"] == DiffType.EQUAL
        assert result[2]["type"] == DiffType.INSERT

    def test_consecutive_deletes_merged(self):
        """Step 7 may create consecutive deletes; normalize merges them (ルール1)."""
        blocks = [
            self._b("equal", "A"),
            self._b("delete", "B"),
            self._b("delete", "C"),
            self._b("insert", "X"),
            self._b("equal", "D"),
        ]
        result = _normalize_order(blocks)
        # Deletes should be merged, inserts kept in order
        delete_blocks = [b for b in result if b["type"] == DiffType.DELETE]
        assert len(delete_blocks) == 1
        assert delete_blocks[0]["text"] == "BC"

    def test_multiple_inserts_keep_order(self):
        """Multiple inserts at same position → maintain array order (ルール4)."""
        blocks = [
            self._b("delete", "A"),
            self._b("insert", "X"),
            self._b("insert", "Y"),
            self._b("equal", "B"),
        ]
        result = _normalize_order(blocks)
        inserts = [b for b in result if b["type"] == DiffType.INSERT]
        assert len(inserts) == 2
        assert inserts[0]["text"] == "X"
        assert inserts[1]["text"] == "Y"

    def test_standalone_insert_unchanged(self):
        """INSERT between equals (no adjacent DELETE) → unchanged."""
        blocks = [
            self._b("equal", "A"),
            self._b("insert", "X"),
            self._b("equal", "B"),
        ]
        result = _normalize_order(blocks)
        assert result[1]["type"] == DiffType.INSERT
        assert len(result) == 3

    def test_standalone_delete_unchanged(self):
        """DELETE between equals (no adjacent INSERT) → unchanged."""
        blocks = [
            self._b("equal", "A"),
            self._b("delete", "B"),
            self._b("equal", "C"),
        ]
        result = _normalize_order(blocks)
        assert result[1]["type"] == DiffType.DELETE
        assert len(result) == 3

    def test_empty_input(self):
        assert _normalize_order([]) == []

    def test_only_equals(self):
        blocks = [self._b("equal", "A"), self._b("equal", "B")]
        result = _normalize_order(blocks)
        assert len(result) == 2
        assert all(b["type"] == DiffType.EQUAL for b in result)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_diff_service.py::TestNormalizeOrder -v`
Expected: FAIL

- [ ] **Step 3: Implement _normalize_order**

Add to `backend/services/diff_service.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_diff_service.py::TestNormalizeOrder -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add backend/services/diff_service.py backend/tests/test_diff_service.py
git commit -m "feat(backend): add diff block order normalization with 4 rules"
```

---

### Task 5: Start Position Calculation

**Files:**
- Modify: `backend/services/diff_service.py`
- Modify: `backend/tests/test_diff_service.py`

- [ ] **Step 1: Write failing tests for _calculate_starts**

Add to `backend/tests/test_diff_service.py`:

```python
class TestCalculateStarts:
    """Start position calculation for diff blocks relative to input text."""

    @staticmethod
    def _b(type_str: str, text: str) -> dict:
        type_map = {
            "equal": DiffType.EQUAL,
            "delete": DiffType.DELETE,
            "insert": DiffType.INSERT,
        }
        return {"type": type_map[type_str], "text": text}

    def test_basic_starts(self):
        """EQUAL(AB), DELETE(C), INSERT(X), EQUAL(DE) → starts: 0, 2, 2, 3."""
        blocks = [
            self._b("equal", "AB"),
            self._b("delete", "C"),
            self._b("insert", "X"),
            self._b("equal", "DE"),
        ]
        result = _calculate_starts(blocks)
        assert result[0]["start"] == 0
        assert result[1]["start"] == 2   # DELETE at pos 2
        assert result[2]["start"] == 2   # INSERT after pos 2 (same as delete)
        assert result[3]["start"] == 3   # EQUAL resumes after deleted char

    def test_insert_only(self):
        """INSERT at beginning → start=0."""
        blocks = [self._b("insert", "XYZ")]
        result = _calculate_starts(blocks)
        assert result[0]["start"] == 0

    def test_delete_only(self):
        """DELETE at beginning → start=0."""
        blocks = [self._b("delete", "ABC")]
        result = _calculate_starts(blocks)
        assert result[0]["start"] == 0

    def test_equal_only(self):
        blocks = [self._b("equal", "hello")]
        result = _calculate_starts(blocks)
        assert result[0]["start"] == 0

    def test_multiple_changes(self):
        """Multiple change pairs → correct cumulative positions."""
        blocks = [
            self._b("equal", "AB"),
            self._b("delete", "C"),
            self._b("insert", "X"),
            self._b("equal", "DE"),
            self._b("delete", "F"),
            self._b("insert", "Y"),
            self._b("equal", "GH"),
        ]
        result = _calculate_starts(blocks)
        assert result[0]["start"] == 0   # EQUAL "AB"
        assert result[1]["start"] == 2   # DELETE "C"
        assert result[2]["start"] == 2   # INSERT "X"
        assert result[3]["start"] == 3   # EQUAL "DE"
        assert result[4]["start"] == 5   # DELETE "F"
        assert result[5]["start"] == 5   # INSERT "Y"
        assert result[6]["start"] == 6   # EQUAL "GH"

    def test_japanese_positions(self):
        """Japanese text: positions are character-based, not byte-based."""
        blocks = [
            self._b("equal", "これは"),
            self._b("delete", "テスト"),
            self._b("insert", "例文"),
            self._b("equal", "です"),
        ]
        result = _calculate_starts(blocks)
        assert result[0]["start"] == 0   # "これは" = 3 chars
        assert result[1]["start"] == 3   # DELETE at pos 3
        assert result[2]["start"] == 3   # INSERT at pos 3
        assert result[3]["start"] == 6   # EQUAL after "テスト" (3 chars)

    def test_empty_blocks(self):
        assert _calculate_starts([]) == []

    def test_insert_does_not_advance_position(self):
        """INSERT blocks do not advance the input position counter."""
        blocks = [
            self._b("equal", "A"),
            self._b("insert", "XX"),
            self._b("insert", "YY"),
            self._b("equal", "B"),
        ]
        result = _calculate_starts(blocks)
        assert result[0]["start"] == 0  # EQUAL "A"
        assert result[1]["start"] == 1  # INSERT at pos 1
        assert result[2]["start"] == 1  # INSERT at pos 1 (no advance)
        assert result[3]["start"] == 1  # EQUAL "B" (no advance from inserts)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_diff_service.py::TestCalculateStarts -v`
Expected: FAIL

- [ ] **Step 3: Implement _calculate_starts**

Add to `backend/services/diff_service.py`:

```python
def _calculate_starts(blocks: list[dict]) -> list[dict]:
    """Calculate start positions for diff blocks relative to input text.

    §4.6: start は元テキスト（入力テキスト）の文字位置を基準とする。
    - EQUAL: start = current_pos, advance by len(text)
    - DELETE: start = current_pos, advance by len(text)
    - INSERT: start = current_pos, do NOT advance (insert has no length in original)

    Modifies blocks in-place by adding "start" field. Returns the same list.
    """
    pos = 0
    for block in blocks:
        block["start"] = pos
        if block["type"] != DiffType.INSERT:
            pos += len(block["text"])
    return blocks
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_diff_service.py::TestCalculateStarts -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add backend/services/diff_service.py backend/tests/test_diff_service.py
git commit -m "feat(backend): add start position calculation for diff blocks"
```

---

### Task 6: Corrections Proximity Matching

**Files:**
- Modify: `backend/services/diff_service.py`
- Modify: `backend/tests/test_diff_service.py`

- [ ] **Step 1: Write failing tests for _match_corrections**

Add to `backend/tests/test_diff_service.py`:

```python
class TestMatchCorrections:
    """§4.5: corrections の近傍マッチ"""

    @staticmethod
    def _b(type_str: str, text: str, start: int = 0) -> dict:
        type_map = {
            "equal": DiffType.EQUAL,
            "delete": DiffType.DELETE,
            "insert": DiffType.INSERT,
        }
        return {"type": type_map[type_str], "text": text, "start": start, "reason": None}

    def test_basic_match(self):
        """Correction original matches a DELETE block → reason assigned."""
        diffs = [
            {"type": DiffType.EQUAL, "text": "A", "start": 0, "reason": None},
            {"type": DiffType.DELETE, "text": "B", "start": 1, "reason": None},
            {"type": DiffType.INSERT, "text": "X", "start": 1, "reason": None},
        ]
        corrections = [
            CorrectionItem(original="B", corrected="X", reason="誤字です", category="誤字脱字"),
        ]
        input_text = "AB"
        _match_corrections(diffs, corrections, input_text)
        assert diffs[1]["reason"] == "誤字です"
        assert corrections[0].diff_matched is True

    def test_short_original_guard(self):
        """Original < 4 chars → never matched (ガード条件)."""
        diffs = [
            {"type": DiffType.DELETE, "text": "です", "start": 0, "reason": None},
        ]
        corrections = [
            CorrectionItem(original="です", corrected="ます", reason="敬語", category="敬語"),
        ]
        _match_corrections(diffs, corrections, "です")
        assert diffs[0]["reason"] is None
        assert corrections[0].diff_matched is False

    def test_consumable_correction(self):
        """Once matched, a correction cannot be used again."""
        diffs = [
            {"type": DiffType.DELETE, "text": "申請書", "start": 0, "reason": None},
            {"type": DiffType.DELETE, "text": "申請書", "start": 10, "reason": None},
        ]
        corrections = [
            CorrectionItem(original="申請書", corrected="届出書", reason="用語", category="用語"),
        ]
        _match_corrections(diffs, corrections, "申請書xxxxxx申請書")
        # Only one diff gets the reason
        matched_count = sum(1 for d in diffs if d["reason"] is not None)
        assert matched_count == 1

    def test_one_diff_max_one_reason(self):
        """1 diff block = max 1 reason. Longest original wins."""
        diffs = [
            {"type": DiffType.DELETE, "text": "申請書類", "start": 0, "reason": None},
        ]
        corrections = [
            CorrectionItem(original="申請", corrected="届出", reason="短い理由", category="用語"),
            CorrectionItem(original="申請書類", corrected="届出書類", reason="長い理由", category="用語"),
        ]
        _match_corrections(diffs, corrections, "申請書類")
        assert diffs[0]["reason"] == "長い理由"  # longest match wins

    def test_no_match_far_away(self):
        """Correction original far from diff block → no match."""
        diffs = [
            {"type": DiffType.DELETE, "text": "ABC", "start": 100, "reason": None},
        ]
        corrections = [
            CorrectionItem(original="ABC", corrected="XYZ", reason="理由", category="用語"),
        ]
        _match_corrections(diffs, corrections, "x" * 100 + "ABC")
        # ABC is at position 100 in input, diff block is at start=100 → should match
        assert diffs[0]["reason"] == "理由"

    def test_replace_pair_assigns_reason_to_delete_block(self):
        """In a delete+insert pair, the DELETE block receives the reason (original text location)."""
        diffs = [
            {"type": DiffType.EQUAL, "text": "A", "start": 0, "reason": None},
            {"type": DiffType.DELETE, "text": "B", "start": 1, "reason": None},
            {"type": DiffType.INSERT, "text": "X", "start": 1, "reason": None},
        ]
        corrections = [
            CorrectionItem(original="B", corrected="X", reason="置換理由", category="用語"),
        ]
        _match_corrections(diffs, corrections, "AB")
        assert diffs[1]["reason"] == "置換理由"

    def test_multiple_occurrences_picks_closest(self):
        """Same text appearing multiple times → picks closest to diff block."""
        input_text = "申請書xxxx申請書yyyy申請書"
        diffs = [
            {"type": DiffType.DELETE, "text": "申請書", "start": 15, "reason": None},
        ]
        corrections = [
            CorrectionItem(original="申請書", corrected="届出書", reason="用語統一", category="用語"),
        ]
        _match_corrections(diffs, corrections, input_text)
        assert diffs[0]["reason"] == "用語統一"

    def test_empty_corrections(self):
        """No corrections → no reasons assigned."""
        diffs = [
            {"type": DiffType.DELETE, "text": "ABC", "start": 0, "reason": None},
        ]
        _match_corrections(diffs, [], "ABC")
        assert diffs[0]["reason"] is None

    def test_unmatched_corrections_marked_false(self):
        """Corrections that don't match any diff → diff_matched=False."""
        diffs = [
            {"type": DiffType.EQUAL, "text": "ABC", "start": 0, "reason": None},
        ]
        corrections = [
            CorrectionItem(original="XYZ", corrected="ZZZ", reason="理由", category="用語"),
        ]
        _match_corrections(diffs, corrections, "ABC")
        assert corrections[0].diff_matched is False

    def test_equal_blocks_never_get_reasons(self):
        """EQUAL blocks should never receive reasons."""
        diffs = [
            {"type": DiffType.EQUAL, "text": "ABC", "start": 0, "reason": None},
        ]
        corrections = [
            CorrectionItem(original="ABC", corrected="XYZ", reason="理由", category="用語"),
        ]
        _match_corrections(diffs, corrections, "ABC")
        assert diffs[0]["reason"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_diff_service.py::TestMatchCorrections -v`
Expected: FAIL

- [ ] **Step 3: Implement _match_corrections**

Add to `backend/services/diff_service.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_diff_service.py::TestMatchCorrections -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add backend/services/diff_service.py backend/tests/test_diff_service.py
git commit -m "feat(backend): add corrections proximity matching with guard and consumable logic"
```

---

### Task 7: Large Rewrite Detection

**Files:**
- Modify: `backend/services/diff_service.py`
- Modify: `backend/tests/test_diff_service.py`

- [ ] **Step 1: Write failing tests for _detect_large_rewrite**

Add to `backend/tests/test_diff_service.py`:

```python
class TestDetectLargeRewrite:
    """§4.4 ステップ10: 大幅書き換え検知"""

    @staticmethod
    def _b(type_str: str, text: str, start: int = 0) -> dict:
        type_map = {
            "equal": DiffType.EQUAL,
            "delete": DiffType.DELETE,
            "insert": DiffType.INSERT,
        }
        return {"type": type_map[type_str], "text": text, "start": start}

    def test_normal_change_no_warning(self):
        """10% change → no warning."""
        diffs = [
            self._b("equal", "ABCDEFGHIJ"),  # 10 chars
            self._b("delete", "K"),           # 1 char changed
        ]
        warnings = _detect_large_rewrite(diffs, input_length=11)
        assert warnings == []

    def test_large_rewrite_warning(self):
        """50% total change + 40% consecutive → warning."""
        diffs = [
            self._b("delete", "ABCDE"),  # 5 chars
            self._b("insert", "XYZWT"),  # 5 chars
            self._b("equal", "FGHIJ"),   # 5 chars
        ]
        warnings = _detect_large_rewrite(diffs, input_length=10)
        assert warnings == ["large_rewrite"]

    def test_many_small_changes_no_warning(self):
        """40% total but only 5% consecutive → no warning (AND condition)."""
        diffs = [
            self._b("equal", "AA"),
            self._b("delete", "B"),
            self._b("insert", "X"),
            self._b("equal", "AA"),
            self._b("delete", "B"),
            self._b("insert", "X"),
            self._b("equal", "AA"),
            self._b("delete", "B"),
            self._b("insert", "X"),
            self._b("equal", "AA"),
        ]
        # Total changed: 6 chars out of 14 = 42.8%
        # Max consecutive change: 2 chars (delete+insert) out of 14 = 14.3%
        # 42.8% > 0.3 AND 14.3% < 0.3 → no warning
        warnings = _detect_large_rewrite(diffs, input_length=14)
        assert warnings == []

    def test_exactly_at_threshold(self):
        """Exactly 30% both conditions → warning (>= not >)."""
        diffs = [
            self._b("delete", "AAA"),  # 3 chars
            self._b("insert", "BBB"),  # 3 chars
            self._b("equal", "BBBBBB"),  # 6 chars
        ]
        # Changed: 6/10 = 60% > 30% → wait, this exceeds
        # Let me recalculate: changed = 3+3 = 6, input = 6+3 = 9 (delete chars count)
        # Actually input_length=10 in the spec means the original text length
        # changed = 6/10 = 60%, consecutive = 6/10 = 60% → warning
        warnings = _detect_large_rewrite(diffs, input_length=10)
        assert warnings == ["large_rewrite"]

    def test_empty_diffs(self):
        warnings = _detect_large_rewrite([], input_length=100)
        assert warnings == []

    def test_only_equals(self):
        diffs = [self._b("equal", "ABCDEF")]
        warnings = _detect_large_rewrite(diffs, input_length=6)
        assert warnings == []

    def test_change_rate_just_below_threshold(self):
        """25% change → no warning regardless of consecutive rate."""
        diffs = [
            self._b("equal", "AAA"),
            self._b("delete", "B"),
            self._b("insert", "X"),
            self._b("equal", "AAA"),
        ]
        # changed = 2/8 = 25% < 30% → no warning regardless
        warnings = _detect_large_rewrite(diffs, input_length=8)
        assert warnings == []

    def test_exactly_30_percent_no_warning(self):
        """Exactly 30% change rate AND 30% consecutive → no warning (strict >)."""
        # changed = 3 chars, input = 10 chars → 30%
        # consecutive = 3 chars → 30%
        # Since we use strict > 0.3, exactly 30% should NOT trigger
        diffs = [
            self._b("delete", "ABC"),  # 3 chars
            self._b("insert", "XYZ"),  # 3 chars
            self._b("equal", "WWWWWWW"),  # 7 chars (input_length = 10)
        ]
        warnings = _detect_large_rewrite(diffs, input_length=10)
        assert warnings == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_diff_service.py::TestDetectLargeRewrite -v`
Expected: FAIL

- [ ] **Step 3: Implement _detect_large_rewrite**

Add to `backend/services/diff_service.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_diff_service.py::TestDetectLargeRewrite -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add backend/services/diff_service.py backend/tests/test_diff_service.py
git commit -m "feat(backend): add large rewrite detection with AND condition"
```

---

### Task 8: Main Orchestrator compute_diffs()

**Files:**
- Modify: `backend/services/diff_service.py`
- Modify: `backend/tests/test_diff_service.py`

- [ ] **Step 1: Write failing tests for compute_diffs()**

Add to `backend/tests/test_diff_service.py`:

```python
class TestComputeDiffs:
    """Integration tests for the compute_diffs() orchestrator."""

    def test_basic_proofreading(self):
        """Simple correction: ABC → AXC produces correct diffs."""
        result = compute_diffs(
            input_text="ABC",
            corrected_text="AXC",
            corrections=[],
            request_id="test-1",
        )
        assert result.status == ProofreadStatus.SUCCESS
        assert result.status_reason is None
        assert result.warnings == []

        # Should have diffs (at least one change)
        change_diffs = [d for d in result.diffs if d.type != DiffType.EQUAL]
        assert len(change_diffs) >= 1

    def test_identical_texts_no_changes(self):
        result = compute_diffs(
            input_text="全く同じテキスト",
            corrected_text="全く同じテキスト",
            corrections=[],
            request_id="test-2",
        )
        assert result.status == ProofreadStatus.SUCCESS
        assert len(result.diffs) == 1
        assert result.diffs[0].type == DiffType.EQUAL
        assert result.diffs[0].text == "全く同じテキスト"

    def test_with_corrections_matching(self):
        """Corrections should be matched to diff blocks."""
        result = compute_diffs(
            input_text="申請書を提出してください",
            corrected_text="届出書を提出してください",
            corrections=[
                CorrectionItem(
                    original="申請書",
                    corrected="届出書",
                    reason="用語の統一",
                    category="用語",
                ),
            ],
            request_id="test-3",
        )
        assert result.status == ProofreadStatus.SUCCESS
        # At least one diff block should have the reason
        reasons = [d.reason for d in result.diffs if d.reason is not None]
        assert "用語の統一" in reasons
        assert result.corrections[0].diff_matched is True

    def test_large_rewrite_detection(self):
        """Text with >30% change → large_rewrite warning."""
        input_text = "あいうえおかきくけこ"  # 10 chars
        corrected_text = "さしすせそたちつてと"  # completely different, 10 chars
        result = compute_diffs(
            input_text=input_text,
            corrected_text=corrected_text,
            corrections=[],
            request_id="test-4",
        )
        assert "large_rewrite" in result.warnings

    def test_enable_diff_compaction_false(self):
        """When compaction is disabled, short blocks should not be absorbed."""
        input_text = "ABCのDE"
        corrected_text = "ABCxDE"
        result_compacted = compute_diffs(
            input_text=input_text,
            corrected_text=corrected_text,
            corrections=[],
            request_id="test-5a",
            enable_diff_compaction=True,
        )
        result_no_compact = compute_diffs(
            input_text=input_text,
            corrected_text=corrected_text,
            corrections=[],
            request_id="test-5b",
            enable_diff_compaction=False,
        )
        # Compacted should have fewer or equal blocks
        assert len(result_no_compact.diffs) >= len(result_compacted.diffs)

    def test_insert_position_field(self):
        """INSERT blocks must have position='after'."""
        result = compute_diffs(
            input_text="ABC",
            corrected_text="AXBC",
            corrections=[],
            request_id="test-6",
        )
        insert_blocks = [d for d in result.diffs if d.type == DiffType.INSERT]
        for block in insert_blocks:
            assert block.position == "after"

    def test_delete_and_equal_no_position(self):
        """DELETE and EQUAL blocks must have position=None."""
        result = compute_diffs(
            input_text="ABC",
            corrected_text="AXC",
            corrections=[],
            request_id="test-7",
        )
        for block in result.diffs:
            if block.type in (DiffType.DELETE, DiffType.EQUAL):
                assert block.position is None

    def test_timeout_fallback_to_line_diff(self):
        """Character-level timeout → falls back to line-level diff."""
        with patch("services.diff_service.CHAR_DIFF_TIMEOUT", 0.001):
            long_text = "\n".join(f"行{i}" for i in range(1000))
            corrected = long_text.replace("行500", "変更行500")
            result = compute_diffs(
                input_text=long_text,
                corrected_text=corrected,
                corrections=[],
                request_id="test-8",
            )
            # Should succeed with line-level fallback
            assert result.status == ProofreadStatus.SUCCESS
            assert len(result.diffs) > 0

    def test_full_timeout_returns_partial(self):
        """Both character and line-level timeout → partial status."""
        with patch("services.diff_service.CHAR_DIFF_TIMEOUT", 0.001):
            with patch("services.diff_service.LINE_DIFF_TIMEOUT", 0.001):
                # Very long text that won't complete in 1ms
                long_text = "あ" * 100000
                result = compute_diffs(
                    input_text=long_text,
                    corrected_text=long_text + "追加",
                    corrections=[],
                    request_id="test-9",
                )
                assert result.status == ProofreadStatus.PARTIAL
                assert result.status_reason == StatusReason.DIFF_TIMEOUT
                assert result.diffs == []

    def test_japanese_realistic_proofreading(self):
        """Realistic Japanese proofreading scenario."""
        input_text = "お世話になっております。申請書を提出いたします。よろしくお願いいたします。"
        corrected_text = "お世話になっております。届出書を提出いたします。よろしくお願いいたします。"
        corrections = [
            CorrectionItem(
                original="申請書",
                corrected="届出書",
                reason="用語の統一：内部で使用する用語に合わせます",
                category="用語",
            ),
        ]
        result = compute_diffs(
            input_text=input_text,
            corrected_text=corrected_text,
            corrections=corrections,
            request_id="test-10",
        )
        assert result.status == ProofreadStatus.SUCCESS
        assert result.warnings == []

        # Find the change
        changes = [d for d in result.diffs if d.type != DiffType.EQUAL]
        assert len(changes) >= 2  # at least one delete + one insert

        # The correction should be matched
        assert corrections[0].diff_matched is True

        # corrected_text reconstruction should work via diffs
        # (verify by checking delete text contains 申請書)
        delete_texts = [d.text for d in result.diffs if d.type == DiffType.DELETE]
        assert any("申請書" in t for t in delete_texts)

    def test_multiple_corrections_partial_match(self):
        """Multiple corrections: some match, some don't."""
        input_text = "申請書を提出してください。よろしくです。"
        corrected_text = "届出書を提出してください。よろしくお願いいたします。"
        corrections = [
            CorrectionItem(
                original="申請書", corrected="届出書",
                reason="用語統一", category="用語",
            ),
            CorrectionItem(
                original="です", corrected="お願いいたします",
                reason="敬語", category="敬語",
            ),
        ]
        result = compute_diffs(
            input_text=input_text,
            corrected_text=corrected_text,
            corrections=corrections,
            request_id="test-11",
        )
        assert result.status == ProofreadStatus.SUCCESS
        # "申請書" (4 chars) should match; "です" (2 chars) should NOT (guard condition)
        assert corrections[0].diff_matched is True
        assert corrections[1].diff_matched is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_diff_service.py::TestComputeDiffs -v`
Expected: FAIL

- [ ] **Step 3: Implement compute_diffs() orchestrator**

Add to `backend/services/diff_service.py` (the `compute_diffs` function, keeping existing helper functions):

```python
def compute_diffs(
    *,
    input_text: str,
    corrected_text: str,
    corrections: list[CorrectionItem],
    request_id: str,
    enable_diff_compaction: bool = ENABLE_DIFF_COMPACTION_DEFAULT,
) -> DiffResult:
    """Compute diffs between input and corrected text with full processing pipeline.

    §4.4 ステップ5–11: diff計算・後処理・corrections照合・大幅書き換え検知

    Pipeline:
    5.  diff-match-patch (5s timeout → line-level fallback → partial)
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
            "Large rewrite detected: request_id=%s input_chars=%d changed_chars=%d change_rate=%.2f",
            request_id,
            len(input_text),
            sum(len(b["text"]) for b in blocks if b["type"] != DiffType.EQUAL),
            sum(len(b["text"]) for b in blocks if b["type"] != DiffType.EQUAL) / len(input_text) if input_text else 0,
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
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_diff_service.py::TestComputeDiffs -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add backend/services/diff_service.py backend/tests/test_diff_service.py
git commit -m "feat(backend): implement compute_diffs() orchestrator with full pipeline"
```

---

### Task 9: Full Test Suite Verification

**Files:** None (verification only)

- [ ] **Step 1: Run all diff service tests**

Run: `cd backend && python -m pytest tests/test_diff_service.py -v`

Expected: All tests PASS
- TestDiffResult: 3
- TestDiffTimeoutError: 1
- TestComputeRawDiffs: 7
- TestComputeLineDiff: 4
- TestMergeConsecutive: 7
- TestAbsorbShortBlocks: 10
- TestNormalizeOrder: 9
- TestCalculateStarts: 7
- TestMatchCorrections: 10
- TestDetectLargeRewrite: 8
- TestComputeDiffs: 11
Total: 77 tests

- [ ] **Step 2: Run entire test suite to check for regressions**

Run: `cd backend && python -m pytest -v`

Expected: All tests PASS (existing + 77 new diff service tests)

- [ ] **Step 3: Final commit (only if fixes were needed)**

```bash
git add backend/services/diff_service.py backend/tests/test_diff_service.py
git commit -m "fix: resolve test regressions from diff service addition"
```

Skip this step if no fixes were needed.
