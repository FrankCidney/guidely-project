import React, { useState } from 'react';
import { authService } from '../api/client';
import { BookOpen, Lock, Mail, AlertCircle, ArrowRight, CheckCircle } from 'lucide-react';

export default function LoginPage({ onLoginSuccess }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');
    setLoading(true);

    try {
      if (isRegister) {
        await authService.register(email, password);
        setSuccessMsg('Account registered successfully! Please log in.');
        setIsRegister(false);
        setPassword('');
      } else {
        const data = await authService.login(email, password);
        onLoginSuccess({
          email,
          role: data.role,
        });
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Authentication failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const fillDemoAdmin = () => {
    setEmail('admin@guidely.com');
    setPassword('admin123Password!');
    setError('');
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">
            <BookOpen size={28} color="#2563eb" />
          </div>
          <h1 className="login-title">Guidely</h1>
          <p className="login-subtitle">Internal Knowledge Q&A Assistant</p>
        </div>

        <div className="login-tabs">
          <button
            type="button"
            className={`tab-btn ${!isRegister ? 'active' : ''}`}
            onClick={() => { setIsRegister(false); setError(''); setSuccessMsg(''); }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`tab-btn ${isRegister ? 'active' : ''}`}
            onClick={() => { setIsRegister(true); setError(''); setSuccessMsg(''); }}
          >
            Register
          </button>
        </div>

        {error && (
          <div className="alert-box error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="alert-box success">
            <CheckCircle size={16} />
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label className="form-label" htmlFor="email">Work Email</label>
            <div className="input-icon-wrapper">
              <Mail size={16} className="input-icon" />
              <input
                id="email"
                type="email"
                className="form-input"
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Password</label>
            <div className="input-icon-wrapper">
              <Lock size={16} className="input-icon" />
              <input
                id="password"
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            <span>{loading ? 'Please wait...' : isRegister ? 'Create Account' : 'Sign In'}</span>
            {!loading && <ArrowRight size={16} />}
          </button>
        </form>

        {!isRegister && (
          <div className="demo-credentials-box">
            <div className="demo-header">
              <span>Quick Login:</span>
              <button type="button" className="btn-demo-fill" onClick={fillDemoAdmin}>
                Fill Admin Credentials
              </button>
            </div>
            <div className="demo-details">
              <code>admin@guidely.com</code> / <code>admin123Password!</code>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
