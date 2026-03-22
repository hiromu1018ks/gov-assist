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
