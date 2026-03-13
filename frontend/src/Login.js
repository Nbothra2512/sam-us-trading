// Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
// SAM (Smart Analyst for Markets) — Proprietary Software

import React, { useState, useEffect, useRef } from 'react';

const BACKEND = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

// Mini sparkline component
function Sparkline({ data, color, width = 60, height = 20 }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// Generate random sparkline data
function randomSparkline(len = 20) {
  const data = [50];
  for (let i = 1; i < len; i++) {
    data.push(data[i - 1] + (Math.random() - 0.48) * 5);
  }
  return data;
}

const TICKER_DATA = [
  { symbol: 'AAPL', price: 227.48, change: +1.24, color: '#22c55e' },
  { symbol: 'MSFT', price: 445.12, change: -0.87, color: '#ef4444' },
  { symbol: 'NVDA', price: 138.25, change: +3.45, color: '#22c55e' },
  { symbol: 'GOOGL', price: 176.92, change: +0.56, color: '#22c55e' },
  { symbol: 'AMZN', price: 208.34, change: -1.12, color: '#ef4444' },
  { symbol: 'TSLA', price: 248.67, change: +2.89, color: '#22c55e' },
  { symbol: 'META', price: 612.45, change: +1.78, color: '#22c55e' },
  { symbol: 'JPM', price: 243.18, change: -0.34, color: '#ef4444' },
];

function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [sparklines] = useState(() => TICKER_DATA.map(() => randomSparkline()));
  const canvasRef = useRef(null);

  // Animated background particles
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animId;
    let particles = [];

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    // Create particles
    for (let i = 0; i < 50; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        r: Math.random() * 2 + 1,
        opacity: Math.random() * 0.5 + 0.1,
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 150) {
            ctx.strokeStyle = `rgba(59, 130, 246, ${0.1 * (1 - dist / 150)})`;
            ctx.lineWidth = 0.5;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }

      // Draw particles
      particles.forEach(p => {
        ctx.fillStyle = `rgba(59, 130, 246, ${p.opacity})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
      });

      animId = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, []);

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
    <div className="login-page">
      <canvas ref={canvasRef} className="login-canvas" />

      {/* Floating orbs */}
      <div className="login-orb orb-1" />
      <div className="login-orb orb-2" />
      <div className="login-orb orb-3" />

      {/* Market ticker bar */}
      <div className="login-ticker">
        <div className="login-ticker-scroll">
          {[...TICKER_DATA, ...TICKER_DATA].map((t, i) => (
            <div key={i} className="login-ticker-item">
              <Sparkline data={sparklines[i % TICKER_DATA.length]} color={t.color} />
              <span className="login-ticker-symbol">{t.symbol}</span>
              <span className="login-ticker-price">${t.price.toFixed(2)}</span>
              <span style={{ color: t.color, fontSize: 11, fontWeight: 600 }}>
                {t.change >= 0 ? '+' : ''}{t.change.toFixed(2)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Login card */}
      <div className="login-card">
        {/* Header */}
        <div className="login-card-header">
          <div className="login-logo-row">
            <div className="login-logo-icon">
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                <rect width="32" height="32" rx="8" fill="#3b82f6" />
                <path d="M8 22L12 14L16 18L20 10L24 16" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="24" cy="16" r="2" fill="white" />
              </svg>
            </div>
            <div>
              <div className="login-logo-text">SAM</div>
              <div className="login-logo-sub">Smart Analyst for Markets</div>
            </div>
          </div>
          <div className="login-badge">
            <span className="login-badge-dot" />
            Markets Live
          </div>
        </div>

        {/* Welcome text */}
        <div className="login-welcome">
          <h2>Welcome back</h2>
          <p>Sign in to access your trading terminal</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="login-form-new">
          <div className="login-input-group">
            <label>Username</label>
            <div className="login-input-wrap">
              <svg className="login-input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                autoFocus
                required
              />
            </div>
          </div>

          <div className="login-input-group">
            <label>Password</label>
            <div className="login-input-wrap">
              <svg className="login-input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
              />
              <button
                type="button"
                className="login-eye-btn"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
              >
                {showPassword ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {error && (
            <div className="login-error-new">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
              {error}
            </div>
          )}

          <button type="submit" className="login-submit" disabled={loading}>
            {loading ? (
              <span className="login-spinner" />
            ) : (
              <>
                Sign In
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginLeft: 6 }}>
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </>
            )}
          </button>
        </form>

        {/* Stats bar */}
        <div className="login-stats">
          <div className="login-stat">
            <span className="login-stat-value">14</span>
            <span className="login-stat-label">AI Tools</span>
          </div>
          <div className="login-stat-divider" />
          <div className="login-stat">
            <span className="login-stat-value">51</span>
            <span className="login-stat-label">US Stocks</span>
          </div>
          <div className="login-stat-divider" />
          <div className="login-stat">
            <span className="login-stat-value">Live</span>
            <span className="login-stat-label">WebSocket</span>
          </div>
        </div>

        {/* Footer */}
        <div className="login-card-footer">
          Smart Touch Infotech Private Limited
        </div>
      </div>
    </div>
  );
}

export default Login;
