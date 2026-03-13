// Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
// SAM (Smart Analyst for Markets) — Proprietary Software

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts';
import './Portfolio.css';

const BACKEND = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const API_URL = BACKEND + '/api';

function getToken() { return localStorage.getItem('sam_token') || ''; }
function authHeaders() { return { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' }; }
function getWsPricesUrl() { return BACKEND.replace(/^http/, 'ws') + '/ws/prices?token=' + getToken(); }

// ─── Search Popup Component ──────────────────────────────────────
function SearchPopup({ result, onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 5000);
    const handleClick = (e) => {
      if (!e.target.closest('.search-popup')) onClose();
    };
    document.addEventListener('click', handleClick);
    return () => { clearTimeout(timer); document.removeEventListener('click', handleClick); };
  }, [onClose]);

  if (!result) return null;
  if (result.error) {
    return (
      <div className="search-popup">
        <div className="search-popup-error">{result.error}</div>
      </div>
    );
  }

  const isUp = (result.change || 0) >= 0;
  return (
    <div className="search-popup" onClick={e => e.stopPropagation()}>
      <div className="search-popup-symbol">{result.symbol}</div>
      <div className="search-popup-price">${result.price?.toFixed(2)}</div>
      <div className={`search-popup-change ${isUp ? 'green' : 'red'}`}>
        {isUp ? '+' : ''}{result.change?.toFixed(2)} ({isUp ? '+' : ''}{result.change_pct?.toFixed(2)}%)
      </div>
    </div>
  );
}

// ─── P&L Mini Chart ─────────────────────────────────────────────
function PnlChart() {
  const [data, setData] = useState([]);

  useEffect(() => {
    try {
      const snapshots = JSON.parse(localStorage.getItem('sam_pnl_snapshots') || '[]');
      const chartData = snapshots.map(s => ({
        t: s.t,
        value: s.v,
        pnl: Math.round((s.v - s.c) * 100) / 100,
      }));
      setData(chartData);
    } catch {}
  }, []);

  if (data.length < 2) return null;

  const latestPnl = data[data.length - 1]?.pnl || 0;
  const isPositive = latestPnl >= 0;
  const color = isPositive ? '#22c55e' : '#ef4444';

  return (
    <div className="pnl-chart-wrap">
      <ResponsiveContainer width="100%" height={80}>
        <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="pnlFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Tooltip
            contentStyle={{ background: '#151c2c', border: '1px solid #1e293b', borderRadius: 6, fontSize: 11 }}
            labelStyle={{ display: 'none' }}
            formatter={(val) => [`$${val.toFixed(2)}`, 'P&L']}
          />
          <Area
            type="monotone"
            dataKey="pnl"
            stroke={color}
            strokeWidth={1.5}
            fill="url(#pnlFill)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── Watchlist Panel ────────────────────────────────────────────
function WatchlistPanel() {
  const [watchlist, setWatchlist] = useState([]);
  const [expanded, setExpanded] = useState(false);
  const [addSymbol, setAddSymbol] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchWatchlist = useCallback(() => {
    fetch(`${API_URL}/watchlist`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : [])
      .then(data => setWatchlist(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchWatchlist();
    const interval = setInterval(fetchWatchlist, 30000);
    return () => clearInterval(interval);
  }, [fetchWatchlist]);

  const addToWatchlist = () => {
    if (!addSymbol.trim()) return;
    setLoading(true);
    fetch(`${API_URL}/watchlist/add`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ symbol: addSymbol.trim().toUpperCase() }),
    })
      .then(() => { setAddSymbol(''); fetchWatchlist(); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  const removeFromWatchlist = (symbol) => {
    fetch(`${API_URL}/watchlist/remove`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ symbol }),
    })
      .then(() => fetchWatchlist())
      .catch(() => {});
  };

  return (
    <div className="watchlist-section">
      <button className="watchlist-toggle" onClick={() => setExpanded(!expanded)}>
        {expanded ? '\u25BC' : '\u25B6'} Watchlist ({watchlist.length})
      </button>
      {expanded && (
        <div className="watchlist-panel">
          <div className="watchlist-add">
            <input
              placeholder="Add symbol..."
              value={addSymbol}
              onChange={e => setAddSymbol(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') addToWatchlist(); }}
            />
            <button onClick={addToWatchlist} disabled={loading || !addSymbol.trim()}>+</button>
          </div>
          {watchlist.length === 0 ? (
            <div className="watchlist-empty">No symbols in watchlist</div>
          ) : (
            <div className="watchlist-items">
              {watchlist.map(w => (
                <div key={w.symbol} className="watchlist-item">
                  <span className="watchlist-sym">{w.symbol}</span>
                  <span className="watchlist-price">${(w.price || 0).toFixed(2)}</span>
                  <span className={`watchlist-chg ${(w.change_pct || 0) >= 0 ? 'green' : 'red'}`}>
                    {(w.change_pct || 0) >= 0 ? '+' : ''}{(w.change_pct || 0).toFixed(2)}%
                  </span>
                  <button className="watchlist-remove" onClick={() => removeFromWatchlist(w.symbol)}>&times;</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main Portfolio Component ───────────────────────────────────
function Portfolio({ refreshKey, onPortfolioChange, onLogout, theme, onToggleTheme }) {
  const [portfolio, setPortfolio] = useState(null);
  const [prevPrices, setPrevPrices] = useState({});
  const [livePrices, setLivePrices] = useState({});
  const [flashing, setFlashing] = useState({});
  const [showExtended, setShowExtended] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [newQty, setNewQty] = useState('');
  const [newPrice, setNewPrice] = useState('');
  const [feedStatus, setFeedStatus] = useState('connecting');

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResult, setSearchResult] = useState(null);

  const priceWsRef = useRef(null);
  const refreshInterval = useRef(null);
  const flashTimerRef = useRef(null);

  // Fetch full portfolio data (REST)
  const fetchPortfolio = useCallback(() => {
    fetch(`${API_URL}/portfolio`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => {
        if (portfolio && portfolio.holdings) {
          const flashes = {};
          data.holdings.forEach(h => {
            const prev = prevPrices[h.symbol];
            if (prev !== undefined && prev !== h.last) {
              flashes[h.symbol] = h.last > prev ? 'flash-green' : 'flash-red';
            }
          });
          if (Object.keys(flashes).length > 0) {
            setFlashing(flashes);
            if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
            flashTimerRef.current = setTimeout(() => setFlashing({}), 500);
          }
        }
        const prices = {};
        data.holdings.forEach(h => { prices[h.symbol] = h.last; });
        setPrevPrices(prices);
        setPortfolio(data);
      })
      .catch(() => {});
  }, [portfolio, prevPrices]);

  // Real-time price WebSocket
  useEffect(() => {
    let reconnectTimer;
    const connectPriceWs = () => {
      const ws = new WebSocket(getWsPricesUrl());
      ws.onopen = () => {
        setFeedStatus('live');
        if (portfolio && portfolio.holdings) {
          const symbols = portfolio.holdings.map(h => h.symbol);
          if (symbols.length > 0) {
            ws.send(JSON.stringify({ type: 'subscribe', symbols }));
          }
        }
      };
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'price_update' && data.prices) {
            setLivePrices(prev => {
              const updated = { ...prev };
              const flashes = {};
              for (const [symbol, info] of Object.entries(data.prices)) {
                const oldPrice = prev[symbol]?.price || prevPrices[symbol];
                if (oldPrice !== undefined && info.price !== oldPrice) {
                  flashes[symbol] = info.price > oldPrice ? 'flash-green' : 'flash-red';
                }
                updated[symbol] = info;
              }
              if (Object.keys(flashes).length > 0) {
                setFlashing(f => ({ ...f, ...flashes }));
                if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
                flashTimerRef.current = setTimeout(() => setFlashing({}), 500);
              }
              return updated;
            });
          }
        } catch (e) { /* ignore */ }
      };
      ws.onclose = () => {
        setFeedStatus('reconnecting');
        reconnectTimer = setTimeout(connectPriceWs, 2000);
      };
      ws.onerror = () => {
        setFeedStatus('error');
        ws.close();
      };
      priceWsRef.current = ws;
    };
    connectPriceWs();
    return () => {
      clearTimeout(reconnectTimer);
      if (priceWsRef.current) priceWsRef.current.close();
    };
  }, []);

  // Re-subscribe when portfolio changes
  useEffect(() => {
    if (priceWsRef.current && priceWsRef.current.readyState === WebSocket.OPEN && portfolio?.holdings) {
      const symbols = portfolio.holdings.map(h => h.symbol);
      if (symbols.length > 0) {
        priceWsRef.current.send(JSON.stringify({ type: 'subscribe', symbols }));
      }
    }
  }, [portfolio?.holdings?.length]);

  // REST refresh on mount + every 30s
  useEffect(() => {
    fetchPortfolio();
    refreshInterval.current = setInterval(fetchPortfolio, 30000);
    return () => clearInterval(refreshInterval.current);
  }, []);

  // Refresh when parent triggers
  useEffect(() => {
    if (refreshKey > 0) fetchPortfolio();
  }, [refreshKey]);

  // Auto-show extended hours
  useEffect(() => {
    if (portfolio && (portfolio.session === 'PRE-MARKET' || portfolio.session === 'AFTER-HOURS')) {
      setShowExtended(true);
    }
  }, [portfolio?.session]);

  const addPosition = () => {
    if (!newSymbol || !newQty || !newPrice) return;
    fetch(`${API_URL}/portfolio/add`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        symbol: newSymbol.toUpperCase(),
        qty: parseFloat(newQty),
        avg_price: parseFloat(newPrice),
      }),
    })
      .then(() => {
        setShowAddModal(false);
        setNewSymbol('');
        setNewQty('');
        setNewPrice('');
        fetchPortfolio();
        if (onPortfolioChange) onPortfolioChange();
      })
      .catch(() => {});
  };

  const removePosition = (symbol) => {
    fetch(`${API_URL}/portfolio/remove`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ symbol }),
    })
      .then(() => {
        fetchPortfolio();
        if (onPortfolioChange) onPortfolioChange();
      })
      .catch(() => {});
  };

  // Search handler
  const handleSearch = () => {
    if (!searchQuery.trim()) return;
    fetch(`${API_URL}/quote/${searchQuery.trim().toUpperCase()}`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : { error: `No data for ${searchQuery.toUpperCase()}` })
      .then(data => setSearchResult(data))
      .catch(() => setSearchResult({ error: 'Failed to fetch quote' }));
  };

  // Merge live streamed prices with REST data
  const getDisplayPrice = (holding) => {
    const liveData = livePrices[holding.symbol];
    if (liveData && liveData.price) {
      const last = liveData.price;
      const market_value = Math.round(last * holding.qty * 100) / 100;
      const pl = Math.round((last - holding.buy_price) * holding.qty * 100) / 100;
      const pl_pct = holding.buy_price ? Math.round(((last - holding.buy_price) / holding.buy_price) * 10000) / 100 : 0;
      const day_chg = holding.prev_close ? Math.round((last - holding.prev_close) * 100) / 100 : holding.day_chg;
      const day_chg_pct = holding.prev_close ? Math.round(((last - holding.prev_close) / holding.prev_close) * 10000) / 100 : holding.day_chg_pct;
      const spread_half = Math.max(Math.round(last * 0.0001 * 100) / 100, 0.01);
      const bid = Math.round((last - spread_half) * 100) / 100;
      const ask = Math.round((last + spread_half) * 100) / 100;
      const mid = Math.round((bid + ask) / 2 * 100) / 100;
      return { ...holding, last, bid, ask, mid, market_value, pl, pl_pct, day_chg, day_chg_pct, prev_close: holding.prev_close };
    }
    return holding;
  };

  const fmt = (n, decimals = 2) => {
    if (n === null || n === undefined) return '\u2014';
    return n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  };

  const fmtDollarSign = (n) => {
    if (n === null || n === undefined) return '\u2014';
    const prefix = n >= 0 ? '+$' : '-$';
    return prefix + fmt(Math.abs(n));
  };

  const fmtPctSign = (n) => {
    if (n === null || n === undefined) return '\u2014';
    const prefix = n >= 0 ? '+' : '-';
    return prefix + fmt(Math.abs(n)) + '%';
  };

  const spreadBarWidth = (spreadPct) => {
    if (!spreadPct) return 0;
    return Math.min(spreadPct / 0.5 * 100, 100);
  };

  const displayHoldings = portfolio?.holdings?.map(getDisplayPrice) || [];
  const totalValue = displayHoldings.reduce((sum, h) => sum + (h.market_value || 0), 0);
  const totalCost = displayHoldings.reduce((sum, h) => sum + (h.cost_basis || 0), 0);
  const totalPl = Math.round((totalValue - totalCost) * 100) / 100;
  const totalPlPct = totalCost ? Math.round(((totalValue - totalCost) / totalCost) * 10000) / 100 : 0;

  const session = portfolio?.session || 'CLOSED';
  const sessionClass = {
    'OPEN': 'session-open',
    'PRE-MARKET': 'session-pre',
    'AFTER-HOURS': 'session-ah',
    'CLOSED': 'session-closed',
  }[session] || 'session-closed';

  const feedStatusClass = {
    'live': 'feed-live',
    'connecting': 'feed-connecting',
    'reconnecting': 'feed-connecting',
    'error': 'feed-error',
  }[feedStatus] || 'feed-connecting';

  return (
    <div className="terminal">
      {/* Header */}
      <div className="terminal-header">
        <div className="terminal-title">
          <h1>uEquity</h1>
          <span className="terminal-subtitle">Live Portfolio Tracker</span>
        </div>
        <div className="terminal-controls">
          {/* Search Bar */}
          <div className="search-bar-wrap">
            <input
              className="search-bar"
              placeholder="Search symbol..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleSearch(); }}
            />
            <button className="search-btn" onClick={handleSearch} title="Search">&#128269;</button>
            {searchResult && (
              <SearchPopup result={searchResult} onClose={() => setSearchResult(null)} />
            )}
          </div>
          <span className={`feed-badge ${feedStatusClass}`} title={`Data feed: ${feedStatus}`}>
            {feedStatus === 'live' ? 'LIVE FEED' : feedStatus === 'connecting' ? 'CONNECTING...' : feedStatus === 'reconnecting' ? 'RECONNECTING...' : 'FEED ERROR'}
          </span>
          <span className={`session-badge ${sessionClass}`}>{session}</span>
          <button
            className={`ext-toggle ${showExtended ? 'active' : ''}`}
            onClick={() => setShowExtended(!showExtended)}
          >
            Extended Hours
          </button>
          <button className="add-btn" onClick={() => setShowAddModal(true)}>+ Add Position</button>
          {/* Theme Toggle */}
          <button className="theme-toggle" onClick={onToggleTheme} title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
            {theme === 'dark' ? '\u2600' : '\uD83C\uDF19'}
          </button>
          {onLogout && <button className="logout-btn" onClick={onLogout}>Logout</button>}
        </div>
      </div>

      {/* Summary Bar with P&L Chart */}
      {portfolio && displayHoldings.length > 0 && (
        <div className="summary-bar">
          <div className="summary-item">
            <span className="summary-label">Total Portfolio Value</span>
            <span className="summary-value">${fmt(totalValue)}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Total Cost</span>
            <span className="summary-value">${fmt(totalCost)}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Unrealized P&L</span>
            <span className={`summary-value ${totalPl >= 0 ? 'green' : 'red'}`}>
              {fmtDollarSign(totalPl)}
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Return %</span>
            <span className={`summary-value ${totalPlPct >= 0 ? 'green' : 'red'}`}>
              {fmtPctSign(totalPlPct)}
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Positions</span>
            <span className="summary-value">{displayHoldings.length}</span>
          </div>
          <div className="summary-item summary-chart">
            <span className="summary-label">P&L Trend</span>
            <PnlChart />
          </div>
        </div>
      )}

      {/* Watchlist */}
      <WatchlistPanel />

      {/* Main Table */}
      <div className="table-wrap">
        <table className="equity-table">
          <thead>
            <tr className="group-header">
              <th colSpan="4" className="group-position">POSITION</th>
              <th colSpan="4" className="group-quote">LIVE QUOTE</th>
              <th colSpan="2" className="group-day">DAY</th>
              {showExtended && <th colSpan="4" className="group-extended">EXTENDED HOURS</th>}
              <th colSpan="3" className="group-pl">P & L</th>
              <th className="group-action"></th>
            </tr>
            <tr className="col-header">
              <th className="left">SYMBOL</th>
              <th>QTY</th>
              <th>BUY PRICE</th>
              <th>COST BASIS</th>
              <th>LAST</th>
              <th className="bid-col">BID</th>
              <th className="ask-col">ASK</th>
              <th>MID</th>
              <th>CHG $</th>
              <th>CHG %</th>
              {showExtended && (
                <>
                  <th>PRE $</th>
                  <th>PRE %</th>
                  <th>AH $</th>
                  <th>AH %</th>
                </>
              )}
              <th>MKT VALUE</th>
              <th>P&L $</th>
              <th>P&L %</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {displayHoldings.length > 0 ? (
              <>
                {displayHoldings.map(h => (
                  <tr key={h.symbol}>
                    <td className="symbol-cell">
                      <div className="symbol-name">{h.symbol}</div>
                      <div className="company-name">{h.name}</div>
                    </td>
                    <td>{h.qty}</td>
                    <td>${fmt(h.buy_price)}</td>
                    <td>${fmt(h.cost_basis)}</td>
                    <td className={`last-cell ${flashing[h.symbol] || ''}`}>${fmt(h.last)}</td>
                    <td className="bid-cell">${fmt(h.bid)}</td>
                    <td className="ask-cell">${fmt(h.ask)}</td>
                    <td className="mid-cell">
                      <div>${fmt(h.mid)}</div>
                      <div className="spread-bar-wrap" title={`Spread: $${h.spread_dollar} (${h.spread_pct}%)`}>
                        <div className="spread-bar" style={{ width: `${spreadBarWidth(h.spread_pct)}%` }}></div>
                      </div>
                    </td>
                    <td className={h.day_chg >= 0 ? 'green' : 'red'}>
                      {h.day_chg >= 0 ? '+$' : '-$'}{fmt(Math.abs(h.day_chg))}
                    </td>
                    <td className={h.day_chg_pct >= 0 ? 'green' : 'red'}>
                      {fmtPctSign(h.day_chg_pct)}
                    </td>
                    {showExtended && (
                      <>
                        <td>{h.pre_price != null ? `$${fmt(h.pre_price)}` : '\u2014'}</td>
                        <td className={h.pre_pct != null ? (h.pre_pct >= 0 ? 'green' : 'red') : ''}>
                          {h.pre_pct != null ? fmtPctSign(h.pre_pct) : '\u2014'}
                        </td>
                        <td>{h.ah_price != null ? `$${fmt(h.ah_price)}` : '\u2014'}</td>
                        <td className={h.ah_pct != null ? (h.ah_pct >= 0 ? 'green' : 'red') : ''}>
                          {h.ah_pct != null ? fmtPctSign(h.ah_pct) : '\u2014'}
                        </td>
                      </>
                    )}
                    <td className="bold">${fmt(h.market_value)}</td>
                    <td className={`bold ${h.pl >= 0 ? 'green' : 'red'}`}>{fmtDollarSign(h.pl)}</td>
                    <td className={`bold ${h.pl_pct >= 0 ? 'green' : 'red'}`}>{fmtPctSign(h.pl_pct)}</td>
                    <td>
                      <button className="remove-btn" onClick={() => removePosition(h.symbol)} title="Remove">x</button>
                    </td>
                  </tr>
                ))}
                {/* TOTALS row */}
                <tr className="totals-row">
                  <td colSpan={showExtended ? 14 : 10} className="totals-label">
                    TOTALS &middot; {displayHoldings.length} POSITIONS &middot; Portfolio Summary
                  </td>
                  <td className="bold">${fmt(totalValue)}</td>
                  <td className={`bold ${totalPl >= 0 ? 'green' : 'red'}`}>{fmtDollarSign(totalPl)}</td>
                  <td className={`bold ${totalPlPct >= 0 ? 'green' : 'red'}`}>{fmtPctSign(totalPlPct)}</td>
                  <td></td>
                </tr>
              </>
            ) : (
              <tr>
                <td colSpan={showExtended ? 18 : 14} className="empty-msg">
                  No positions yet. Click "+ Add Position" or tell SAM to add one.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Color Legend */}
      <div className="legend">
        <span><i className="dot bid-dot"></i> BID = Orange</span>
        <span><i className="dot ask-dot"></i> ASK = Green</span>
        <span>MID = (BID+ASK)/2</span>
        <span><i className="dot last-dot"></i> LAST = Most recent trade</span>
        <span className="green">&#9650; Green = Gain / Up</span>
        <span className="red">&#9660; Red = Loss / Down</span>
      </div>

      {/* Add Position Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Add Position</h3>
            <label>Symbol</label>
            <input placeholder="e.g. AAPL" value={newSymbol} onChange={e => setNewSymbol(e.target.value)} autoFocus
              onKeyDown={e => { if (e.key === 'Enter') addPosition(); }}
            />
            <label>Quantity</label>
            <input placeholder="Number of shares" type="number" value={newQty} onChange={e => setNewQty(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') addPosition(); }}
            />
            <label>Buy Price</label>
            <input placeholder="Average purchase price" type="number" step="0.01" value={newPrice} onChange={e => setNewPrice(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') addPosition(); }}
            />
            <div className="modal-preview">
              {newQty && newPrice && (
                <span>Cost Basis = ${(parseFloat(newQty || 0) * parseFloat(newPrice || 0)).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
              )}
            </div>
            <div className="modal-actions">
              <button className="modal-cancel" onClick={() => setShowAddModal(false)}>Cancel</button>
              <button className="modal-add" onClick={addPosition} disabled={!newSymbol || !newQty || !newPrice}>Add Position</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Portfolio;
