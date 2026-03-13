// Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
// SAM (Smart Analyst for Markets) — Proprietary Software

import React, { useState, useEffect, useRef, useCallback } from 'react';
import './Portfolio.css';

const BACKEND = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const API_URL = BACKEND + '/api';
const WS_PRICES_URL = BACKEND.replace(/^http/, 'ws') + '/ws/prices';

function Portfolio({ refreshKey, onPortfolioChange }) {
  const [portfolio, setPortfolio] = useState(null);
  const [prevPrices, setPrevPrices] = useState({});
  const [livePrices, setLivePrices] = useState({});    // Real-time streamed prices
  const [flashing, setFlashing] = useState({});
  const [showExtended, setShowExtended] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [newQty, setNewQty] = useState('');
  const [newPrice, setNewPrice] = useState('');
  const [feedStatus, setFeedStatus] = useState('connecting');
  const priceWsRef = useRef(null);
  const refreshInterval = useRef(null);
  const flashTimerRef = useRef(null);

  // Fetch full portfolio data (REST — for initial load and P&L calculations)
  const fetchPortfolio = useCallback(() => {
    fetch(`${API_URL}/portfolio`)
      .then(r => r.json())
      .then(data => {
        // Price flash on REST refresh
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

  // ─── Real-time price WebSocket ─────────────────────────────────
  useEffect(() => {
    let reconnectTimer;

    const connectPriceWs = () => {
      const ws = new WebSocket(WS_PRICES_URL);

      ws.onopen = () => {
        setFeedStatus('live');
        // Subscribe to all portfolio symbols
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
        } catch (e) { /* ignore parse errors */ }
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
  }, []); // Connect once on mount

  // Re-subscribe when portfolio changes
  useEffect(() => {
    if (priceWsRef.current && priceWsRef.current.readyState === WebSocket.OPEN && portfolio?.holdings) {
      const symbols = portfolio.holdings.map(h => h.symbol);
      if (symbols.length > 0) {
        priceWsRef.current.send(JSON.stringify({ type: 'subscribe', symbols }));
      }
    }
  }, [portfolio?.holdings?.length]);

  // REST refresh on mount + every 30s (fallback — main updates come via WebSocket)
  useEffect(() => {
    fetchPortfolio();
    refreshInterval.current = setInterval(fetchPortfolio, 30000);
    return () => clearInterval(refreshInterval.current);
  }, []);

  // Refresh when parent triggers (SAM chat added/removed a holding)
  useEffect(() => {
    if (refreshKey > 0) {
      fetchPortfolio();
    }
  }, [refreshKey]);

  // Auto-show extended hours during pre-market/after-hours
  useEffect(() => {
    if (portfolio && (portfolio.session === 'PRE-MARKET' || portfolio.session === 'AFTER-HOURS')) {
      setShowExtended(true);
    }
  }, [portfolio?.session]);

  const addPosition = () => {
    if (!newSymbol || !newQty || !newPrice) return;
    fetch(`${API_URL}/portfolio/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol }),
    })
      .then(() => {
        fetchPortfolio();
        if (onPortfolioChange) onPortfolioChange();
      })
      .catch(() => {});
  };

  // ─── Merge live streamed prices with REST data ─────────────────
  const getDisplayPrice = (holding) => {
    const liveData = livePrices[holding.symbol];
    if (liveData && liveData.price) {
      // Recalculate P&L with live price
      const last = liveData.price;
      const market_value = Math.round(last * holding.qty * 100) / 100;
      const pl = Math.round((last - holding.buy_price) * holding.qty * 100) / 100;
      const pl_pct = holding.buy_price ? Math.round(((last - holding.buy_price) / holding.buy_price) * 10000) / 100 : 0;
      const day_chg = holding.prev_close ? Math.round((last - holding.prev_close) * 100) / 100 : holding.day_chg;
      const day_chg_pct = holding.prev_close ? Math.round(((last - holding.prev_close) / holding.prev_close) * 10000) / 100 : holding.day_chg_pct;

      // Estimate bid/ask from live price
      const spread_half = Math.max(Math.round(last * 0.0001 * 100) / 100, 0.01);
      const bid = Math.round((last - spread_half) * 100) / 100;
      const ask = Math.round((last + spread_half) * 100) / 100;
      const mid = Math.round((bid + ask) / 2 * 100) / 100;

      return {
        ...holding,
        last, bid, ask, mid,
        market_value, pl, pl_pct,
        day_chg, day_chg_pct,
        prev_close: holding.prev_close,
      };
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

  // Compute display holdings with live prices merged
  const displayHoldings = portfolio?.holdings?.map(getDisplayPrice) || [];

  // Recompute totals from live data
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
        </div>
      </div>

      {/* Summary Bar */}
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
        </div>
      )}

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
