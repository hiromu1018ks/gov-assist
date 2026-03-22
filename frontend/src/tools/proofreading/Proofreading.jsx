import { useState, useCallback } from 'react';
import { loadSettings } from '../../utils/storage';
import { apiPost } from '../../api/client';
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
    setClearKey((k) => k + 1);
  }, []);

  const hasContent = result || error;

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
      <ResultView result={result} onRetry={handleRetry} />
      {hasContent && (
        <div className="action-bar mt-md">
          <button className="btn btn--secondary" onClick={handleClear} type="button">
            クリア
          </button>
        </div>
      )}
    </div>
  );
}

export default Proofreading;
