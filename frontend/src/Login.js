// Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
// SAM (Smart Analyst for Markets) — Proprietary Software

import React, { useState } from 'react';

const BACKEND = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch(`${BACKEND}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || 'Invalid credentials');
        setLoading(false);
        return;
      }

      const data = await res.json();
      localStorage.setItem('sam_token', data.token);
      localStorage.setItem('sam_user', data.username);
      onLogin(data.token);
    } catch (err) {
      setError('Connection failed — is the backend running?');
    }
    setLoading(false);
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <div className="login-header">
          <div className="login-logo">SAM</div>
          <div className="login-subtitle">Smart Analyst for Markets</div>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              autoFocus
              required
            />
          </div>

          <div className="login-field">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
            />
          </div>

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="login-footer">
          Smart Touch Infotech Private Limited
        </div>
      </div>
    </div>
  );
}

export default Login;
