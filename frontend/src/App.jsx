import { Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Header';
import SideMenu from './components/SideMenu';
import Proofreading from './tools/proofreading/Proofreading';
import Settings from './tools/settings/Settings';

function App() {
  return (
    <div className="app">
      <Header />
      <div className="app-content">
        <SideMenu />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Proofreading />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;
