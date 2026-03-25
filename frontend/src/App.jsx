import { useState, useCallback, lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Header';
import SideMenu from './components/SideMenu';
import WarningModal from './components/WarningModal';
import BootSequence from './effects/BootSequence';
import MatrixRain from './effects/MatrixRain';
import useStatusMessages from './effects/useStatusMessages';

const Proofreading = lazy(() => import('./tools/proofreading/Proofreading'));
const History = lazy(() => import('./tools/history/History'));
const Settings = lazy(() => import('./tools/settings/Settings'));

function App() {
  const [bootDone, setBootDone] = useState(false);
  const statusMessage = useStatusMessages();
  const handleBootComplete = useCallback(() => setBootDone(true), []);

  return (
    <div className="app">
      <MatrixRain />
      {!bootDone && <BootSequence onComplete={handleBootComplete} />}
      <WarningModal />
      <Header />
      <div className="app-content">
        <SideMenu />
        <main className="main-content">
          <Suspense fallback={null}>
            <Routes>
              <Route path="/" element={<Proofreading />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/history" element={<History />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>
      </div>
      <div className="system-bar">
        <span className="system-bar__status">●</span>
        <span>READY</span>
        <span className="system-bar__message">{statusMessage}</span>
        <span className="system-bar__spacer" />
        <span className="system-bar__info">localhost:8000</span>
      </div>
    </div>
  );
}

export default App;
