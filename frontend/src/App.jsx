// src/App.jsx
import { Routes, Route, Navigate } from 'react-router-dom';
// import { useAuth } from './context/AuthContext';  // Auth disabled for localhost MVP
import Header from './components/Header';
import SideMenu from './components/SideMenu';
// import ProtectedRoute from './components/ProtectedRoute';  // Auth disabled for localhost MVP
import WarningModal from './components/WarningModal';
// import LoginForm from './components/LoginForm';  // Auth disabled for localhost MVP
import Proofreading from './tools/proofreading/Proofreading';
import History from './tools/history/History';
import Settings from './tools/settings/Settings';

function App() {
  // --- Auth disabled for localhost MVP ---
  // To re-enable: uncomment useAuth, ProtectedRoute, LoginForm imports and
  // restore the conditional rendering and /login route below.
  // const { isAuthenticated } = useAuth();

  return (
    <div className="app">
      <WarningModal />
      <Header />
      <div className="app-content">
        <SideMenu />
        <main className="main-content">
          <Routes>
            {/* <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <LoginForm />} /> */}
            <Route path="/" element={<Proofreading />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/history" element={<History />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;
