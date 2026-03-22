import { useState } from 'react';
import { HighlightView, CompareView } from './DiffView';

const TABS = [
  { id: 'highlight', label: '① ハイライト表示' },
  { id: 'compare', label: '② 比較表示' },
  { id: 'comments', label: '③ コメント一覧' },
];

/**
 * Determine which tabs are available based on result status.
 * §3.3.4 status branching table.
 */
function getAvailableTabs(result) {
  if (result.status === 'error') return [];
  if (result.status === 'partial') {
    if (result.status_reason === 'parse_fallback') return [TABS[2]];
    if (result.status_reason === 'diff_timeout') {
      return result.diffs && result.diffs.length > 0 ? TABS : [TABS[2]];
    }
  }
  return TABS;
}

/**
 * Get status message for partial/error states.
 * Returns { type, text } or null.
 */
function getStatusMessage(result) {
  if (result.status === 'partial') {
    if (result.status_reason === 'diff_timeout') {
      if (result.diffs && result.diffs.length > 0) {
        return {
          type: 'info',
          text: '差分計算がタイムアウトしました。行単位での差分を表示しています。',
        };
      }
      return {
        type: 'info',
        text: '差分計算に失敗しました。校正済みテキストのみ表示します。',
      };
    }
    if (result.status_reason === 'parse_fallback') {
      return {
        type: 'info',
        text: 'AI の応答形式が不完全でした。取得できたテキストのみ表示します。',
      };
    }
  }
  if (result.status === 'error') {
    return { type: 'error', text: '校正結果を取得できませんでした。' };
  }
  return null;
}

/**
 * Tab ③: Comments list — displays all corrections as a numbered list.
 * Each item shows original, corrected, reason, category.
 * diff_matched: false items get a badge.
 */
function CorrectionList({ corrections }) {
  if (!corrections || corrections.length === 0) {
    return <p className="result-view__empty">修正箇所はありません。</p>;
  }

  return (
    <ol className="correction-list">
      {corrections.map((c, i) => (
        <li key={i} className="correction-item">
          <div className="correction-item__header">
            <span className="correction-item__number">{i + 1}</span>
            <span className="correction-item__category">{c.category}</span>
            {c.diff_matched === false && (
              <span className="badge badge--info">参考（AI推定）</span>
            )}
          </div>
          <div className="correction-item__pair">
            <div className="correction-item__original">
              <span className="correction-item__label">修正前：</span>
              <span className="diff-delete">{c.original}</span>
            </div>
            <div className="correction-item__corrected">
              <span className="correction-item__label">修正後：</span>
              <span className="diff-insert">{c.corrected}</span>
            </div>
          </div>
          {c.reason && (
            <div className="correction-item__reason">
              <span className="correction-item__label">理由：</span>
              {c.reason}
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}

/**
 * ResultView — displays proofreading results with 3-tab framework.
 *
 * Props:
 *   result: ProofreadResponse object or null
 *   onRetry: callback for retry button (error state)
 *
 * Status branching per design spec §3.3.4:
 *   success: all 3 tabs, summary, notice
 *   partial + diff_timeout + diffs: all 3 tabs + info message
 *   partial + diff_timeout + no diffs: tab ③ only + corrected_text
 *   partial + parse_fallback: tab ③ only + corrected_text
 *   error: no tabs, error message + retry button
 */
export default function ResultView({ result, onRetry }) {
  // IMPORTANT: useState must be called before any conditional returns
  // to comply with React's Rules of Hooks (hooks must not be conditional).
  // The initial value computes available tabs from result, defaulting to empty.
  const [activeTab, setActiveTab] = useState(() => {
    if (!result) return null;
    const tabs = getAvailableTabs(result);
    return tabs.length > 0 ? tabs[0].id : null;
  });

  if (!result) return null;

  const availableTabs = getAvailableTabs(result);
  const statusMessage = getStatusMessage(result);
  const hasLargeRewrite = result.warnings && result.warnings.includes('large_rewrite');
  const showCorrectedText =
    result.status === 'partial' && (!result.diffs || result.diffs.length === 0);

  // Error state: no tabs, error message + retry
  if (result.status === 'error') {
    return (
      <div className="result-view mt-lg">
        <div className="message message--error">{statusMessage.text}</div>
        {onRetry && (
          <button className="btn btn--secondary mt-md" onClick={onRetry}>
            再試行
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="result-view mt-lg">
      {/* Large rewrite warning */}
      {hasLargeRewrite && (
        <div className="message message--warning mb-md">
          ⚠️ AI が広範囲を書き換えました。内容を十分ご確認ください。
        </div>
      )}

      {/* Status reason message */}
      {statusMessage && (
        <div className={`message message--${statusMessage.type} mb-md`}>
          {statusMessage.text}
        </div>
      )}

      {/* Summary */}
      {result.summary && (
        <div className="result-view__summary mb-md">{result.summary}</div>
      )}

      {/* Diff-based notice (shown in all non-error states) */}
      <div className="result-view__notice mb-md">
        表示は差分ベースです。コメントは AI 推定であり正確でない場合があります。
      </div>

      {/* Corrected text (prominent display for partial states without diffs) */}
      {showCorrectedText && result.corrected_text && (
        <div className="result-view__corrected-text mb-md">
          <h4>校正済みテキスト</h4>
          <pre className="result-view__corrected-text-body">
            {result.corrected_text}
          </pre>
        </div>
      )}

      {/* Tab bar + content */}
      {availableTabs.length > 0 && (
        <>
          <div className="tabs" role="tablist">
            {availableTabs.map((tab) => (
              <button
                key={tab.id}
                role="tab"
                className={`tab ${activeTab === tab.id ? 'tab--active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
                aria-selected={activeTab === tab.id}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="result-view__panel" role="tabpanel">
            {activeTab === 'highlight' && (
              <HighlightView diffs={result.diffs} />
            )}
            {activeTab === 'compare' && (
              <CompareView diffs={result.diffs} />
            )}
            {activeTab === 'comments' && (
              <CorrectionList corrections={result.corrections} />
            )}
          </div>
        </>
      )}
    </div>
  );
}
