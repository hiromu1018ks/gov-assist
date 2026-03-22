// src/tools/proofreading/Proofreading.jsx
import { useState } from 'react';
import InputArea from './InputArea';
import OptionPanel from './OptionPanel';
import ResultView from './ResultView';

function Proofreading() {
  const [options, setOptions] = useState(null);
  const [isSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = (text, documentType) => {
    // Task 19 will implement the full proofreading flow:
    // preprocessing -> API call -> result display
    console.log('Proofread requested:', { textLength: text.length, documentType, options });
  };

  return (
    <div>
      <h2>AI 文書校正</h2>
      <div className="mt-md">
        <InputArea onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      </div>
      <div className="mt-md">
        <OptionPanel onChange={setOptions} disabled={isSubmitting} />
      </div>
      <ResultView result={result} />
    </div>
  );
}

export default Proofreading;
