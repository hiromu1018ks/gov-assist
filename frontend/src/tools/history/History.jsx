import { useState } from 'react';
import HistoryList from './HistoryList';
import HistoryDetail from './HistoryDetail';

export default function History() {
  const [selectedId, setSelectedId] = useState(null);

  if (selectedId !== null) {
    return (
      <HistoryDetail
        key={selectedId}
        historyId={selectedId}
        onBack={() => setSelectedId(null)}
      />
    );
  }

  return <HistoryList onSelectItem={(id) => setSelectedId(id)} />;
}
