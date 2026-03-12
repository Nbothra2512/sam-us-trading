import React, { useState, useEffect, useRef } from 'react';
import './Portfolio.css';

const API_URL = 'http://localhost:8000/api';

function Portfolio({ refreshKey, onPortfolioChange }) {
  const [portfolio, setPortfolio] = useState(null);
  const [prevPrices, setPrevPrices] = useState({});
  const [flashing, setFlashing] = useState({});
  const [showExtended, setShowExtended] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [newQty, setNewQty] = useState('');
  const [newPrice, setNewPrice] = useState('');
  const refreshInterval = useRef(null);

  const fetchPortfolio = () => {
    fetch(`${API_URL}/portfolio`)
      .then(r => r.json())
      .then(data => {
        // Price flash: detect changes
        if (portfolio && portfolio.holdings) {
          const flashes = {};
          data.holdings.forEach(h => {
            const prev = prevPrices[h.symbol];
            if (prev !== undefined && prev !== h.last) {
              flashes[h.symbol] = h.last > prev ? 'flash-green' : 'flash-red';
            }
          });
          setFlashing(flashes);
          setTimeout(() => setFlashing({}), 500);
        }
        const prices = {};
        data.holdings.forEach(h => { prices[h.symbol] = h.last; });
        setPrevPrices(prices);
        setPortfolio(data);
      })
      .catch(() => {});
  };

  // Refresh on mount + every 15s
  useEffect(() => {
    fetchPortfolio();
    refreshInterval.current = setInterval(fetchPortfolio, 15000);
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
        // Notify parent so SAM chat knows too
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

  const session = portfolio?.session || 'CLOSED';
  const sessionClass = {
    'OPEN': 'session-open',
    'PRE-MARKET': 'session-pre',
    'AFTER-HOURS': 'session-ah',
    'CLOSED': 'session-closed',
  }[session] || 'session-closed';

  return (
    <div className="terminal">
      {/* Header */}
      <div className="terminal-header">
        <div className="terminal-title">
          <h1>uEquity</h1>
          <span className="terminal-subtitle">Live Portfolio Tracker</span>
        </div>
        <div className="terminal-controls">
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

      {/* Summary Bar: Total Portfolio Value, Total Cost, Unrealized P&L, Return %, Position Count */}
      {portfolio && portfolio.position_count > 0 && (
        <div className="summary-bar">
          <div className="summary-item">
            <span className="summary-label">Total Portfolio Value</span>
            <span className="summary-value">${fmt(portfolio.total_value)}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Total Cost</span>
            <span className="summary-value">${fmt(portfolio.total_cost)}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Unrealized P&L</span>
            <span className={`summary-value ${portfolio.total_pl >= 0 ? 'green' : 'red'}`}>
              {fmtDollarSign(portfolio.total_pl)}
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Return %</span>
            <span className={`summary-value ${portfolio.total_pl_pct >= 0 ? 'green' : 'red'}`}>
              {fmtPctSign(portfolio.total_pl_pct)}
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Positions</span>
            <span className="summary-value">{portfolio.position_count}</span>
          </div>
        </div>
      )}

      {/* Main Table: 5 Column Groups · 17 Data Points Per Position */}
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
            {portfolio && portfolio.holdings && portfolio.holdings.length > 0 ? (
              <>
                {portfolio.holdings.map(h => (
                  <tr key={h.symbol}>
                    {/* POSITION: Symbol, Qty, Buy Price, Cost Basis */}
                    <td className="symbol-cell">
                      <div className="symbol-name">{h.symbol}</div>
                      <div className="company-name">{h.name}</div>
                    </td>
                    <td>{h.qty}</td>
                    <td>${fmt(h.buy_price)}</td>
                    <td>${fmt(h.cost_basis)}</td>

                    {/* LIVE QUOTE: Last, Bid (orange), Ask (green), Mid + spread bar */}
                    <td className={`last-cell ${flashing[h.symbol] || ''}`}>${fmt(h.last)}</td>
                    <td className="bid-cell">${fmt(h.bid)}</td>
                    <td className="ask-cell">${fmt(h.ask)}</td>
                    <td className="mid-cell">
                      <div>${fmt(h.mid)}</div>
                      <div className="spread-bar-wrap" title={`Spread: $${h.spread_dollar} (${h.spread_pct}%)`}>
                        <div className="spread-bar" style={{ width: `${spreadBarWidth(h.spread_pct)}%` }}></div>
                      </div>
                    </td>

                    {/* DAY: CHG $, CHG % */}
                    <td className={h.day_chg >= 0 ? 'green' : 'red'}>
                      {h.day_chg >= 0 ? '+$' : '-$'}{fmt(Math.abs(h.day_chg))}
                    </td>
                    <td className={h.day_chg_pct >= 0 ? 'green' : 'red'}>
                      {fmtPctSign(h.day_chg_pct)}
                    </td>

                    {/* EXTENDED HOURS: Pre $, Pre %, AH $, AH % */}
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

                    {/* P&L: Mkt Value, P&L $, P&L % */}
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
                    TOTALS &middot; {portfolio.position_count} POSITIONS &middot; Portfolio Summary
                  </td>
                  <td className="bold">${fmt(portfolio.total_value)}</td>
                  <td className={`bold ${portfolio.total_pl >= 0 ? 'green' : 'red'}`}>{fmtDollarSign(portfolio.total_pl)}</td>
                  <td className={`bold ${portfolio.total_pl_pct >= 0 ? 'green' : 'red'}`}>{fmtPctSign(portfolio.total_pl_pct)}</td>
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
