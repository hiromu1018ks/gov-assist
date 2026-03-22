import { useState, useEffect, useCallback } from 'react';
import { apiGet, apiPut } from '../../api/client';
import { loadSettings, saveSettings } from '../../utils/storage';

const DOCUMENT_TYPES = [
  { value: 'email', label: 'メール' },
  { value: 'report', label: '報告書' },
  { value: 'official', label: '公文書' },
  { value: 'other', label: 'その他' },
];

const OPTIONS = [
  { key: 'typo', label: '誤字・脱字・変換ミスの検出' },
  { key: 'keigo', label: '敬語・丁寧語の適切さチェック' },
  { key: 'terminology', label: '公文書用語・表現への統一（例：「ください」→「くださいますよう」）' },
  { key: 'style', label: '文体の統一（です・ます調 / である調）' },
  { key: 'legal', label: '法令・条例用語の確認' },
  { key: 'readability', label: '文章の読みやすさ・論理構成の改善提案' },
];

export default function Settings() {
  // --- Client settings state (lazy init from localStorage) ---
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(() => loadSettings().model);
  const [documentType, setDocumentType] = useState(() => loadSettings().document_type);
  const [options, setOptions] = useState(() => loadSettings().options);

  // --- Server settings state ---
  const [historyLimit, setHistoryLimit] = useState(50);
  const [savingServer, setSavingServer] = useState(false);
  const [serverMessage, setServerMessage] = useState(null);

  // --- Error state ---
  const [modelsError, setModelsError] = useState(null);
  const [settingsError, setSettingsError] = useState(null);

  // --- Fetch on mount ---
  useEffect(() => {
    apiGet('/api/models')
      .then((data) => {
        if (data.models?.length > 0) {
          setModels(data.models);
          const ids = data.models.map((m) => m.model_id);
          const current = loadSettings().model;
          if (!ids.includes(current)) {
            const fallback = data.models[0].model_id;
            setSelectedModel(fallback);
            saveSettings({ ...loadSettings(), model: fallback });
          }
        }
      })
      .catch(() => setModelsError('モデル一覧の取得に失敗しました。'));

    apiGet('/api/settings')
      .then((data) => setHistoryLimit(data.history_limit))
      .catch(() => setSettingsError('サーバー設定の取得に失敗しました。'));
  }, []);

  // --- Client settings handlers (localStorage, immediate) ---
  const handleModelChange = useCallback((e) => {
    const value = e.target.value;
    setSelectedModel(value);
    saveSettings({ ...loadSettings(), model: value });
  }, []);

  const handleDocumentTypeChange = useCallback((e) => {
    const value = e.target.value;
    setDocumentType(value);
    saveSettings({ ...loadSettings(), document_type: value });
  }, []);

  const handleOptionChange = useCallback((key) => {
    const next = { ...options, [key]: !options[key] };
    setOptions(next);
    saveSettings({ ...loadSettings(), options: next });
  }, [options]);

  // --- Server settings handler (PUT API) ---
  const handleSaveServerSettings = useCallback(async () => {
    setSavingServer(true);
    setServerMessage(null);
    try {
      await apiPut('/api/settings', { history_limit: Number(historyLimit) });
      setServerMessage({ type: 'success', text: 'サーバー設定を保存しました。' });
    } catch {
      setServerMessage({ type: 'error', text: 'サーバー設定の保存に失敗しました。' });
    } finally {
      setSavingServer(false);
    }
  }, [historyLimit]);

  return (
    <div className="settings">
      <h2>設定</h2>

      {/* --- Client Settings --- */}
      <section className="settings__section">
        <h3 className="settings__section-title">AI モデル選択</h3>
        {modelsError ? (
          <p className="message message--error">{modelsError}</p>
        ) : (
          <div className="form-group">
            <label className="label" htmlFor="settings-model">AI モデル</label>
            <select
              id="settings-model"
              className="select"
              value={selectedModel}
              onChange={handleModelChange}
            >
              {models.map((m) => (
                <option key={m.model_id} value={m.model_id}>
                  {m.display_name}
                </option>
              ))}
            </select>
          </div>
        )}
      </section>

      <section className="settings__section">
        <h3 className="settings__section-title">校正の初期設定</h3>

        <div className="form-group">
          <label className="label" htmlFor="settings-doc-type">デフォルト文書種別</label>
          <select
            id="settings-doc-type"
            className="select"
            value={documentType}
            onChange={handleDocumentTypeChange}
          >
            {DOCUMENT_TYPES.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        <fieldset className="option-panel">
          <legend className="option-panel__legend">デフォルト校正オプション</legend>
          <div className="option-panel__grid">
            {OPTIONS.map(({ key, label }) => (
              <label key={key} className="checkbox">
                <input
                  type="checkbox"
                  className="checkbox__input"
                  checked={!!options[key]}
                  onChange={() => handleOptionChange(key)}
                />
                {label}
              </label>
            ))}
          </div>
        </fieldset>
      </section>

      {/* --- Server Settings --- */}
      <section className="settings__section">
        <h3 className="settings__section-title">サーバー設定</h3>
        {settingsError ? (
          <p className="message message--error">{settingsError}</p>
        ) : (
          <>
            <div className="form-group">
              <label className="label" htmlFor="settings-history-limit">履歴保存件数上限</label>
              <input
                id="settings-history-limit"
                className="input"
                type="number"
                min="1"
                max="200"
                value={historyLimit}
                onChange={(e) => setHistoryLimit(Number(e.target.value))}
              />
              <p className="settings__hint">1〜200件で設定してください。古い履歴から自動削除されます。</p>
            </div>
            <button
              className="btn btn--primary"
              onClick={handleSaveServerSettings}
              disabled={savingServer}
            >
              {savingServer ? '保存中...' : 'サーバー設定を保存'}
            </button>
            {serverMessage && (
              <p className={`message mt-sm ${serverMessage.type === 'error' ? 'message--error' : 'message--success'}`}>
                {serverMessage.text}
              </p>
            )}
          </>
        )}
      </section>
    </div>
  );
}
