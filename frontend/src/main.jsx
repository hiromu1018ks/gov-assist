// src/main.jsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import App from './App';
import './css/base.css';
import './css/layout.css';
import './css/components.css';
import './css/animations.css';
import ScanlineOverlay from './effects/ScanlineOverlay';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ScanlineOverlay />
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
