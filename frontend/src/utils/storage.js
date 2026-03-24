const STORAGE_KEY = 'govassist_settings';
const CURRENT_VERSION = 1;

const DEFAULTS = {
  version: CURRENT_VERSION,
  model: 'gpt-oss-120b',
  document_type: 'official',
  options: {
    typo: true,
    keigo: true,
    terminology: true,
    style: true,
    legal: false,
    readability: true,
  },
};

export function loadSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULTS };

    const stored = JSON.parse(raw);

    return {
      ...DEFAULTS,
      ...stored,
      version: CURRENT_VERSION,
      options: {
        ...DEFAULTS.options,
        ...(stored.options || {}),
      },
    };
  } catch {
    return { ...DEFAULTS };
  }
}

export function saveSettings(settings) {
  const toSave = { ...settings, version: CURRENT_VERSION };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
}
