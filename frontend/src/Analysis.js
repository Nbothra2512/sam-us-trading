// Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
// SAM (Smart Analyst for Markets) — Proprietary Software

import React, { useState, useEffect, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from 'recharts';
import './Analysis.css';

const BACKEND = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const API_URL = BACKEND + '/api';

function getToken() { return localStorage.getItem('sam_token') || ''; }
function authHeaders() { return { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' }; }

// ─── Signal Badge ────────────────────────────────────────────────
function SignalBadge({ signal, small }) {
  const cls = {
    'BULLISH': 'signal-bullish',
    'BEARISH': 'signal-bearish',
    'MIXED': 'signal-mixed',
    'NEUTRAL': 'signal-neutral',
  }[signal] || 'signal-neutral';
  return <span className={`signal-badge ${cls} ${small ? 'signal-sm' : ''}`}>{signal}</span>;
}

// ─── Severity Badge ──────────────────────────────────────────────
function SeverityDot({ severity }) {
  const cls = severity === 'high' ? 'sev-high' : severity === 'medium' ? 'sev-med' : 'sev-low';
  return <span className={`sev-dot ${cls}`} />;
}

// ─── S/R Level Bar ───────────────────────────────────────────────
function SRBar({ current, supports, resistances }) {
  if (!supports?.length && !resistances?.length) return null;

  const allLevels = [
    ...supports.map(s => ({ ...s, type: 'support' })),
    ...resistances.map(r => ({ ...r, type: 'resistance' })),
  ];
  const prices = [...allLevels.map(l => l.level), current];
  const min = Math.min(...prices) * 0.995;
  const max = Math.max(...prices) * 1.005;
  const range = max - min || 1;

  const pxPos = (price) => `${((price - min) / range) * 100}%`;

  return (
    <div className="sr-bar-wrap">
      <div className="sr-bar">
        {allLevels.map((lev, i) => (
          <div
            key={i}
            className={`sr-level ${lev.type}`}
            style={{ left: pxPos(lev.level) }}
            title={`${lev.type === 'support' ? 'S' : 'R'}: $${lev.level} (${lev.strength})`}
          >
            <span className="sr-level-line" />
          </div>
        ))}
        <div
          className="sr-current"
          style={{ left: pxPos(current) }}
          title={`Current: $${current}`}
        >
          <span className="sr-current-dot" />
        </div>
      </div>
      <div className="sr-labels">
        <span>${supports[0]?.level || '—'}</span>
        <span className="sr-current-label">${current}</span>
        <span>${resistances[0]?.level || '—'}</span>
      </div>
    </div>
  );
}

// ─── Stock Detail Modal ──────────────────────────────────────────
function StockDetail({ symbol, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/patterns/${symbol}?days=252`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : null)
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [symbol]);

  if (loading) return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="analysis-modal" onClick={e => e.stopPropagation()}>
        <div className="analysis-loading">Loading {symbol} analysis...</div>
      </div>
    </div>
  );

  if (!data) return null;

  const trend = data.trend || {};
  const sr = data.support_resistance || {};
  const mr = data.mean_reversion || {};
  const bo = data.breakout || {};

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="analysis-modal" onClick={e => e.stopPropagation()}>
        <div className="amodal-header">
          <h2>{symbol} <SignalBadge signal={data.overall_signal} /></h2>
          <button className="amodal-close" onClick={onClose}>&times;</button>
        </div>

        {/* Trend Section */}
        <div className="amodal-section">
          <h3>Trend Analysis</h3>
          <div className="amodal-grid">
            <div className="amodal-stat">
              <span className="amodal-label">Trend</span>
              <span className="amodal-value">{trend.trend || '—'}</span>
            </div>
            <div className="amodal-stat">
              <span className="amodal-label">Score</span>
              <span className={`amodal-value ${(trend.trend_score || 0) >= 0 ? 'green' : 'red'}`}>{trend.trend_score || 0}</span>
            </div>
            <div className="amodal-stat">
              <span className="amodal-label">ADX</span>
              <span className="amodal-value">{trend.adx || '—'} ({trend.trend_strength || '—'})</span>
            </div>
            <div className="amodal-stat">
              <span className="amodal-label">MACD</span>
              <span className={`amodal-value ${(trend.macd || 0) >= 0 ? 'green' : 'red'}`}>{trend.macd || '—'}</span>
            </div>
          </div>
          <div className="amodal-grid">
            <div className="amodal-stat">
              <span className="amodal-label">10d Return</span>
              <span className={`amodal-value ${(trend.return_10d || 0) >= 0 ? 'green' : 'red'}`}>{trend.return_10d || 0}%</span>
            </div>
            <div className="amodal-stat">
              <span className="amodal-label">30d Return</span>
              <span className={`amodal-value ${(trend.return_30d || 0) >= 0 ? 'green' : 'red'}`}>{trend.return_30d || 0}%</span>
            </div>
            <div className="amodal-stat">
              <span className="amodal-label">90d Return</span>
              <span className={`amodal-value ${(trend.return_90d || 0) >= 0 ? 'green' : 'red'}`}>{trend.return_90d || 0}%</span>
            </div>
          </div>
          <div className="amodal-ma-row">
            <span className={`ma-pill ${trend.above_20_ma ? 'ma-above' : 'ma-below'}`}>MA20: ${trend.sma_20}</span>
            <span className={`ma-pill ${trend.above_50_ma ? 'ma-above' : 'ma-below'}`}>MA50: ${trend.sma_50}</span>
            <span className={`ma-pill ${trend.above_200_ma ? 'ma-above' : 'ma-below'}`}>MA200: ${trend.sma_200}</span>
          </div>
          {trend.signals?.length > 0 && (
            <div className="amodal-signals">
              {trend.signals.map((s, i) => <div key={i} className="amodal-signal-item">{s}</div>)}
            </div>
          )}
        </div>

        {/* Support & Resistance */}
        <div className="amodal-section">
          <h3>Support & Resistance</h3>
          <SRBar
            current={sr.current_price}
            supports={sr.support || []}
            resistances={sr.resistance || []}
          />
          <div className="sr-table">
            <div className="sr-col">
              <h4 className="green">Support Levels</h4>
              {(sr.support || []).map((s, i) => (
                <div key={i} className="sr-row">
                  <span className="sr-price green">${s.level}</span>
                  <span className="sr-meta">{s.strength} | {s.touches} touches | {s.methods?.join(', ')}</span>
                  <span className="sr-dist">{s.distance_pct}% below</span>
                </div>
              ))}
            </div>
            <div className="sr-col">
              <h4 className="red">Resistance Levels</h4>
              {(sr.resistance || []).map((r, i) => (
                <div key={i} className="sr-row">
                  <span className="sr-price red">${r.level}</span>
                  <span className="sr-meta">{r.strength} | {r.touches} touches | {r.methods?.join(', ')}</span>
                  <span className="sr-dist">{r.distance_pct}% above</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Mean Reversion */}
        <div className="amodal-section">
          <h3>Mean Reversion</h3>
          <div className="amodal-grid">
            <div className="amodal-stat">
              <span className="amodal-label">RSI (14)</span>
              <span className={`amodal-value ${mr.rsi < 30 ? 'green' : mr.rsi > 70 ? 'red' : ''}`}>{mr.rsi || '—'}</span>
            </div>
            <div className="amodal-stat">
              <span className="amodal-label">Bollinger %</span>
              <span className="amodal-value">{mr.bollinger_position || '—'}%</span>
            </div>
            <div className="amodal-stat">
              <span className="amodal-label">Z-Score</span>
              <span className={`amodal-value ${(mr.z_score || 0) < -2 ? 'green' : (mr.z_score || 0) > 2 ? 'red' : ''}`}>{mr.z_score || '—'}</span>
            </div>
            <div className="amodal-stat">
              <span className="amodal-label">Signal</span>
              <span className={`amodal-value ${mr.signal?.includes('buy') ? 'green' : mr.signal?.includes('sell') ? 'red' : ''}`}>
                {mr.signal?.toUpperCase() || 'NEUTRAL'}
              </span>
            </div>
          </div>
          {mr.signals?.length > 0 && (
            <div className="amodal-signals">
              {mr.signals.map((s, i) => <div key={i} className="amodal-signal-item">{s}</div>)}
            </div>
          )}
        </div>

        {/* Breakout */}
        {bo.breakout && (
          <div className="amodal-section">
            <h3>Breakout Detected</h3>
            <div className={`breakout-banner ${bo.direction}`}>
              <span className="breakout-dir">{bo.direction?.toUpperCase()} BREAKOUT</span>
              <span>{bo.description}</span>
              <span>Breakout: {bo.breakout_pct}% | Volume confirmed: {bo.volume_confirmation ? 'Yes' : 'No'}</span>
            </div>
          </div>
        )}

        {/* Chart Patterns */}
        {data.chart_patterns?.length > 0 && (
          <div className="amodal-section">
            <h3>Chart Patterns</h3>
            {data.chart_patterns.map((cp, i) => (
              <div key={i} className={`pattern-card ${cp.signal?.includes('bullish') ? 'pattern-bullish' : 'pattern-bearish'}`}>
                <div className="pattern-name">{cp.pattern}</div>
                <div className="pattern-desc">{cp.description}</div>
                {cp.target && <div className="pattern-target">Target: ${cp.target}</div>}
              </div>
            ))}
          </div>
        )}

        {/* Recent Candlestick Patterns */}
        {data.recent_candlestick_patterns?.length > 0 && (
          <div className="amodal-section">
            <h3>Recent Candlestick Patterns</h3>
            <div className="candle-list">
              {data.recent_candlestick_patterns.slice(-6).map((p, i) => (
                <div key={i} className={`candle-item ${p.signal === 'bullish' ? 'candle-bull' : p.signal === 'bearish' ? 'candle-bear' : 'candle-neutral'}`}>
                  <span className="candle-date">{p.date}</span>
                  <span className="candle-name">{p.pattern}</span>
                  <span className={`candle-signal ${p.signal}`}>{p.signal}</span>
                  <span className="candle-str">{p.strength}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Analysis Panel ─────────────────────────────────────────
function Analysis({ refreshKey }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchAnalysis = useCallback(() => {
    setLoading(true);
    fetch(`${API_URL}/patterns/portfolio`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        setData(d);
        setLoading(false);
        setLastRefresh(new Date().toLocaleTimeString());
      })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchAnalysis();
  }, [fetchAnalysis]);

  // Refresh when portfolio changes
  useEffect(() => {
    if (refreshKey > 0) fetchAnalysis();
  }, [refreshKey, fetchAnalysis]);

  if (loading && !data) {
    return (
      <div className="analysis-panel">
        <div className="analysis-header">
          <h2>Pattern Analysis</h2>
        </div>
        <div className="analysis-loading">Scanning portfolio patterns...</div>
      </div>
    );
  }

  if (!data || !data.holdings || data.holdings.length === 0) {
    return (
      <div className="analysis-panel">
        <div className="analysis-header">
          <h2>Pattern Analysis</h2>
        </div>
        <div className="analysis-empty">Add stocks to your portfolio to see pattern analysis</div>
      </div>
    );
  }

  // Prepare chart data for signal scores
  const chartData = data.holdings
    .filter(h => h.signal_score !== undefined)
    .map(h => ({
      symbol: h.symbol,
      score: h.signal_score,
      fill: h.signal_score > 0 ? '#22c55e' : h.signal_score < 0 ? '#ef4444' : '#64748b',
    }));

  return (
    <div className="analysis-panel">
      {/* Header */}
      <div className="analysis-header">
        <div className="analysis-title-row">
          <h2>Pattern Analysis</h2>
          <SignalBadge signal={data.portfolio_signal} />
        </div>
        <div className="analysis-meta">
          <span>{data.bullish_count} bullish / {data.bearish_count} bearish / {data.neutral_count} neutral</span>
          <button className="analysis-refresh" onClick={fetchAnalysis} disabled={loading}>
            {loading ? 'Scanning...' : 'Refresh'}
          </button>
          {lastRefresh && <span className="analysis-time">Updated {lastRefresh}</span>}
        </div>
      </div>

      {/* Alerts */}
      {data.alerts?.length > 0 && (
        <div className="alerts-section">
          <h3>Alerts ({data.alerts.length})</h3>
          <div className="alerts-list">
            {data.alerts.slice(0, 10).map((a, i) => (
              <div key={i} className={`alert-item alert-${a.severity}`} onClick={() => setSelectedSymbol(a.symbol)}>
                <SeverityDot severity={a.severity} />
                <span className="alert-sym">{a.symbol}</span>
                <span className="alert-msg">{a.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Signal Score Chart */}
      {chartData.length > 0 && (
        <div className="score-chart-section">
          <h3>Signal Scores</h3>
          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={chartData} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
              <XAxis dataKey="symbol" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} domain={['auto', 'auto']} />
              <Tooltip
                contentStyle={{ background: '#151c2c', border: '1px solid #1e293b', borderRadius: 6, fontSize: 11 }}
                formatter={(val) => [val, 'Score']}
              />
              <Bar dataKey="score" radius={[3, 3, 0, 0]}>
                {chartData.map((entry, idx) => (
                  <Cell key={idx} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Holdings Grid */}
      <div className="holdings-grid">
        {data.holdings.map((h, i) => {
          if (h.error) {
            return (
              <div key={i} className="holding-card holding-error">
                <div className="hcard-header">
                  <span className="hcard-symbol">{h.symbol}</span>
                  <span className="hcard-error">No data</span>
                </div>
              </div>
            );
          }
          return (
            <div key={i} className="holding-card" onClick={() => setSelectedSymbol(h.symbol)}>
              <div className="hcard-header">
                <span className="hcard-symbol">{h.symbol}</span>
                <SignalBadge signal={h.signal} small />
              </div>
              <div className="hcard-price">${h.current_price}</div>
              <div className="hcard-trend">
                <span className={`hcard-trend-label ${(h.trend_score || 0) >= 0 ? 'green' : 'red'}`}>
                  {h.trend || '—'}
                </span>
              </div>

              {/* Mini S/R bar */}
              <SRBar
                current={h.current_price}
                supports={h.support_levels || []}
                resistances={h.resistance_levels || []}
              />

              <div className="hcard-stats">
                <div className="hcard-stat">
                  <span className="hcard-stat-label">RSI</span>
                  <span className={`hcard-stat-value ${h.rsi < 30 ? 'green' : h.rsi > 70 ? 'red' : ''}`}>
                    {h.rsi != null ? h.rsi.toFixed(0) : '—'}
                  </span>
                </div>
                <div className="hcard-stat">
                  <span className="hcard-stat-label">10d</span>
                  <span className={`hcard-stat-value ${(h.return_10d || 0) >= 0 ? 'green' : 'red'}`}>
                    {h.return_10d != null ? `${h.return_10d > 0 ? '+' : ''}${h.return_10d}%` : '—'}
                  </span>
                </div>
                <div className="hcard-stat">
                  <span className="hcard-stat-label">30d</span>
                  <span className={`hcard-stat-value ${(h.return_30d || 0) >= 0 ? 'green' : 'red'}`}>
                    {h.return_30d != null ? `${h.return_30d > 0 ? '+' : ''}${h.return_30d}%` : '—'}
                  </span>
                </div>
              </div>

              {/* Breakout indicator */}
              {h.breakout && (
                <div className={`hcard-breakout ${h.breakout_direction}`}>
                  BREAKOUT {h.breakout_direction?.toUpperCase()} {h.breakout_pct}%
                </div>
              )}

              {/* Recent patterns */}
              {h.recent_patterns?.length > 0 && (
                <div className="hcard-patterns">
                  {h.recent_patterns.slice(-2).map((p, j) => (
                    <span key={j} className={`hcard-pattern ${p.signal}`}>{p.pattern}</span>
                  ))}
                </div>
              )}

              <div className="hcard-footer">Click for full analysis</div>
            </div>
          );
        })}
      </div>

      {/* Detail Modal */}
      {selectedSymbol && (
        <StockDetail symbol={selectedSymbol} onClose={() => setSelectedSymbol(null)} />
      )}
    </div>
  );
}

export default Analysis;
