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
