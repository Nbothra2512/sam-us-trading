// Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
// SAM (Smart Analyst for Markets) — Proprietary Software

import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import Portfolio from './Portfolio';
import Login from './Login';
import ToastContainer, { showToast } from './Toast';
import './App.css';

const BACKEND = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const API_URL = BACKEND + '/api';

function getToken() {
  return localStorage.getItem('sam_token') || '';
}

function getWsUrl(path) {
  const token = getToken();
  return BACKEND.replace(/^http/, 'ws') + path + '?token=' + token;
}

function authHeaders() {
  return { Authorization: `Bearer ${getToken()}` };
}

// ─── Ticker Tape Component ──────────────────────────────────────
function TickerTape() {
  const [tickers, setTickers] = useState([]);
  const INDICES = [
    { symbol: 'SPY', label: 'S&P 500' },
    { symbol: 'QQQ', label: 'NASDAQ' },
    { symbol: 'DIA', label: 'DOW' },
  ];

  const fetchTickers = useCallback(() => {
    const token = getToken();
    if (!token) return;
    Promise.all(
      INDICES.map(idx =>
        fetch(`${API_URL}/quote/${idx.symbol}`, { headers: { Authorization: `Bearer ${token}` } })
          .then(r => r.ok ? r.json() : null)
          .catch(() => null)
      )
    ).then(results => {
      const data = results.map((r, i) => {
        if (!r || r.error) return { ...INDICES[i], price: null, change: 0, change_pct: 0 };
        return { ...INDICES[i], price: r.price, change: r.change, change_pct: r.change_pct };
      });
      setTickers(data);
    });
  }, []);

  useEffect(() => {
    fetchTickers();
    const interval = setInterval(fetchTickers, 30000);
    return () => clearInterval(interval);
  }, [fetchTickers]);

  if (tickers.length === 0) return null;

  // Duplicate for seamless scrolling
  const items = [...tickers, ...tickers, ...tickers];

  return (
    <div className="ticker-tape">
      <div className="ticker-scroll">
        {items.map((t, i) => (
          <span key={i} className="ticker-item">
            <span className="ticker-label">{t.label}</span>
            <span className="ticker-symbol">{t.symbol}</span>
            {t.price != null ? (
              <>
                <span className="ticker-price">${t.price.toFixed(2)}</span>
                <span className={`ticker-change ${t.change >= 0 ? 'green' : 'red'}`}>
                  {t.change >= 0 ? '+' : ''}{t.change.toFixed(2)} ({t.change >= 0 ? '+' : ''}{t.change_pct.toFixed(2)}%)
                </span>
              </>
            ) : (
              <span className="ticker-price">--</span>
            )}
          </span>
        ))}
      </div>
    </div>
  );
}

// ─── Chat Tabs Logic ────────────────────────────────────────────
function loadChatTabs() {
  try {
    const saved = localStorage.getItem('sam_chat_tabs');
    if (saved) return JSON.parse(saved);
  } catch {}
  return [{ id: 'general', name: 'General' }];
}

function saveChatTabs(tabs) {
  localStorage.setItem('sam_chat_tabs', JSON.stringify(tabs));
}

function loadTabMessages(tabId) {
  try {
    const saved = localStorage.getItem(`sam_chat_${tabId}`);
    if (saved) return JSON.parse(saved);
  } catch {}
  return [];
}

function saveTabMessages(tabId, messages) {
  localStorage.setItem(`sam_chat_${tabId}`, JSON.stringify(messages));
}

// ─── Main App ───────────────────────────────────────────────────
function App() {
  const [token, setToken] = useState(() => localStorage.getItem('sam_token') || '');
  const [theme, setTheme] = useState(() => localStorage.getItem('sam_theme') || 'dark');

  // Chat tabs
  const [chatTabs, setChatTabs] = useState(loadChatTabs);
  const [activeTab, setActiveTab] = useState(() => {
    const tabs = loadChatTabs();
    return tabs.length > 0 ? tabs[0].id : 'general';
  });
  const [messages, setMessages] = useState(() => loadTabMessages(activeTab));

  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [connected, setConnected] = useState(false);
  const [portfolioData, setPortfolioData] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // Panel state: 'both', 'portfolio', 'chat'
  const [panelMode, setPanelMode] = useState('both');
  const [mobileTab, setMobileTab] = useState('portfolio');
  const [splitPct, setSplitPct] = useState(50);
  const isDragging = useRef(false);

  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const layoutRef = useRef(null);
  const prevPortfolioRef = useRef(null);

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('sam_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const handleLogout = () => {
    localStorage.removeItem('sam_token');
    localStorage.removeItem('sam_user');
    setToken('');
    wsRef.current?.close();
  };

  // Verify token on mount
  useEffect(() => {
    if (!token) return;
    fetch(`${API_URL}/auth/verify`, { headers: authHeaders() })
      .then(r => { if (!r.ok) handleLogout(); })
      .catch(() => handleLogout());
  }, [token]);

  // Shared portfolio fetch
  const fetchPortfolio = useCallback(() => {
    if (!token) return;
    fetch(`${API_URL}/portfolio`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (!d) return;
        // Check for alerts before updating state
        if (prevPortfolioRef.current && d.holdings) {
          const today = new Date().toISOString().slice(0, 10);
          d.holdings.forEach(h => {
            // 5% move alert
            if (Math.abs(h.day_chg_pct) >= 5) {
              const dir = h.day_chg_pct >= 0 ? 'up' : 'down';
              showToast(`${h.symbol} is ${dir} ${Math.abs(h.day_chg_pct).toFixed(1)}% today!`, 'alert');
            }
          });
          // Earnings today check (only once per refresh cycle)
          if (!prevPortfolioRef.current._earningsChecked) {
            fetch(`${API_URL}/earnings?from_date=${today}&to_date=${today}`, { headers: authHeaders() })
              .then(r => r.ok ? r.json() : null)
              .then(earningsData => {
                if (earningsData?.earnings) {
                  const portfolioSymbols = new Set(d.holdings.map(h => h.symbol));
                  earningsData.earnings.forEach(e => {
                    if (portfolioSymbols.has(e.symbol)) {
                      showToast(`${e.symbol} reports earnings today (${e.hour === 'bmo' ? 'before open' : 'after close'})`, 'earnings');
                    }
                  });
                }
              })
              .catch(() => {});
            d._earningsChecked = true;
          }
        }
        prevPortfolioRef.current = d;
        setPortfolioData(d);

        // Save portfolio value snapshot for P&L chart
        if (d.holdings && d.holdings.length > 0) {
          const totalVal = d.holdings.reduce((sum, h) => sum + (h.market_value || 0), 0);
          const totalCost = d.holdings.reduce((sum, h) => sum + (h.cost_basis || 0), 0);
          if (totalVal > 0) {
            try {
              const snapshots = JSON.parse(localStorage.getItem('sam_pnl_snapshots') || '[]');
              const now = Date.now();
              // Only add if last snapshot was > 5 minutes ago
              if (snapshots.length === 0 || now - snapshots[snapshots.length - 1].t > 300000) {
                snapshots.push({ t: now, v: Math.round(totalVal * 100) / 100, c: Math.round(totalCost * 100) / 100 });
                // Keep last 200 snapshots
                if (snapshots.length > 200) snapshots.splice(0, snapshots.length - 200);
                localStorage.setItem('sam_pnl_snapshots', JSON.stringify(snapshots));
              }
            } catch {}
          }
        }
      })
      .catch(() => {});
  }, [token]);

  const triggerRefresh = useCallback(() => {
    setRefreshKey(k => k + 1);
    fetchPortfolio();
  }, [fetchPortfolio]);

  useEffect(() => {
    if (!token) return;
    fetchPortfolio();
    const interval = setInterval(fetchPortfolio, 30000);
    return () => clearInterval(interval);
  }, [fetchPortfolio, token]);

  useEffect(() => {
    if (!token) return;
    const connect = () => {
      const ws = new WebSocket(getWsUrl('/ws/chat'));
      ws.onopen = () => setConnected(true);
      ws.onclose = (e) => {
        setConnected(false);
        if (e.code === 4001) { handleLogout(); return; }
        setTimeout(connect, 3000);
      };
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'typing') {
          setIsTyping(data.status);
        } else if (data.type === 'message') {
          setMessages(prev => [...prev, { role: 'assistant', content: data.content }]);
          triggerRefresh();
        } else if (data.type === 'error') {
          setMessages(prev => [...prev, { role: 'error', content: data.content }]);
        }
      };
      wsRef.current = ws;
    };
    connect();
    return () => wsRef.current?.close();
  }, [triggerRefresh, token]);

  // Persist messages for active tab
  useEffect(() => {
    saveTabMessages(activeTab, messages);
  }, [messages, activeTab]);

  // Save tabs
  useEffect(() => {
    saveChatTabs(chatTabs);
  }, [chatTabs]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Switch tab
  const switchTab = (tabId) => {
    saveTabMessages(activeTab, messages);
    setActiveTab(tabId);
    setMessages(loadTabMessages(tabId));
  };

  const addTab = () => {
    const name = prompt('Tab name:');
    if (!name || !name.trim()) return;
    const id = 'tab_' + Date.now();
    const newTabs = [...chatTabs, { id, name: name.trim() }];
    setChatTabs(newTabs);
    switchTab(id);
  };

  const closeTab = (tabId, e) => {
    e.stopPropagation();
    if (chatTabs.length <= 1) return;
    const newTabs = chatTabs.filter(t => t.id !== tabId);
    setChatTabs(newTabs);
    localStorage.removeItem(`sam_chat_${tabId}`);
    if (activeTab === tabId) {
      const nextTab = newTabs[0].id;
      setActiveTab(nextTab);
      setMessages(loadTabMessages(nextTab));
    }
  };

  // ─── Drag to resize ─────────────────────────────────────────────
  const handleDragStart = useCallback((e) => {
    e.preventDefault();
    isDragging.current = true;
    document.body.style.cursor = 'row-resize';
    document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const handleDrag = (e) => {
      if (!isDragging.current || !layoutRef.current) return;
      const rect = layoutRef.current.getBoundingClientRect();
      const y = (e.clientY || e.touches?.[0]?.clientY) - rect.top;
      const pct = Math.min(Math.max((y / rect.height) * 100, 15), 85);
      setSplitPct(pct);
    };
    const handleDragEnd = () => {
      isDragging.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    window.addEventListener('mousemove', handleDrag);
    window.addEventListener('mouseup', handleDragEnd);
    window.addEventListener('touchmove', handleDrag);
    window.addEventListener('touchend', handleDragEnd);
    return () => {
      window.removeEventListener('mousemove', handleDrag);
      window.removeEventListener('mouseup', handleDragEnd);
      window.removeEventListener('touchmove', handleDrag);
      window.removeEventListener('touchend', handleDragEnd);
    };
  }, []);

  const sendMessage = () => {
    if (!input.trim() || !connected) return;
    const msg = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: msg }]);
    wsRef.current.send(JSON.stringify({ message: msg }));
    setInput('');
    inputRef.current?.focus();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const togglePanel = (panel) => {
    if (panelMode === panel) {
      setPanelMode('both');
    } else {
      setPanelMode(panel);
    }
  };

  if (!token) {
    return <Login onLogin={(t) => setToken(t)} />;
  }

  const showPortfolio = panelMode === 'both' || panelMode === 'portfolio';
  const showChat = panelMode === 'both' || panelMode === 'chat';

  return (
    <div className="app-root">
      <ToastContainer />
      <TickerTape />

      {/* Desktop split layout */}
      <div className="split-layout desktop-layout" ref={layoutRef}>
        {/* Top — uEquity Portfolio Terminal */}
        {showPortfolio && (
          <div
            className="split-top"
            style={panelMode === 'both' ? { height: `calc(${splitPct}% - 14px)` } : { height: 'calc(100vh - 56px)' }}
          >
            <Portfolio
              refreshKey={refreshKey}
              onPortfolioChange={triggerRefresh}
              onLogout={handleLogout}
              theme={theme}
              onToggleTheme={toggleTheme}
            />
          </div>
        )}

        {/* Divider with collapse buttons */}
        <div
          className={`split-divider ${panelMode === 'both' ? 'draggable' : ''}`}
          onMouseDown={panelMode === 'both' ? handleDragStart : undefined}
          onTouchStart={panelMode === 'both' ? handleDragStart : undefined}
        >
          <div className="divider-controls">
            <button
              className={`divider-btn ${panelMode === 'portfolio' ? 'active' : ''}`}
              onClick={() => togglePanel('portfolio')}
              title={panelMode === 'portfolio' ? 'Show both panels' : 'Full screen portfolio'}
            >
              {panelMode === 'portfolio' ? '\u25D3' : '\u25B2'}
            </button>
            <span className="divider-grip">&hellip;</span>
            <button
              className={`divider-btn ${panelMode === 'chat' ? 'active' : ''}`}
              onClick={() => togglePanel('chat')}
              title={panelMode === 'chat' ? 'Show both panels' : 'Full screen chat'}
            >
              {panelMode === 'chat' ? '\u25D3' : '\u25BC'}
            </button>
          </div>
        </div>

        {/* Bottom — SAM Chat */}
        {showChat && (
          <div
            className="split-bottom"
            style={panelMode === 'both' ? { height: `calc(${100 - splitPct}% - 14px)` } : { height: 'calc(100vh - 56px)' }}
          >
            <div className="chat-header">
              <div className="chat-brand">SAM <span>Smart Analyst for Markets</span></div>
              <div className="chat-controls">
                <span className={`status-dot ${connected ? 'live' : 'off'}`}></span>
                <span className="status-text">{connected ? 'Live' : 'Offline'}</span>
                {messages.length > 0 && (
                  <button className="clear-btn" onClick={() => { setMessages([]); localStorage.removeItem(`sam_chat_${activeTab}`); }}>
                    Clear
                  </button>
                )}
              </div>
            </div>

            {/* Chat Tabs */}
            <div className="chat-tabs">
              {chatTabs.map(tab => (
                <div
                  key={tab.id}
                  className={`chat-tab ${activeTab === tab.id ? 'active' : ''}`}
                  onClick={() => switchTab(tab.id)}
                >
                  <span className="chat-tab-name">{tab.name}</span>
                  {chatTabs.length > 1 && (
                    <button className="chat-tab-close" onClick={(e) => closeTab(tab.id, e)}>&times;</button>
                  )}
                </div>
              ))}
              <button className="chat-tab-add" onClick={addTab} title="New chat tab">+</button>
            </div>

            <div className="chat-messages">
              {messages.length === 0 && (
                <div className="chat-welcome">
                  <span className="welcome-text">Ask SAM anything about the US stock market — prices, news, analysis, or manage your portfolio</span>
                  <div className="welcome-chips">
                    <button onClick={() => setInput("What's NVDA trading at?")}>NVDA Price</button>
                    <button onClick={() => setInput('News sentiment on TSLA')}>TSLA Sentiment</button>
                    <button onClick={() => setInput('Analyze AAPL technicals')}>Analyze AAPL</button>
                    <button onClick={() => setInput('Add 10 shares of AAPL at $180 to my portfolio')}>Add AAPL</button>
                    <button onClick={() => setInput('Show my portfolio')}>My Portfolio</button>
                  </div>
                </div>
              )}

              {messages.map((msg, i) => (
                <div key={i} className={`message ${msg.role}`}>
                  <div className="message-content">
                    {msg.role === 'assistant' ? (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    ) : (
                      msg.content
                    )}
                  </div>
                </div>
              ))}

              {isTyping && (
                <div className="message assistant">
                  <div className="typing">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="chat-input">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask SAM about prices, news, technicals, or manage your portfolio..."
                rows={1}
              />
              <button onClick={sendMessage} disabled={!connected || !input.trim()}>Send</button>
            </div>
          </div>
        )}
      </div>

      {/* Mobile layout — tab-based switching */}
      <div className="mobile-layout">
        <div className="mobile-content">
          {mobileTab === 'portfolio' && (
            <div className="mobile-panel">
              <Portfolio
                refreshKey={refreshKey}
                onPortfolioChange={triggerRefresh}
                onLogout={handleLogout}
                theme={theme}
                onToggleTheme={toggleTheme}
              />
            </div>
          )}
          {mobileTab === 'chat' && (
            <div className="mobile-panel mobile-chat-panel">
              <div className="chat-header">
                <div className="chat-brand">SAM <span>Smart Analyst for Markets</span></div>
                <div className="chat-controls">
                  <span className={`status-dot ${connected ? 'live' : 'off'}`}></span>
                  <span className="status-text">{connected ? 'Live' : 'Offline'}</span>
                  {messages.length > 0 && (
                    <button className="clear-btn" onClick={() => { setMessages([]); localStorage.removeItem(`sam_chat_${activeTab}`); }}>
                      Clear
                    </button>
                  )}
                </div>
              </div>

              <div className="chat-messages">
                {messages.length === 0 && (
                  <div className="chat-welcome">
                    <span className="welcome-text">Ask SAM anything about the stock market</span>
                    <div className="welcome-chips">
                      <button onClick={() => setInput("What's NVDA trading at?")}>NVDA Price</button>
                      <button onClick={() => setInput('Analyze AAPL')}>Analyze AAPL</button>
                      <button onClick={() => setInput('Show my portfolio')}>Portfolio</button>
                    </div>
                  </div>
                )}

                {messages.map((msg, i) => (
                  <div key={i} className={`message ${msg.role}`}>
                    <div className="message-content">
                      {msg.role === 'assistant' ? (
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      ) : (
                        msg.content
                      )}
                    </div>
                  </div>
                ))}

                {isTyping && (
                  <div className="message assistant">
                    <div className="typing">
                      <span></span><span></span><span></span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              <div className="chat-input">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask SAM..."
                  rows={1}
                />
                <button onClick={sendMessage} disabled={!connected || !input.trim()}>Send</button>
              </div>
            </div>
          )}
        </div>

        {/* Mobile bottom nav */}
        <div className="mobile-nav">
          <button
            className={`mobile-nav-btn ${mobileTab === 'portfolio' ? 'active' : ''}`}
            onClick={() => setMobileTab('portfolio')}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 3v18h18" /><path d="M7 16l4-8 4 4 4-6" />
            </svg>
            <span>Portfolio</span>
          </button>
          <button
            className={`mobile-nav-btn ${mobileTab === 'chat' ? 'active' : ''}`}
            onClick={() => setMobileTab('chat')}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <span>SAM Chat</span>
            {connected && <span className="mobile-nav-dot" />}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
