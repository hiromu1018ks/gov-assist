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
    try {
      const result = await extractText(file);
      if (result.error) {
        setExtractionError(result.error);
        return;
      }
      setPreviousText(textRef.current);
      setExtractionSource(file.name);
      setText(result.text);
      setExtractionError(null);
    } catch {
      setExtractionError('ファイルの読み込みに失敗しました。テキストを直接入力してください。');
    } finally {
      setIsExtracting(false);
    }
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
