import { useState, useEffect, useCallback } from 'react';
import { apiGet, apiDelete } from '../../api/client';

const DOC_TYPE_LABELS = {
  email: 'メール',
  report: '報告書',
  official: '公文書',
  other: 'その他',
};

const PAGE_SIZE = 20;

function formatDate(iso) {
  const d = new Date(iso);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const h = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${y}/${m}/${day} ${h}:${min}`;
}

export default function HistoryList({ onSelectItem }) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [docType, setDocType] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [appliedQuery, setAppliedQuery] = useState('');
  const [appliedDocType, setAppliedDocType] = useState('');
  const [appliedDateFrom, setAppliedDateFrom] = useState('');
  const [appliedDateTo, setAppliedDateTo] = useState('');
  const [offset, setOffset] = useState(0);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (appliedQuery) params.set('q', appliedQuery);
      if (appliedDocType) params.set('document_type', appliedDocType);
      if (appliedDateFrom) params.set('date_from', appliedDateFrom);
      if (appliedDateTo) params.set('date_to', appliedDateTo);
      params.set('limit', String(PAGE_SIZE));
      params.set('offset', String(offset));

      const data = await apiGet(`/api/history?${params.toString()}`);
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err.message || '履歴の取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  }, [appliedQuery, appliedDocType, appliedDateFrom, appliedDateTo, offset]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleSearch = (e) => {
    e.preventDefault();
    setAppliedQuery(searchQuery);
    setAppliedDocType(docType);
    setAppliedDateFrom(dateFrom);
    setAppliedDateTo(dateTo);
    setOffset(0);
  };

  const handleClearFilters = () => {
    setSearchQuery('');
    setDocType('');
    setDateFrom('');
    setDateTo('');
    setAppliedQuery('');
    setAppliedDocType('');
    setAppliedDateFrom('');
    setAppliedDateTo('');
    setOffset(0);
  };

  const handleDeleteItem = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm('この履歴を削除しますか？')) return;
    try {
      await apiDelete(`/api/history/${id}`);
      fetchHistory();
    } catch {
      setError('削除に失敗しました。');
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm('全ての履歴を削除しますか？この操作は取り消せません。')) return;
    try {
      await apiDelete('/api/history');
      setItems([]);
      setTotal(0);
      setOffset(0);
    } catch {
      setError('全件削除に失敗しました。');
    }
  };

  const hasNextPage = offset + PAGE_SIZE < total;
  const hasPrevPage = offset > 0;
  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + PAGE_SIZE, total);

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" role="status"></div>
        <span>読み込み中...</span>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-md">
        <h2>校正履歴</h2>
        {total > 0 && (
          <button className="btn btn--danger btn--sm" onClick={handleDeleteAll} type="button">
            全件削除
          </button>
        )}
      </div>

      <form className="history-filters" onSubmit={handleSearch}>
        <div className="history-filters__row">
          <div className="history-filters__search">
            <input className="input" type="text" placeholder="キーワード検索" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
          </div>
          <div className="history-filters__type">
            <label className="sr-only" htmlFor="history-filter-type">文書種別</label>
            <select className="select" id="history-filter-type" value={docType} onChange={(e) => setDocType(e.target.value)}>
              <option value="">全ての種別</option>
              <option value="email">メール</option>
              <option value="report">報告書</option>
              <option value="official">公文書</option>
              <option value="other">その他</option>
            </select>
          </div>
          <div className="history-filters__date">
            <input className="input" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} aria-label="開始日" />
            <span>〜</span>
            <input className="input" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} aria-label="終了日" />
          </div>
          <button className="btn btn--primary btn--sm" type="submit">検索</button>
          <button className="btn btn--secondary btn--sm" type="button" onClick={handleClearFilters}>クリア</button>
        </div>
      </form>

      {error && <div className="message message--error mt-md" role="alert">{error}</div>}

      {!error && items.length === 0 && (
        <div className="history-list__empty mt-lg">
          <p>履歴がありません。</p>
        </div>
      )}

      {!error && items.length > 0 && (
        <>
          <div className="history-list mt-md">
            {items.map((item) => (
              <div
                key={item.id}
                className="history-item"
                onClick={() => onSelectItem(item.id)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelectItem(item.id); } }}
                role="button"
                tabIndex={0}
              >
                <div className="history-item__header">
                  <span className="history-item__date">{formatDate(item.created_at)}</span>
                  <span className="badge">{DOC_TYPE_LABELS[item.document_type] || item.document_type}</span>
                  {item.truncated && <span className="badge badge--warning">⚠ 詳細省略</span>}
                </div>
                <p className="history-item__preview">{item.preview}</p>
                <div className="history-item__meta">
                  <span>{item.model}</span>
                  {item.memo && <span className="history-item__memo">メモ: {item.memo}</span>}
                </div>
                <button
                  className="btn btn--danger btn--sm history-item__delete"
                  onClick={(e) => handleDeleteItem(e, item.id)}
                  type="button"
                  aria-label="削除"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          <div className="history-list__pagination mt-md">
            <span>{pageStart}-{pageEnd}件 / 全{total}件</span>
            <div className="flex gap-sm">
              <button className="btn btn--secondary btn--sm" disabled={!hasPrevPage} onClick={() => setOffset((o) => o - PAGE_SIZE)} type="button">前へ</button>
              <button className="btn btn--secondary btn--sm" disabled={!hasNextPage} onClick={() => setOffset((o) => o + PAGE_SIZE)} type="button">次へ</button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
