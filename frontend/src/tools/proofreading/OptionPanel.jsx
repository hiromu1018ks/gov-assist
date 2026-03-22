import { useState, useRef, useCallback } from 'react';
import { loadSettings } from '../../utils/storage';

const OPTIONS = [
  { key: 'typo', label: '誤字・脱字・変換ミスの検出' },
  { key: 'keigo', label: '敬語・丁寧語の適切さチェック' },
  { key: 'terminology', label: '公文書用語・表現への統一（例：「ください」→「くださいますよう」）' },
  { key: 'style', label: '文体の統一（です・ます調 / である調）' },
  { key: 'legal', label: '法令・条例用語の確認' },
  { key: 'readability', label: '文章の読みやすさ・論理構成の改善提案' },
];

export default function OptionPanel({ onChange, disabled }) {
  const [options, setOptions] = useState(() => loadSettings().options || {});
  // Ref to avoid stale closure in handleChange — consistent with InputArea.jsx pattern
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const handleChange = useCallback((key) => {
    const prev = optionsRef.current;
    const next = { ...prev, [key]: !prev[key] };
    setOptions(next);
    onChange?.(next);
  }, [onChange]);

  return (
    <fieldset className="option-panel" disabled={disabled}>
      <legend className="option-panel__legend">校正オプション</legend>
      <div className="option-panel__grid">
        {OPTIONS.map(({ key, label }) => (
          <label key={key} className="checkbox">
            <input
              type="checkbox"
              className="checkbox__input"
              checked={!!options[key]}
              onChange={() => handleChange(key)}
            />
            {label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
