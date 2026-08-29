import React from 'react';
import { Search, Database, LogOut, Shield, User, BookOpen } from 'lucide-react';

export default function Navbar({ user, activeTab, setActiveTab, onLogout }) {
  return (
    <header className="navbar">
      <div className="navbar-container">
        <div className="navbar-brand">
          <div className="brand-icon">
            <BookOpen size={20} color="#2563eb" />
          </div>
          <div className="brand-text">
            <span className="brand-name">Guidely</span>
            <span className="brand-tag">Knowledge Base</span>
          </div>
        </div>

        {user && (
          <nav className="navbar-nav">
            <button
              className={`nav-link ${activeTab === 'search' ? 'active' : ''}`}
              onClick={() => setActiveTab('search')}
            >
              <Search size={16} />
              <span>Search & Q&A</span>
            </button>

            {user.role === 'admin' && (
              <button
                className={`nav-link ${activeTab === 'admin' ? 'active' : ''}`}
                onClick={() => setActiveTab('admin')}
              >
                <Database size={16} />
                <span>Admin Console</span>
              </button>
            )}
          </nav>
        )}

        <div className="navbar-actions">
          {user ? (
            <div className="user-profile">
              <div className="user-info">
                <span className="user-email">{user.email}</span>
                <span className={`role-badge ${user.role}`}>
                  {user.role === 'admin' ? <Shield size={12} /> : <User size={12} />}
                  {user.role}
                </span>
              </div>
              <button className="btn-logout" onClick={onLogout} title="Sign Out">
                <LogOut size={16} />
                <span>Sign Out</span>
              </button>
            </div>
          ) : (
            <div className="guest-badge">
              <User size={14} />
              <span>Guest</span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
