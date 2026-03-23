import { useState, useEffect, useCallback, useRef } from 'react';

const BOOT_LINES = [
  'GOV_ASSIST BIOS v2.0 — POST check...',
  'Memory test... 8192K OK',
  'Loading AI kernel... kimi-k2.5',
  'Connecting to localhost:8000... CONNECTED',
  'Mounting SQLite database... MOUNTED',
  '[ SYSTEM READY ]',
];

const TYPE_DELAY = 80;
const SKIP_DELAY = 500;

export default function BootSequence({ onComplete }) {
  const [visibleLines, setVisibleLines] = useState([]);
  const [complete, setComplete] = useState(false);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    if (sessionStorage.getItem('govassist_boot_done') === '1') {
      onCompleteRef.current();
      return;
    }

    const lines = [...BOOT_LINES];
    let index = 0;
    let skipTimer = null;

    const timer = setInterval(() => {
      if (index < lines.length) {
        setVisibleLines(prev => [...prev, lines[index]]);
        index++;
      } else {
        clearInterval(timer);
        skipTimer = setTimeout(() => setComplete(true), SKIP_DELAY);
      }
    }, TYPE_DELAY);

    return () => {
      clearInterval(timer);
      if (skipTimer) clearTimeout(skipTimer);
    };
  }, []);

  const handleSkip = useCallback(() => {
    setComplete(true);
  }, []);

  useEffect(() => {
    if (complete) {
      sessionStorage.setItem('govassist_boot_done', '1');
      onCompleteRef.current();
    }
  }, [complete]);

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
        handleSkip();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [handleSkip]);

  if (complete) return null;

  return (
    <div
      onClick={handleSkip}
      role="status"
      aria-live="polite"
      style={{
        position: 'fixed',
        inset: 0,
        background: '#000',
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        fontFamily: "'Share Tech Mono', 'Courier New', monospace",
      }}
    >
      <div style={{ color: '#00ff41', fontSize: '13px', lineHeight: '2', padding: '20px' }}>
        {visibleLines.map((line, i) => (
          <div
            key={i}
            style={{
              textShadow: '0 0 4px #00ff41',
              opacity: line?.startsWith('[') ? 1 : 0.7,
            }}
          >
            {line}
          </div>
        ))}
        <div style={{ opacity: 0.3, marginTop: '8px' }}>click or press any key to skip</div>
      </div>
    </div>
  );
}
