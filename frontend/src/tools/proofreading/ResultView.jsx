import { useState } from 'react';
import FullTextView from './FullTextView';

const TABS = [
  { id: 'before', label: '校正前' },
  { id: 'after', label: '校正後' },
  { id: 'diff', label: '差分' },
];

/**
 * Determine which tabs are available based on result status.
 * §3.3.4 status branching table.
 */
function getAvailableTabs(result) {
  if (result.status === 'error') return [];
  if (result.status === 'partial') {
    if (result.status_reason === 'parse_fallback') return [TABS[1], TABS[2]];
    if (result.status_reason === 'diff_timeout') {
      return result.diffs && result.diffs.length > 0 ? TABS : [TABS[1], TABS[2]];
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
 * DiffListView — displays corrections as a numbered list with optional summary and warnings.
 * Each item shows original, corrected, reason, category.
 * diff_matched: false items get a badge.
 */
function DiffListView({ corrections, summary, warnings }) {
  const hasLargeRewrite = warnings && warnings.includes('large_rewrite');

  return (
    <div>
      {summary && (
        <div className="diff-list-summary">{summary}</div>
      )}
      {hasLargeRewrite && (
        <div className="diff-list-warning">
          ⚠️ AI が広範囲を書き換えました。内容を十分ご確認ください。
        </div>
      )}
      {!corrections || corrections.length === 0 ? (
        <p className="result-view__empty">修正箇所はありません。</p>
      ) : (
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
      )}
    </div>
  );
}

/**
 * ResultView — displays proofreading results with 3-tab framework.
 *
 * Props:
 *   result: ProofreadResponse object or null
 *   originalText: the original text before proofreading (default '')
 *   onRetry: callback for retry button (error state)
 *
 * Status branching per design spec §3.3.4:
 *   success: all 3 tabs, summary, notice
 *   partial + diff_timeout + diffs: all 3 tabs + info message
 *   partial + diff_timeout + no diffs: after + diff tabs
 *   partial + parse_fallback: after + diff tabs
 *   error: no tabs, error message + retry button
 */
export default function ResultView({ result, originalText = '', onRetry }) {
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
      {/* Status reason message */}
      {statusMessage && (
        <div className={`message message--${statusMessage.type} mb-md`}>
          {statusMessage.text}
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
            {activeTab === 'before' && (
              <FullTextView text={originalText} label="校正前" />
            )}
            {activeTab === 'after' && (
              <FullTextView text={result.corrected_text} label="校正後" />
            )}
            {activeTab === 'diff' && (
              <DiffListView
                corrections={result.corrections}
                summary={result.summary}
                warnings={result.warnings}
              />
            )}
          </div>
        </>
      )}

      {/* Notice (below tabs, all non-error states) */}
      <div className="result-view__notice mt-md">
        ※ 差分タブのコメントは AI 推定であり、正確でない場合があります。
      </div>
    </div>
  );
}
