"""Tests for diff service."""

import pytest
from concurrent.futures import TimeoutError as FuturesTimeoutError
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
        """ABC -> AXC should produce EQUAL, DELETE, INSERT, EQUAL."""
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

    @patch("services.diff_service.ThreadPoolExecutor")
    def test_timeout_raises_error(self, mock_executor_cls):
        """Mock ThreadPoolExecutor to simulate timeout on char diff."""
        mock_future = MagicMock()
        mock_future.result.side_effect = FuturesTimeoutError()
        mock_executor = MagicMock()
        mock_executor.__enter__ = MagicMock(return_value=mock_executor)
        mock_executor.__exit__ = MagicMock(return_value=False)
        mock_executor.submit.return_value = mock_future
        mock_executor_cls.return_value = mock_executor

        with pytest.raises(DiffTimeoutError):
            _compute_raw_diffs("ABC", "AXC")


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

    @patch("services.diff_service.ThreadPoolExecutor")
    def test_line_diff_timeout(self, mock_executor_cls):
        """Mock ThreadPoolExecutor to simulate timeout on line diff."""
        mock_future = MagicMock()
        mock_future.result.side_effect = FuturesTimeoutError()
        mock_executor = MagicMock()
        mock_executor.__enter__ = MagicMock(return_value=mock_executor)
        mock_executor.__exit__ = MagicMock(return_value=False)
        mock_executor.submit.return_value = mock_future
        mock_executor_cls.return_value = mock_executor

        with pytest.raises(DiffTimeoutError):
            _compute_line_diff("ABC\nDEF", "ABC\nXYZ")


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
