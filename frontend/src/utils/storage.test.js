import { describe, it, expect, beforeEach } from 'vitest';
import { loadSettings, saveSettings } from './storage';

beforeEach(() => {
  localStorage.clear();
});

describe('loadSettings', () => {
  it('returns defaults when nothing is stored', () => {
    const settings = loadSettings();
    expect(settings.version).toBe(1);
    expect(settings.model).toBe('kimi-k2.5');
    expect(settings.document_type).toBe('official');
    expect(settings.options.typo).toBe(true);
    expect(settings.options.legal).toBe(false);
  });

  it('returns stored settings when version matches', () => {
    const stored = {
      version: 1,
      model: 'test-model',
      document_type: 'email',
      options: { typo: false, keigo: true, terminology: true, style: true, legal: true, readability: false },
    };
    localStorage.setItem('govassist_settings', JSON.stringify(stored));
    const settings = loadSettings();
    expect(settings.model).toBe('test-model');
    expect(settings.document_type).toBe('email');
    expect(settings.options.typo).toBe(false);
    expect(settings.options.legal).toBe(true);
  });

  it('returns defaults when localStorage has corrupted data', () => {
    localStorage.setItem('govassist_settings', 'not-json{{{');
    const settings = loadSettings();
    expect(settings.model).toBe('kimi-k2.5');
    expect(settings.version).toBe(1);
  });

  it('migrates settings from older version (keeps known fields)', () => {
    const old = { version: 0, model: 'old-model', document_type: 'report' };
    localStorage.setItem('govassist_settings', JSON.stringify(old));
    const settings = loadSettings();
    expect(settings.version).toBe(1);
    expect(settings.model).toBe('old-model');
    expect(settings.document_type).toBe('report');
    // New fields get defaults
    expect(settings.options).toBeDefined();
    expect(settings.options.typo).toBe(true);
  });

  it('handles missing options field gracefully', () => {
    const partial = { version: 1, model: 'test' };
    localStorage.setItem('govassist_settings', JSON.stringify(partial));
    const settings = loadSettings();
    expect(settings.model).toBe('test');
    expect(settings.options.typo).toBe(true);
  });
});

describe('saveSettings', () => {
  it('saves settings with version to localStorage', () => {
    saveSettings({ model: 'new-model', document_type: 'email', options: {} });
    const raw = localStorage.getItem('govassist_settings');
    const parsed = JSON.parse(raw);
    expect(parsed.version).toBe(1);
    expect(parsed.model).toBe('new-model');
  });

  it('overwrites existing settings', () => {
    saveSettings({ model: 'first', document_type: 'official', options: {} });
    saveSettings({ model: 'second', document_type: 'email', options: {} });
    const settings = loadSettings();
    expect(settings.model).toBe('second');
  });
});
