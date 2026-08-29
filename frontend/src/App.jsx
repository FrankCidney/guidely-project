import React, { useState, useEffect } from 'react';
import { authService } from './api/client';
import Navbar from './components/Navbar';
import LoginPage from './pages/LoginPage';
import SearchPage from './pages/SearchPage';
import AdminPage from './pages/AdminPage';
import './App.css';

export default function App() {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('search');
  const [initializing, setInitializing] = useState(true);

  // Check stored auth session on initial load
  useEffect(() => {
    async function checkAuth() {
      const storedUser = authService.getCurrentUser();
      const token = authService.getToken();

      if (token && storedUser) {
        try {
          const profile = await authService.getProfile();
          setUser(profile);
        } catch {
          authService.logout();
          setUser(null);
        }
      }
      setInitializing(false);
    }
    checkAuth();
  }, []);

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    setActiveTab(userData.role === 'admin' ? 'admin' : 'search');
  };

  const handleLogout = () => {
    authService.logout();
    setUser(null);
    setActiveTab('search');
  };

  if (initializing) {
    return (
      <div className="app-loading-screen">
        <div className="loading-spinner-ring" />
        <p>Loading Guidely Knowledge Assistant...</p>
      </div>
    );
  }

  if (!user) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="app-root">
      <Navbar
        user={user}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onLogout={handleLogout}
      />

      <main className="main-content-area">
        {activeTab === 'search' && <SearchPage />}
        {activeTab === 'admin' && user.role === 'admin' && <AdminPage />}
      </main>

      <footer className="app-footer">
        <div className="footer-container">
          <span>Guidely RAG Knowledge Assistant</span>
          <span className="footer-dot">•</span>
          <span>Google Gemini & FAISS</span>
        </div>
      </footer>
    </div>
  );
}
