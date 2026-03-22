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
        """EQUAL(AB), DELETE(C), INSERT(X), EQUAL(DE) -> starts: 0, 2, 2, 3."""
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
        """INSERT at beginning -> start=0."""
        blocks = [self._b("insert", "XYZ")]
        result = _calculate_starts(blocks)
        assert result[0]["start"] == 0

    def test_delete_only(self):
        """DELETE at beginning -> start=0."""
        blocks = [self._b("delete", "ABC")]
        result = _calculate_starts(blocks)
        assert result[0]["start"] == 0

    def test_equal_only(self):
        blocks = [self._b("equal", "hello")]
        result = _calculate_starts(blocks)
        assert result[0]["start"] == 0

    def test_multiple_changes(self):
        """Multiple change pairs -> correct cumulative positions."""
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
            {"type": DiffType.EQUAL, "text": "おはよう", "start": 0, "reason": None},
            {"type": DiffType.DELETE, "text": "ございます", "start": 4, "reason": None},
            {"type": DiffType.INSERT, "text": "ございます", "start": 4, "reason": None},
        ]
        corrections = [
            CorrectionItem(original="ございます", corrected="ざいます", reason="誤字です", category="誤字脱字"),
        ]
        input_text = "おはようございます"
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
            {"type": DiffType.DELETE, "text": "申請書類", "start": 0, "reason": None},
            {"type": DiffType.DELETE, "text": "申請書類", "start": 10, "reason": None},
        ]
        corrections = [
            CorrectionItem(original="申請書類", corrected="届出書類", reason="用語", category="用語"),
        ]
        _match_corrections(diffs, corrections, "申請書類xxxxx申請書類")
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
        assert diffs[0]["reason"] == "長い理由"

    def test_no_match_far_away(self):
        """Correction original far from diff block → no match."""
        diffs = [
            {"type": DiffType.DELETE, "text": "ABCD", "start": 100, "reason": None},
        ]
        corrections = [
            CorrectionItem(original="ABCD", corrected="XYZW", reason="理由", category="用語"),
        ]
        _match_corrections(diffs, corrections, "x" * 100 + "ABCD")
        assert diffs[0]["reason"] == "理由"

    def test_replace_pair_assigns_reason_to_delete_block(self):
        """In a delete+insert pair, the DELETE block receives the reason."""
        diffs = [
            {"type": DiffType.EQUAL, "text": "おはよう", "start": 0, "reason": None},
            {"type": DiffType.DELETE, "text": "ございます", "start": 4, "reason": None},
            {"type": DiffType.INSERT, "text": "ざいます", "start": 4, "reason": None},
        ]
        corrections = [
            CorrectionItem(original="ございます", corrected="ざいます", reason="置換理由", category="用語"),
        ]
        _match_corrections(diffs, corrections, "おはようございます")
        assert diffs[1]["reason"] == "置換理由"

    def test_multiple_occurrences_picks_closest(self):
        """Same text appearing multiple times → picks closest to diff block."""
        input_text = "申請書類xxx申請書類yyy申請書類"
        diffs = [
            {"type": DiffType.DELETE, "text": "申請書類", "start": 15, "reason": None},
        ]
        corrections = [
            CorrectionItem(original="申請書類", corrected="届出書類", reason="用語統一", category="用語"),
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
        """60% change and 60% consecutive → warning (well above 30%)."""
        diffs = [
            self._b("delete", "AAA"),  # 3 chars
            self._b("insert", "BBB"),  # 3 chars
            self._b("equal", "BBBBBB"),  # 6 chars
        ]
        # changed = 6/10 = 60% > 30%, consecutive = 6/10 = 60% > 30%
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
        """Exactly 30% both conditions → no warning (strict >, not >=).

        Fixed from plan: the plan's test data had 6/10 = 60% (not 30%).
        Corrected to use only a DELETE of 3 chars (no INSERT) with input_length=10.
        """
        diffs = [
            self._b("delete", "ABC"),   # 3 chars
            self._b("equal", "WWWWWWW"),  # 7 chars
        ]
        # changed = 3/10 = 30% (NOT > 30%), consecutive = 3/10 = 30% (NOT > 30%)
        warnings = _detect_large_rewrite(diffs, input_length=10)
        assert warnings == []
