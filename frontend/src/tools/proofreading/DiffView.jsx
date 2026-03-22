import { useRef, useCallback } from 'react';

/**
 * DiffView — diff-based display components for proofreading results.
 *
 * §3.3.4: Frontend renders diffs in reduce-style sequential order.
 * `start` index is NOT used for rendering; only array order matters.
 * All rendering via standard React data binding (no dangerouslySetInnerHTML).
 */

/**
 * Tab ① Highlight View
 *
 * Displays original text with color-coded highlights for delete/insert blocks.
 * Mouse hover shows nearby-matched reason as tooltip (data-tooltip attribute).
 *
 * Props:
 *   diffs: array of { type: 'equal'|'delete'|'insert', text, start, position, reason }
 */
export function HighlightView({ diffs }) {
  if (!diffs || diffs.length === 0) {
    return (
      <div className="diff-highlight">
        <p className="diff-highlight__empty">表示する差分がありません。</p>
      </div>
    );
  }

  return (
    <div className="diff-highlight">
      {diffs.map((diff, i) => {
        const className =
          diff.type === 'delete'
            ? 'diff-delete'
            : diff.type === 'insert'
              ? 'diff-insert'
              : '';

        const tooltipProps =
          diff.reason
            ? { className: `${className} tooltip`, 'data-tooltip': diff.reason }
            : { className };

        return <span key={i} {...tooltipProps}>{diff.text}</span>;
      })}
    </div>
  );
}

/**
 * Tab ② Compare View
 *
 * Side-by-side display: left = before (equal + delete), right = after (equal + insert).
 * Synchronized scrolling between panels via onScroll event.
 *
 * Props:
 *   diffs: array of { type, text, start, position, reason }
 */
export function CompareView({ diffs }) {
  const leftRef = useRef(null);
  const rightRef = useRef(null);
  const isScrolling = useRef(false);

  const handleScroll = useCallback((source) => {
    if (isScrolling.current) return;
    isScrolling.current = true;

    const target = source === 'left' ? rightRef.current : leftRef.current;
    if (target) {
      target.scrollTop = source === 'left' ? leftRef.current.scrollTop : rightRef.current.scrollTop;
    }

    requestAnimationFrame(() => {
      isScrolling.current = false;
    });
  }, []);

  if (!diffs || diffs.length === 0) {
    return (
      <div className="diff-highlight">
        <p className="diff-highlight__empty">表示する差分がありません。</p>
      </div>
    );
  }

  return (
    <div className="diff-compare">
      <div
        className="diff-compare__panel diff-compare__panel--scroll-sync"
        ref={leftRef}
        onScroll={() => handleScroll('left')}
      >
        <div className="diff-compare__panel-header">修正前</div>
        {diffs.map((diff, i) => {
          if (diff.type === 'insert') return null;
          const className = diff.type === 'delete' ? 'diff-delete' : '';
          const tooltipProps = diff.reason
            ? { className: `${className} tooltip`, 'data-tooltip': diff.reason }
            : { className };
          return <span key={i} {...tooltipProps}>{diff.text}</span>;
        })}
      </div>
      <div
        className="diff-compare__panel diff-compare__panel--scroll-sync"
        ref={rightRef}
        onScroll={() => handleScroll('right')}
      >
        <div className="diff-compare__panel-header">修正後</div>
        {diffs.map((diff, i) => {
          if (diff.type === 'delete') return null;
          const className = diff.type === 'insert' ? 'diff-insert' : '';
          const tooltipProps = diff.reason
            ? { className: `${className} tooltip`, 'data-tooltip': diff.reason }
            : { className };
          return <span key={i} {...tooltipProps}>{diff.text}</span>;
        })}
      </div>
    </div>
  );
}
