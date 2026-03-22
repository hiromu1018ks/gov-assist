# Task 15: Input Area — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the InputArea component with text input, file upload (.docx/.pdf), drag-and-drop, extraction preview, document type selector, character counter (8,000 limit), and security warning — the user-facing input half of the proofreading tool.

**Architecture:** A self-contained InputArea component manages text and document type state internally. File extraction is handled by a separate `fileExtractor.js` utility that wraps mammoth.js (.docx) and pdfjs-dist (.pdf). InputArea exposes an `onSubmit(text, documentType)` callback for the parent to initiate proofreading (wired in Task 19). All rendering uses standard React JSX — no `dangerouslySetInnerHTML`. Existing CSS classes from `components.css` are reused; only a few InputArea-specific styles are added.

**Tech Stack:** React 18, mammoth.js, pdfjs-dist, Vitest, React Testing Library, plain CSS (no Tailwind)

**Design Spec References:** §3.3.1 (Input Area), §3.3.2 (Character limit), §6.1 (File Input), §8.4 (Security Warning)

---

## File Structure

### New files (4)

| File | Responsibility |
|------|---------------|
| `src/tools/proofreading/fileExtractor.js` | Extract text from .docx (mammoth) and .pdf (pdfjs-dist); handle errors and edge cases |
| `src/tools/proofreading/fileExtractor.test.js` | Tests for file extraction — mock mammoth and pdfjs-dist |
| `src/tools/proofreading/InputArea.jsx` | Text input, file upload, drag-and-drop, doc type selector, char counter, security warning |
| `src/tools/proofreading/InputArea.test.jsx` | Tests for InputArea component — mock fileExtractor |

### Modified files (3)

| File | Changes |
|------|---------|
| `src/tools/proofreading/Proofreading.jsx` | Replace placeholder with InputArea component |
| `src/App.test.jsx` | Update proofreading placeholder assertions for new content |
| `src/css/components.css` | Add InputArea-specific styles (char counter, input area layout) |

### Key Constraints

- **No `dangerouslySetInnerHTML`** — all rendering via React JSX (§8.2)
- **No Tailwind** — plain CSS only (CLAUDE.md)
- **Client-side file extraction** — mammoth.js for .docx, pdfjs-dist for .pdf (§6.1)
- **Image-only PDF returns error** — no OCR (§6.1)
- **Extraction preview** — user reviews extracted text before sending (§3.3.1)
- **Character limit 8,000** — disable submit on overflow, show counter (§3.3.1)
- **Security warning always visible** above input (§8.4)
- **Minimum 10 lines** for textarea (§3.3.1)
- **localStorage** for default document type via `loadSettings()` (§3.4)
- **File extraction is async** — show spinner during extraction (§3.3.5)

---

## Task 1: Install Dependencies

**Files:**
- Modify: `frontend/package.json` (mammoth, pdfjs-dist added)

- [ ] **Step 1: Install mammoth and pdfjs-dist**

```bash
cd /home/hart/Code/gov-assist/frontend
npm install mammoth pdfjs-dist
```

Expected: `package.json` now includes `mammoth` and `pdfjs-dist` in dependencies.

- [ ] **Step 2: Verify installation**

```bash
cd /home/hart/Code/gov-assist/frontend
node -e "require('mammoth'); console.log('mammoth OK')"
node -e "require('pdfjs-dist'); console.log('pdfjs-dist OK')"
```

Expected: Both print "OK" without errors.

- [ ] **Step 3: Commit**

```bash
cd /home/hart/Code/gov-assist
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(frontend): add mammoth and pdfjs-dist for file text extraction"
```

---

## Task 2: File Extractor Utility

**Files:**
- Create: `src/tools/proofreading/fileExtractor.js`
- Create: `src/tools/proofreading/fileExtractor.test.js`

- [ ] **Step 1: Write the failing tests**

```js
// src/tools/proofreading/fileExtractor.test.js
import { describe, it, expect, vi, beforeEach } from 'vitest';

const { mockExtractRawText, mockGetDocument } = vi.hoisted(() => ({
  mockExtractRawText: vi.fn(),
  mockGetDocument: vi.fn(),
}));

vi.mock('mammoth', () => ({ default: { extractRawText: mockExtractRawText } }));
vi.mock('pdfjs-dist', () => ({
  getDocument: mockGetDocument,
  GlobalWorkerOptions: { workerSrc: '' },
}));

import { extractText } from './fileExtractor';

describe('fileExtractor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function makeFile(name, content = '') {
    return new File([content], name, { type: 'application/octet-stream' });
  }

  it('extracts text from .docx file using mammoth', async () => {
    mockExtractRawText.mockResolvedValue({ value: '  extracted docx text  ', messages: [] });

    const result = await extractText(makeFile('test.docx', 'binary'));

    expect(mockExtractRawText).toHaveBeenCalledOnce();
    expect(result.text).toBe('extracted docx text');
    expect(result.error).toBeNull();
  });

  it('extracts text from .pdf file using pdfjs-dist', async () => {
    const mockGetTextContent = vi.fn().mockResolvedValue({
      items: [{ str: 'Hello ' }, { str: 'world' }],
    });
    const mockGetPage = vi.fn().mockResolvedValue({ getTextContent: mockGetTextContent });
    mockGetDocument.mockReturnValue({
      promise: Promise.resolve({ numPages: 1, getPage: mockGetPage }),
    });

    const result = await extractText(makeFile('test.pdf', 'binary'));

    expect(mockGetDocument).toHaveBeenCalledOnce();
    expect(result.text).toBe('Hello world');
    expect(result.error).toBeNull();
  });

  it('returns error for unsupported file type', async () => {
    const result = await extractText(makeFile('test.xlsx'));

    expect(result.text).toBe('');
    expect(result.error).toContain('対応していない');
  });

  it('returns error when PDF has no extractable text (image-only)', async () => {
    mockGetDocument.mockReturnValue({
      promise: Promise.resolve({
        numPages: 1,
        getPage: vi.fn().mockResolvedValue({
          getTextContent: vi.fn().mockResolvedValue({ items: [] }),
        }),
      }),
    });

    const result = await extractText(makeFile('scan.pdf'));

    expect(result.text).toBe('');
    expect(result.error).toContain('テキストを抽出できませんでした');
  });

  it('extracts text from multi-page PDF by concatenating all pages', async () => {
    const mockGetTextContent1 = vi.fn().mockResolvedValue({
      items: [{ str: 'Page 1 text' }],
    });
    const mockGetTextContent2 = vi.fn().mockResolvedValue({
      items: [{ str: 'Page 2 text' }],
    });
    const mockGetPage = vi.fn()
      .mockResolvedValueOnce({ getTextContent: mockGetTextContent1 })
      .mockResolvedValueOnce({ getTextContent: mockGetTextContent2 });
    mockGetDocument.mockReturnValue({
      promise: Promise.resolve({ numPages: 2, getPage: mockGetPage }),
    });

    const result = await extractText(makeFile('multi.pdf', 'binary'));

    expect(result.text).toBe('Page 1 text\nPage 2 text');
    expect(mockGetPage).toHaveBeenCalledTimes(2);
  });

  it('returns error when mammoth throws', async () => {
    mockExtractRawText.mockRejectedValue(new Error('Invalid docx'));

    const result = await extractText(makeFile('broken.docx'));

    expect(result.text).toBe('');
    expect(result.error).toContain('読み込みに失敗しました');
  });

  it('returns error when pdfjs-dist throws', async () => {
    mockGetDocument.mockReturnValue({
      promise: Promise.reject(new Error('Invalid PDF')),
    });

    const result = await extractText(makeFile('broken.pdf'));

    expect(result.text).toBe('');
    expect(result.error).toContain('読み込みに失敗しました');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/hart/Code/gov-assist/frontend && npx vitest run src/tools/proofreading/fileExtractor.test.js`
Expected: FAIL — `Cannot find module './fileExtractor'`

- [ ] **Step 3: Write the implementation**

```js
// src/tools/proofreading/fileExtractor.js
import mammoth from 'mammoth';
import * as pdfjsLib from 'pdfjs-dist';

// Set up pdf.js worker for Vite bundling
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

/**
 * Extract text from a .docx or .pdf file.
 * @param {File} file - The file to extract text from
 * @returns {Promise<{text: string, error: string|null}>}
 */
export async function extractText(file) {
  const ext = file.name.split('.').pop().toLowerCase();

  if (ext !== 'docx' && ext !== 'pdf') {
    return { text: '', error: '対応していないファイル形式です（.docx, .pdf のみ対応）。' };
  }

  try {
    if (ext === 'docx') {
      return await extractDocx(file);
    }
    return await extractPdf(file);
  } catch {
    return { text: '', error: 'ファイルの読み込みに失敗しました。テキストを直接入力してください。' };
  }
}

async function extractDocx(file) {
  const arrayBuffer = await file.arrayBuffer();
  const result = await mammoth.extractRawText({ arrayBuffer });
  const text = result.value.trim();

  if (!text) {
    return { text: '', error: 'テキストを抽出できませんでした。テキスト形式のファイルか、テキストを直接入力してください。' };
  }

  return { text, error: null };
}

async function extractPdf(file) {
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

  let fullText = '';
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    const pageText = content.items.map((item) => item.str).join('');
    fullText += pageText + '\n';
  }

  fullText = fullText.trim();

  if (!fullText) {
    return { text: '', error: 'テキストを抽出できませんでした。テキスト形式の PDF か、テキストを直接入力してください。' };
  }

  return { text: fullText, error: null };
}
```

> **Note on pdf.js worker setup:** The `new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url)` pattern tells Vite to bundle the worker as a separate chunk. If this causes build errors with the installed pdfjs-dist version, fall back to a CDN URL: `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/hart/Code/gov-assist/frontend && npx vitest run src/tools/proofreading/fileExtractor.test.js`
Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /home/hart/Code/gov-assist
git add frontend/src/tools/proofreading/fileExtractor.js frontend/src/tools/proofreading/fileExtractor.test.js
git commit -m "feat(frontend): add fileExtractor utility for .docx and .pdf text extraction"
```

---

## Task 3: InputArea Component — Core

This task implements the InputArea component with text input, document type selector, character counter, security warning, and submit button. File upload and drag-and-drop are added in Task 4.

**Files:**
- Create: `src/tools/proofreading/InputArea.jsx`
- Create: `src/tools/proofreading/InputArea.test.jsx`

- [ ] **Step 1: Write the failing tests (core features)**

```jsx
// src/tools/proofreading/InputArea.test.jsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('./fileExtractor', () => ({
  extractText: vi.fn(),
}));

vi.mock('../../utils/storage', () => ({
  loadSettings: vi.fn(() => ({
    version: 1,
    model: 'kimi-k2.5',
    document_type: 'official',
    options: {},
  })),
  saveSettings: vi.fn(),
}));

import InputArea from './InputArea';

describe('InputArea', () => {
  const onSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  function renderInputArea(props = {}) {
    return render(<InputArea onSubmit={onSubmit} isSubmitting={false} {...props} />);
  }

  // --- Core tests ---

  it('renders security warning message', () => {
    renderInputArea();
    expect(screen.getByText(/外部 AI サービス/)).toBeInTheDocument();
    expect(screen.getByText(/個人情報・機密情報/)).toBeInTheDocument();
  });

  it('renders document type selector with all 4 options', () => {
    renderInputArea();
    const selector = screen.getByLabelText('文書種別');
    expect(selector).toBeInTheDocument();

    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(4);
    expect(options.map((o) => o.value)).toEqual(['email', 'report', 'official', 'other']);
  });

  it('defaults document type to saved setting', async () => {
    const { loadSettings } = await import('../../utils/storage');
    vi.mocked(loadSettings).mockReturnValue({
      version: 1, model: 'kimi-k2.5', document_type: 'report', options: {},
    });
    renderInputArea();

    expect(screen.getByLabelText('文書種別')).toHaveValue('report');
  });

  it('renders textarea with accessible label', () => {
    renderInputArea();
    expect(screen.getByLabelText('校正テキスト入力')).toBeInTheDocument();
  });

  it('shows character counter with correct count', () => {
    renderInputArea();
    expect(screen.getByText('0 / 8,000 文字')).toBeInTheDocument();
  });

  it('updates character counter when text is typed', async () => {
    const user = userEvent.setup();
    renderInputArea();

    await user.type(screen.getByLabelText('校正テキスト入力'), 'テスト');

    expect(screen.getByText('3 / 8,000 文字')).toBeInTheDocument();
  });

  it('shows error style when character count exceeds 8,000', async () => {
    const user = userEvent.setup();
    renderInputArea();

    const textarea = screen.getByLabelText('校正テキスト入力');
    await userEvent.clear(textarea);
    await user.type(textarea, 'x'.repeat(8001));

    const counter = screen.getByText('8,001 / 8,000 文字');
    expect(counter.className).toContain('char-counter--over');
  });

  it('disables submit button when text is empty', () => {
    renderInputArea();
    expect(screen.getByRole('button', { name: '校正実行' })).toBeDisabled();
  });

  it('disables submit button when text exceeds 8,000 characters', async () => {
    const user = userEvent.setup();
    renderInputArea();

    await user.type(screen.getByLabelText('校正テキスト入力'), 'x'.repeat(8001));

    expect(screen.getByRole('button', { name: '校正実行' })).toBeDisabled();
  });

  it('enables submit button with valid text', async () => {
    const user = userEvent.setup();
    renderInputArea();

    await user.type(screen.getByLabelText('校正テキスト入力'), '校正してください。');

    expect(screen.getByRole('button', { name: '校正実行' })).not.toBeDisabled();
  });

  it('calls onSubmit with text and documentType on submit', async () => {
    const user = userEvent.setup();
    renderInputArea();

    await user.type(screen.getByLabelText('校正テキスト入力'), 'テスト文書');
    await user.click(screen.getByRole('button', { name: '校正実行' }));

    expect(onSubmit).toHaveBeenCalledWith('テスト文書', 'official');
  });

  it('disables textarea when isSubmitting is true', () => {
    renderInputArea({ isSubmitting: true });
    expect(screen.getByLabelText('校正テキスト入力')).toBeDisabled();
  });

  it('disables submit button when isSubmitting is true', () => {
    renderInputArea({ isSubmitting: true });
    expect(screen.getByRole('button', { name: '校正実行' })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/hart/Code/gov-assist/frontend && npx vitest run src/tools/proofreading/InputArea.test.js`
Expected: FAIL — `Cannot find module './InputArea'`

- [ ] **Step 3: Write the implementation**

```jsx
// src/tools/proofreading/InputArea.jsx
import { useState, useRef, useCallback } from 'react';
import { loadSettings } from '../../utils/storage';
import { extractText } from './fileExtractor';

const MAX_CHARS = 8000;

const DOCUMENT_TYPES = [
  { value: 'email', label: 'メール' },
  { value: 'report', label: '報告書' },
  { value: 'official', label: '公文書' },
  { value: 'other', label: 'その他' },
];

export default function InputArea({ onSubmit, isSubmitting }) {
  const [text, setText] = useState('');
  const [documentType, setDocumentType] = useState(() => loadSettings().document_type);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractionSource, setExtractionSource] = useState(null);
  const [previousText, setPreviousText] = useState(null);
  const [extractionError, setExtractionError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);
  const dragCounterRef = useRef(0);
  // Ref to avoid stale closure in async handleFile — always reads current text
  const textRef = useRef(text);
  textRef.current = text;

  const charCount = text.length;
  const isOverLimit = charCount > MAX_CHARS;
  const canSubmit = charCount > 0 && !isOverLimit && !isSubmitting;

  const handleFile = useCallback(async (file) => {
    setIsExtracting(true);
    setExtractionError(null);

    const result = await extractText(file);

    setIsExtracting(false);

    if (result.error) {
      setExtractionError(result.error);
      return;
    }

    setPreviousText(textRef.current);
    setExtractionSource(file.name);
    setText(result.text);
    setExtractionError(null);
  }, []);

  const handleTextChange = (e) => {
    const newText = e.target.value;
    setText(newText);
    setExtractionError(null);
    // Clear extraction banner when user manually edits
    if (extractionSource) {
      setExtractionSource(null);
      setPreviousText(null);
    }
  };

  const handleSubmit = () => {
    if (!canSubmit) return;
    onSubmit(text, documentType);
  };

  const handleFileButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileInputChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFile(file);
    }
    // Reset input so the same file can be re-selected
    e.target.value = '';
  };

  const handleUndoExtraction = () => {
    setText(previousText);
    setExtractionSource(null);
    setPreviousText(null);
    setExtractionError(null);
  };

  // Drag-and-drop handlers
  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.types.includes('Files')) {
      dragCounterRef.current++;
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) {
      setIsDragging(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current = 0;
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  };

  return (
    <div className="input-area">
      {/* Security Warning (§8.4) */}
      <div className="message message--warning">
        <span className="input-area__warning-icon">⚠</span>{' '}
        本ツールはテキストを外部 AI サービス（さくらの AI Engine）に送信します。
        個人情報・機密情報を含む文書の入力はお控えください。
      </div>

      {/* Header: Document Type + File Upload */}
      <div className="input-area__header form-row mt-md">
        <div className="form-group" style={{ flex: 1 }}>
          <label className="label" htmlFor="document-type">文書種別</label>
          <select
            id="document-type"
            className="select"
            value={documentType}
            onChange={(e) => setDocumentType(e.target.value)}
            disabled={isSubmitting}
          >
            {DOCUMENT_TYPES.map((dt) => (
              <option key={dt.value} value={dt.value}>{dt.label}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label className="label">&nbsp;</label>
          <input
            type="file"
            accept=".docx,.pdf"
            ref={fileInputRef}
            className="sr-only"
            tabIndex={-1}
            onChange={handleFileInputChange}
          />
          <button
            className="btn btn--secondary"
            onClick={handleFileButtonClick}
            type="button"
            disabled={isSubmitting || isExtracting}
          >
            ファイルを選択
          </button>
        </div>
      </div>

      {/* Extraction Source Banner */}
      {extractionSource && (
        <div className="input-area__banner message message--info mt-sm">
          「{extractionSource}」からテキストを抽出しました。内容を確認してください。
          <button
            className="btn btn--sm btn--secondary mt-sm"
            onClick={handleUndoExtraction}
            type="button"
          >
            元に戻す
          </button>
        </div>
      )}

      {/* Extraction Error */}
      {extractionError && (
        <div className="message message--error mt-sm" role="alert">
          {extractionError}
        </div>
      )}

      {/* Text Area with Drop Zone */}
      <div
        className={`input-area__textarea-wrapper mt-md ${isDragging ? 'drop-zone--active' : ''}`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {isExtracting ? (
          <div className="loading input-area__extracting">
            <div className="spinner" role="status" aria-label="読み込み中"></div>
            <span>ファイルを読み込んでいます...</span>
          </div>
        ) : (
          <textarea
            className="textarea input-area__textarea"
            value={text}
            onChange={handleTextChange}
            placeholder="校正したいテキストを入力するか、ファイルをドラッグ＆ドロップしてください。"
            aria-label="校正テキスト入力"
            disabled={isSubmitting}
            rows={10}
          />
        )}
      </div>

      {/* Footer: Character Counter + Submit */}
      <div className="input-area__footer flex justify-between items-center mt-sm">
        <span
          className={`char-counter ${isOverLimit ? 'char-counter--over' : ''}`}
          aria-live="polite"
        >
          {charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()} 文字
        </span>
        <button
          className="btn btn--primary"
          onClick={handleSubmit}
          disabled={!canSubmit}
          type="button"
        >
          校正実行
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/hart/Code/gov-assist/frontend && npx vitest run src/tools/proofreading/InputArea.test.js`
Expected: 12 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /home/hart/Code/gov-assist
git add frontend/src/tools/proofreading/InputArea.jsx frontend/src/tools/proofreading/InputArea.test.jsx
git commit -m "feat(frontend): add InputArea component with text input, doc type selector, char counter, and security warning"
```

---

## Task 4: InputArea Component — File Upload and Drag-and-Drop Tests

This task adds the file upload and drag-and-drop test cases to the InputArea test file.

**Files:**
- Modify: `src/tools/proofreading/InputArea.test.jsx`

- [ ] **Step 1: Add file upload and drag-and-drop tests**

Read the current test file first. Then append these tests inside the existing `describe('InputArea', ...)` block, after the last core test:

```jsx
  // --- File Upload and Drag-and-Drop tests ---

  it('clicking file button triggers hidden file input', async () => {
    const user = userEvent.setup();
    renderInputArea();

    const fileButton = screen.getByRole('button', { name: 'ファイルを選択' });
    await user.click(fileButton);

    const fileInput = document.querySelector('input[type="file"]');
    expect(fileInput).toBeInTheDocument();
  });

  it('shows spinner and replaces text after successful file extraction', async () => {
    const { extractText } = await import('./fileExtractor');
    vi.mocked(extractText).mockResolvedValue({ text: 'extracted content from file', error: null });

    const user = userEvent.setup();
    renderInputArea();

    // Set some initial text
    await user.type(screen.getByLabelText('校正テキスト入力'), 'original text');

    // Trigger file input change
    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(['binary'], 'test.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });
    await user.upload(fileInput, file);

    // Should show extracted text
    await screen.findByDisplayValue('extracted content from file');
    expect(screen.getByText(/test.docx/)).toBeInTheDocument();
  });

  it('shows extraction source banner with filename after extraction', async () => {
    const { extractText } = await import('./fileExtractor');
    vi.mocked(extractText).mockResolvedValue({ text: 'content', error: null });

    const user = userEvent.setup();
    renderInputArea();

    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(['binary'], 'report.pdf', { type: 'application/pdf' });
    await user.upload(fileInput, file);

    await screen.findByText(/report.pdf/);
    expect(screen.getByText(/テキストを抽出しました/)).toBeInTheDocument();
  });

  it('restores previous text when cancel button is clicked', async () => {
    const { extractText } = await import('./fileExtractor');
    vi.mocked(extractText).mockResolvedValue({ text: 'new content', error: null });

    const user = userEvent.setup();
    renderInputArea();

    // Set initial text
    await user.type(screen.getByLabelText('校正テキスト入力'), 'original text');

    // Upload file
    const fileInput = document.querySelector('input[type="file"]');
    await user.upload(fileInput, new File(['binary'], 'test.docx'));

    await screen.findByDisplayValue('new content');

    // Click cancel
    await user.click(screen.getByRole('button', { name: '元に戻す' }));

    expect(screen.getByLabelText('校正テキスト入力')).toHaveValue('original text');
    expect(screen.queryByText(/test.docx/)).not.toBeInTheDocument();
  });

  it('shows error message on extraction failure', async () => {
    const { extractText } = await import('./fileExtractor');
    vi.mocked(extractText).mockResolvedValue({
      text: '',
      error: 'テキストを抽出できませんでした。',
    });

    const user = userEvent.setup();
    renderInputArea();

    const fileInput = document.querySelector('input[type="file"]');
    await user.upload(fileInput, new File(['binary'], 'image.pdf'));

    await screen.findByText('テキストを抽出できませんでした。');
  });

  it('clears extraction banner when user types after extraction', async () => {
    const { extractText } = await import('./fileExtractor');
    vi.mocked(extractText).mockResolvedValue({ text: 'extracted', error: null });

    const user = userEvent.setup();
    renderInputArea();

    const fileInput = document.querySelector('input[type="file"]');
    await user.upload(fileInput, new File(['binary'], 'test.docx'));

    await screen.findByText(/test.docx/);

    // User types in textarea — banner should disappear
    await user.type(screen.getByLabelText('校正テキスト入力'), ' edit');

    expect(screen.queryByText(/test.docx/)).not.toBeInTheDocument();
  });

  it('applies drop-zone--active class when dragging files over textarea', () => {
    renderInputArea();
    const wrapper = document.querySelector('.input-area__textarea-wrapper');

    userEvent.fireEvent.dragEnter(wrapper, {
      dataTransfer: { types: ['Files'] },
    });

    expect(wrapper.classList.contains('drop-zone--active')).toBe(true);
  });

  it('handles file drop and extracts text', async () => {
    const { extractText } = await import('./fileExtractor');
    vi.mocked(extractText).mockResolvedValue({ text: 'dropped content', error: null });

    renderInputArea();
    const wrapper = document.querySelector('.input-area__textarea-wrapper');

    const file = new File(['binary'], 'dropped.pdf');
    userEvent.fireEvent.drop(wrapper, {
      dataTransfer: { files: [file], types: ['Files'] },
    });

    expect(extractText).toHaveBeenCalledWith(file);
    await screen.findByDisplayValue('dropped content');
  });
```

- [ ] **Step 2: Run all InputArea tests**

Run: `cd /home/hart/Code/gov-assist/frontend && npx vitest run src/tools/proofreading/InputArea.test.js`
Expected: 20 tests PASS (12 core + 8 file upload/DnD)

- [ ] **Step 3: Commit**

```bash
cd /home/hart/Code/gov-assist
git add frontend/src/tools/proofreading/InputArea.test.jsx
git commit -m "test(frontend): add file upload and drag-and-drop tests for InputArea"
```

---

## Task 5: InputArea CSS

**Files:**
- Modify: `src/css/components.css`

- [ ] **Step 1: Add InputArea styles**

Append at the end of `src/css/components.css`:

```css
/* --- Input Area (§3.3.1) --- */

.input-area {
  max-width: 100%;
}

.input-area__warning-icon {
  margin-right: var(--spacing-xs);
}

.input-area__textarea-wrapper {
  position: relative;
  border-radius: var(--radius);
  transition: border-color var(--transition-fast),
              background-color var(--transition-fast);
}

.input-area__textarea-wrapper.drop-zone--active {
  border: 2px dashed var(--color-primary);
  background-color: rgba(74, 144, 217, 0.05);
}

.input-area__textarea {
  display: block;
  width: 100%;
  min-height: 16rem;
}

.input-area__extracting {
  min-height: 16rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}

/* Character counter */

.char-counter {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.char-counter--over {
  color: var(--color-danger);
  font-weight: 600;
}

/* Extraction source banner */

.input-area__banner {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}
```

- [ ] **Step 2: Verify build succeeds**

```bash
cd /home/hart/Code/gov-assist/frontend
npx vite build
```

Expected: Build completes with exit code 0.

- [ ] **Step 3: Commit**

```bash
cd /home/hart/Code/gov-assist
git add frontend/src/css/components.css
git commit -m "feat(frontend): add InputArea CSS styles for char counter, drop zone, and extraction banner"
```

---

## Task 6: Integration — Wire InputArea into Proofreading

**Files:**
- Modify: `src/tools/proofreading/Proofreading.jsx`
- Modify: `src/App.test.jsx`

- [ ] **Step 1: Update Proofreading.jsx to render InputArea**

Read the current file first. Then replace the entire contents of `src/tools/proofreading/Proofreading.jsx` with:

```jsx
// src/tools/proofreading/Proofreading.jsx
import InputArea from './InputArea';

function Proofreading() {
  const handleSubmit = (text, documentType) => {
    // Task 19 will implement the full proofreading flow:
    // preprocessing → API call → result display
    console.log('Proofread requested:', { textLength: text.length, documentType });
  };

  return (
    <div>
      <h2>AI 文書校正</h2>
      <div className="mt-md">
        <InputArea onSubmit={handleSubmit} isSubmitting={false} />
      </div>
    </div>
  );
}

export default Proofreading;
```

- [ ] **Step 2: Update App.test.jsx — fix proofreading assertions**

Read the current file first. Find this test:

```js
  it('renders proofreading placeholder on default route /', () => {
    renderApp('/');
    const main = screen.getByRole('main');
    expect(within(main).getByText('AI 文書校正')).toBeInTheDocument();
    expect(within(main).getByText(/Task 15/)).toBeInTheDocument();
  });
```

Replace with:

```js
  it('renders proofreading tool on default route /', () => {
    renderApp('/');
    const main = screen.getByRole('main');
    expect(within(main).getByText('AI 文書校正')).toBeInTheDocument();
    expect(within(main).getByText(/外部 AI サービス/)).toBeInTheDocument();
  });
```

Also update the redirect test that checks for Task 15 text:

```js
  it('redirects unknown routes to /', () => {
    renderApp('/unknown-page');
    const main = screen.getByRole('main');
    expect(within(main).getByText(/外部 AI サービス/)).toBeInTheDocument();
  });
```

- [ ] **Step 3: Run all tests**

```bash
cd /home/hart/Code/gov-assist/frontend
npx vitest run
```

Expected: ALL tests PASS (existing + new InputArea + fileExtractor + updated App tests)

- [ ] **Step 4: Commit**

```bash
cd /home/hart/Code/gov-assist
git add frontend/src/tools/proofreading/Proofreading.jsx frontend/src/App.test.jsx
git commit -m "feat(frontend): integrate InputArea into Proofreading page, replace placeholder"
```

---

## Task 7: Build and Visual Verification

- [ ] **Step 1: Full build verification**

```bash
cd /home/hart/Code/gov-assist/frontend
npx vite build
```

Expected: Build completes with exit code 0, no errors.

- [ ] **Step 2: Verify file structure matches design spec**

```bash
cd /home/hart/Code/gov-assist/frontend
find src/tools/proofreading -type f | sort
```

Expected output:
```
src/tools/proofreading/Proofreading.jsx
src/tools/proofreading/InputArea.jsx
src/tools/proofreading/InputArea.test.jsx
src/tools/proofreading/fileExtractor.js
src/tools/proofreading/fileExtractor.test.js
```

- [ ] **Step 3: Visual verification (manual)**

```bash
cd /home/hart/Code/gov-assist/frontend
npm run dev &
```

Open `http://localhost:5173` and verify:
1. Security warning (yellow banner) is visible at top of input area
2. Document type selector shows 4 options — defaults to "公文書"
3. Textarea is at least 10 lines tall with placeholder text
4. Character counter shows "0 / 8,000 文字"
5. "校正実行" button is disabled (no text)
6. Type text — counter updates, button becomes enabled
7. "ファイルを選択" button exists beside document type selector
8. Drag a file over the textarea — blue dashed border highlight appears

After verification:
```bash
kill %1
```

- [ ] **Step 4: Final commit (if any cleanup needed)**

```bash
cd /home/hart/Code/gov-assist
git status
# If any uncommitted changes:
git add -A
git commit -m "chore(frontend): cleanup for Task 15 input area"
```

---

## Summary

| Task | New Files | Modified Files | Tests |
|------|-----------|----------------|-------|
| 1. Install Dependencies | 0 | 2 (package.json, lock) | 0 |
| 2. File Extractor | 2 | 0 | 7 |
| 3. InputArea — Core | 2 | 0 | 12 |
| 4. InputArea — File Upload/DnD Tests | 0 | 1 | +8 |
| 5. InputArea CSS | 0 | 1 | 0 |
| 6. Integration | 0 | 2 | All pass |
| 7. Build and Visual Verification | 0 | 0 | 0 |
| **Total** | **4** | **3** | **27+** |

**New dependencies:** `mammoth`, `pdfjs-dist`

**Key design decisions:**
- InputArea manages its own `text` and `documentType` state — exposes `onSubmit(text, documentType)` callback for parent
- File extraction is a separate utility (`fileExtractor.js`) — easily mocked in tests
- pdf.js worker uses `new URL()` pattern for Vite compatibility
- Drag counter ref prevents flicker on nested drag events
- Extraction banner auto-clears when user manually types (prevents confusing "undo" after edits)
- Character counter uses `aria-live="polite"` for screen reader accessibility

## Next steps

After Task 15 is complete, the following tasks become available:
- **Task 16**: Text Preprocessing and Proofreading Options — `preprocess.js`, `OptionPanel.jsx`
- **Task 17**: Result View Framework — `ResultView.jsx` (3-tab structure)
- **Task 18**: Diff View — `DiffView.jsx` (highlight and comparison tabs)
- **Task 19**: Proofreading Integration — wires InputArea + OptionPanel + ResultView + API call
