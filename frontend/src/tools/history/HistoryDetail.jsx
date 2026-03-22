import { useState, useEffect, useCallback } from 'react';
import { apiGet, apiPatch, apiDelete } from '../../api/client';
import ResultView from '../proofreading/ResultView';

const DOC_TYPE_LABELS = {
  email: 'メール',
  report: '報告書',
  official: '公文書',
  other: 'その他',
};

function formatDate(iso) {
  const d = new Date(iso);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const h = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${y}/${m}/${day} ${h}:${min}`;
}

export default function HistoryDetail({ historyId, onBack }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [memo, setMemo] = useState('');
  const [memoSaving, setMemoSaving] = useState(false);
  const [memoSuccess, setMemoSuccess] = useState(false);

  const fetchDetail = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet(`/api/history/${historyId}`);
      setDetail(data);
      setMemo(data.memo || '');
    } catch (err) {
      setError(err.message || '履歴の取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  }, [historyId]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const handleSaveMemo = async () => {
    setMemoSaving(true);
    setMemoSuccess(false);
    try {
      const updated = await apiPatch(`/api/history/${historyId}`, { memo });
      setDetail(updated);
      setMemoSuccess(true);
      setTimeout(() => setMemoSuccess(false), 2000);
    } catch {
      setError('メモの保存に失敗しました。');
    } finally {
      setMemoSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('この履歴を削除しますか？')) return;
    try {
      await apiDelete(`/api/history/${historyId}`);
      onBack();
    } catch {
      setError('削除に失敗しました。');
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" role="status"></div>
        <span>読み込み中...</span>
      </div>
    );
  }

  if (!detail) {
    return (
      <div>
        <button className="btn btn--secondary mb-md" onClick={onBack} type="button">
          ← 一覧に戻る
        </button>
        <div className="message message--error">{error || '履歴が見つかりませんでした。'}</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-md">
        <button className="btn btn--secondary" onClick={onBack} type="button">
          ← 一覧に戻る
        </button>
        <button className="btn btn--danger btn--sm" onClick={handleDelete} type="button">
          削除
        </button>
      </div>

      <h2>校正履歴詳細</h2>

      {error && <div className="message message--error mt-md" role="alert">{error}</div>}

      {detail.truncated && (
        <div className="message message--warning mt-md">
          データサイズ超過のため校正詳細は保存されていません。校正済みテキストのみ表示します。
        </div>
      )}

      <div className="history-detail__meta mt-md">
        <span>{formatDate(detail.created_at)}</span>
        <span className="badge ml-sm">{DOC_TYPE_LABELS[detail.document_type] || detail.document_type}</span>
        <span className="ml-sm">{detail.model}</span>
      </div>

      <div className="history-detail__section mt-md">
        <h3>入力テキスト</h3>
        <pre className="history-detail__input-text">{detail.input_text}</pre>
      </div>

      {!detail.truncated && (
        <ResultView result={detail.result} />
      )}

      {detail.truncated && detail.result?.corrected_text && (
        <div className="history-detail__section mt-md">
          <h3>校正済みテキスト</h3>
          <pre className="history-detail__input-text">{detail.result.corrected_text}</pre>
        </div>
      )}

      <div className="history-detail__memo mt-lg">
        <label className="label" htmlFor="history-memo">メモ</label>
        <textarea
          className="textarea"
          id="history-memo"
          value={memo}
          onChange={(e) => setMemo(e.target.value)}
          rows={3}
          placeholder="メモを入力..."
        />
        <div className="mt-sm">
          <button
            className="btn btn--secondary btn--sm"
            onClick={handleSaveMemo}
            disabled={memoSaving}
            type="button"
          >
            {memoSaving ? '保存中...' : memoSuccess ? '保存しました' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
