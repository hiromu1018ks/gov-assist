export default function FullTextView({ text, label }) {
  return (
    <div className="full-text-view" role="region" aria-label={label} style={{ whiteSpace: 'pre-wrap' }}>
      {text}
    </div>
  );
}
