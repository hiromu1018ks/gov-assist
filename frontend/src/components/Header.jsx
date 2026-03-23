import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadSettings, saveSettings } from '../utils/storage';
import { apiGet } from '../api/client';

const DEFAULT_MODEL = { model_id: 'kimi-k2.5', display_name: 'Kimi K2.5' };

function Header() {
  const navigate = useNavigate();
  const [models, setModels] = useState([DEFAULT_MODEL]);
  const [selectedModel, setSelectedModel] = useState(() => loadSettings().model);

  useEffect(() => {
    apiGet('/api/models')
      .then(data => {
        if (data.models?.length > 0) {
          setModels(data.models);
          const settings = loadSettings();
          const ids = data.models.map(m => m.model_id);
          if (!ids.includes(settings.model)) {
            const fallback = data.models[0].model_id;
            setSelectedModel(fallback);
            saveSettings({ ...settings, model: fallback });
          }
        }
      })
      .catch(() => {});
  }, []);

  const handleModelChange = (e) => {
    const newModel = e.target.value;
    setSelectedModel(newModel);
    saveSettings({ ...loadSettings(), model: newModel });
  };

  return (
    <header className="status-bar">
      <div className="status-bar__left">
        <span className="status-bar__prompt">▶</span>
        <span>GOV_ASSIST</span>
        <span className="status-bar__version">v1.0</span>
        <span className="status-bar__indicator">● ONLINE</span>
      </div>
      <div className="status-bar__right">
        <span>[ AI: {models.find(m => m.model_id === selectedModel)?.display_name || selectedModel} ]</span>
        <div className="status-bar__actions">
          <select
            className="select"
            value={selectedModel}
            onChange={handleModelChange}
            style={{ width: 'auto', fontSize: 'var(--font-size-xs)' }}
            aria-label="AI モデル選択"
          >
            {models.map(model => (
              <option key={model.model_id} value={model.model_id}>
                {model.display_name}
              </option>
            ))}
          </select>
          <button
            className="btn btn--sm btn--secondary"
            onClick={() => navigate('/settings')}
            aria-label="設定を開く"
            type="button"
          >
            ⚙
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
