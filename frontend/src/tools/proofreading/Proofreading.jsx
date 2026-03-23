import { useState, useCallback } from 'react';
import { loadSettings } from '../../utils/storage';
import { apiPost, apiPostBlob } from '../../api/client';
import { preprocessText } from './preprocess';
import InputArea from './InputArea';
import OptionPanel from './OptionPanel';
import ResultView from './ResultView';

function Proofreading() {
  const [options, setOptions] = useState(() => loadSettings().options);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [lastParams, setLastParams] = useState(null);
  const [clearKey, setClearKey] = useState(0);
  const [copySuccess, setCopySuccess] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const callProofreadApi = useCallback(async (text, documentType, model) => {
    setIsSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiPost('/api/proofread', {
        request_id: crypto.randomUUID(),
        text,
        document_type: documentType,
        options: options || {},
        model,
      });
      setResult(response);
    } catch (err) {
      setError(err.message || '校正に失敗しました。');
    } finally {
      setIsSubmitting(false);
    }
  }, [options]);

  const handleSubmit = useCallback(async (rawText, documentType) => {
    const { text: preprocessed, error: preprocessError } = preprocessText(rawText);
    if (preprocessError) {
      setError(preprocessError);
      return;
    }

    const settings = loadSettings();
    setLastParams({ rawText, text: preprocessed, documentType, model: settings.model });
    await callProofreadApi(preprocessed, documentType, settings.model);
  }, [callProofreadApi]);

  const handleRetry = useCallback(async () => {
    if (!lastParams || isSubmitting) return;
    await callProofreadApi(lastParams.text, lastParams.documentType, lastParams.model);
  }, [lastParams, isSubmitting, callProofreadApi]);

  const handleClear = useCallback(() => {
    setResult(null);
    setError(null);
    setLastParams(null);
    setCopySuccess(false);
    setSaveSuccess(false);
    setClearKey((k) => k + 1);
  }, []);

  const handleCopy = useCallback(async () => {
    if (!result?.corrected_text) return;
    try {
      await navigator.clipboard.writeText(result.corrected_text);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch {
      setError('クリップボードへのコピーに失敗しました。');
    }
  }, [result]);

  const handleDownload = useCallback(async () => {
    if (!result?.corrected_text) return;
    try {
      const blob = await apiPostBlob('/api/export/docx', {
        corrected_text: result.corrected_text,
        document_type: lastParams?.documentType || 'official',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = '校正済み文書.docx';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setError('Word ファイルのダウンロードに失敗しました。');
    }
  }, [result, lastParams]);

  const handleSaveHistory = useCallback(async () => {
    if (!result || !lastParams) return;
    try {
      await apiPost('/api/history', {
        input_text: lastParams.rawText,
        result,
        model: lastParams.model,
        document_type: lastParams.documentType,
      });
      setSaveSuccess(true);
    } catch {
      setError('履歴への保存に失敗しました。');
    }
  }, [result, lastParams]);

  const hasContent = result || error;
  const showActions = result && result.status !== 'error' && result.corrected_text;

  return (
    <div>
      <h2>AI 文書校正</h2>
      <div className="mt-md">
        <InputArea key={clearKey} onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      </div>
      <div className="mt-md">
        <OptionPanel onChange={setOptions} disabled={isSubmitting} />
      </div>
      {isSubmitting && (
        <div className="loading mt-lg">
          <div className="spinner" role="status" aria-label="校正中"></div>
          <span>AI が校正しています...</span>
        </div>
      )}
      {error && !isSubmitting && (
        <div className="message message--error mt-md" role="alert">
          {error}
        </div>
      )}
      {!result && error && !isSubmitting && lastParams && (
        <button className="btn btn--secondary mt-sm" onClick={handleRetry} type="button">
          再試行
        </button>
      )}
      <ResultView result={result} originalText={lastParams?.rawText ?? ''} onRetry={handleRetry} />
      {hasContent && (
        <div className="action-bar mt-md">
          {showActions && (
            <>
              <button className="btn btn--secondary" onClick={handleCopy} type="button">
                {copySuccess ? 'コピーしました' : '校正済みテキストをコピー'}
              </button>
              <button className="btn btn--secondary" onClick={handleDownload} type="button">
                Word でダウンロード (.docx)
              </button>
              <button className="btn btn--secondary" onClick={handleSaveHistory} type="button" disabled={saveSuccess}>
                {saveSuccess ? '保存しました' : '履歴に保存'}
              </button>
            </>
          )}
          <button className="btn btn--secondary" onClick={handleClear} type="button">
            クリア
          </button>
        </div>
      )}
    </div>
  );
}

export default Proofreading;
