// src/App.jsx
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Header from './components/Header';
import SideMenu from './components/SideMenu';
import ProtectedRoute from './components/ProtectedRoute';
import WarningModal from './components/WarningModal';
import LoginForm from './components/LoginForm';
import Proofreading from './tools/proofreading/Proofreading';
import Settings from './tools/settings/Settings';

function App() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="app">
      <WarningModal />
      {isAuthenticated && <Header />}
      <div className="app-content">
        {isAuthenticated && <SideMenu />}
        <main className="main-content">
          <Routes>
            <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <LoginForm />} />
            <Route path="/" element={<ProtectedRoute><Proofreading /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;
