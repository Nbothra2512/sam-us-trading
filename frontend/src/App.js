// Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
// SAM (Smart Analyst for Markets) — Proprietary Software

import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import Portfolio from './Portfolio';
import Analysis from './Analysis';
import NewsFeed from './NewsFeed';
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
const TICKER_INDICES = [
  { symbol: 'SPY', label: 'S&P 500' },
  { symbol: 'QQQ', label: 'NASDAQ' },
  { symbol: 'DIA', label: 'DOW' },
];

function TickerTape() {
  const [tickers, setTickers] = useState([]);

  const fetchTickers = useCallback(() => {
    const token = getToken();
    if (!token) return;
    Promise.all(
      TICKER_INDICES.map(idx =>
        fetch(`${API_URL}/quote/${idx.symbol}`, { headers: { Authorization: `Bearer ${token}` } })
          .then(r => r.ok ? r.json() : null)
          .catch(() => null)
      )
    ).then(results => {
      const data = results.map((r, i) => {
        if (!r || r.error) return { ...TICKER_INDICES[i], price: null, change: 0, change_pct: 0 };
        return { ...TICKER_INDICES[i], price: r.price, change: r.change, change_pct: r.change_pct };
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

  // Triplicate for seamless scrolling (matches CSS translateX(-33.33%))
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

// ─── Chat Panel (shared between desktop and mobile) ─────────────
function ChatPanel({ messages, setMessages, input, setInput, isTyping, connected,
  chatTabs, activeTab, switchTab, addTab, closeTab, sendMessage, handleKeyDown,
  messagesEndRef, inputRef, showTabs = true }) {
  return (
    <>
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
      {showTabs && (
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
      )}

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-welcome">
            <span className="welcome-text">Ask SAM anything about the US stock market — prices, news, analysis, or manage your portfolio</span>
            <div className="welcome-chips">
              <button onClick={() => setInput("What's NVDA trading at?")}>NVDA Price</button>
              <button onClick={() => setInput('News sentiment on TSLA')}>TSLA Sentiment</button>
              <button onClick={() => setInput('Analyze AAPL technicals')}>Analyze AAPL</button>
              <button onClick={() => setInput('Scan AAPL for patterns and support/resistance')}>AAPL Patterns</button>
              <button onClick={() => setInput('Scan the market for oversold stocks and breakouts')}>Market Scan</button>
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
    </>
  );
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
  const [topView, setTopView] = useState('portfolio'); // 'portfolio', 'analysis', 'news'
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [mobileTab, setMobileTab] = useState('portfolio');
  const [splitPct, setSplitPct] = useState(50);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const isDragging = useRef(false);

  const wsRef = useRef(null);
  // Separate refs for desktop and mobile to avoid cross-contamination
  const desktopEndRef = useRef(null);
  const mobileEndRef = useRef(null);
  const desktopInputRef = useRef(null);
  const mobileInputRef = useRef(null);
  const layoutRef = useRef(null);
  const prevPortfolioRef = useRef(null);

  // Track which 5% alerts have already fired (by symbol, per session)
  const alertedSymbolsRef = useRef(new Set());
  // Track if earnings check has been done today
  const earningsCheckDateRef = useRef('');

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('sam_theme', theme);
  }, [theme]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyboard = (e) => {
      // Ignore when typing in input/textarea
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;

      const key = e.key.toLowerCase();

      if (key === '/') {
        e.preventDefault();
        const searchBar = document.querySelector('.search-bar');
        if (searchBar) searchBar.focus();
      } else if (key === 'p') {
        if (isMobile) setMobileTab('portfolio');
        else { setTopView('portfolio'); setPanelMode('both'); }
      } else if (key === 'a') {
        if (isMobile) setMobileTab('analysis');
        else { setTopView('analysis'); setPanelMode('both'); }
      } else if (key === 'n') {
        if (isMobile) setMobileTab('news');
        else { setTopView('news'); setPanelMode('both'); }
      } else if (key === 'c') {
        if (isMobile) setMobileTab('chat');
        else {
          setPanelMode('both');
          setTimeout(() => desktopInputRef.current?.focus(), 100);
        }
      } else if (key === 'escape') {
        setShowShortcuts(false);
        setPanelMode('both');
      } else if (key === '?') {
        setShowShortcuts(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyboard);
    return () => window.removeEventListener('keydown', handleKeyboard);
  }, [isMobile]);

  // Track mobile/desktop to avoid dual-mounting Portfolio
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 768px)');
    const handler = (e) => setIsMobile(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const handleLogout = useCallback(() => {
    localStorage.removeItem('sam_token');
    localStorage.removeItem('sam_user');
    setToken('');
    wsRef.current?.close();
  }, []);

  // Verify token on mount
  useEffect(() => {
    if (!token) return;
    fetch(`${API_URL}/auth/verify`, { headers: authHeaders() })
      .then(r => { if (!r.ok) handleLogout(); })
      .catch(() => handleLogout());
  }, [token, handleLogout]);

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
            // 5% move alert — only fire once per symbol per session
            if (Math.abs(h.day_chg_pct) >= 5 && !alertedSymbolsRef.current.has(h.symbol)) {
              alertedSymbolsRef.current.add(h.symbol);
              const dir = h.day_chg_pct >= 0 ? 'up' : 'down';
              showToast(`${h.symbol} is ${dir} ${Math.abs(h.day_chg_pct).toFixed(1)}% today!`, 'alert');
            }
          });
          // Earnings today check — only once per day
          if (earningsCheckDateRef.current !== today) {
            earningsCheckDateRef.current = today;
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
              if (snapshots.length === 0 || now - snapshots[snapshots.length - 1].t > 300000) {
                snapshots.push({ t: now, v: Math.round(totalVal * 100) / 100, c: Math.round(totalCost * 100) / 100 });
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
    let shouldReconnect = true;
    const connect = () => {
      const ws = new WebSocket(getWsUrl('/ws/chat'));
      ws.onopen = () => setConnected(true);
      ws.onclose = (e) => {
        setConnected(false);
        if (e.code === 4001) { handleLogout(); return; }
        if (shouldReconnect) setTimeout(connect, 3000);
      };
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'typing') {
            setIsTyping(data.status);
          } else if (data.type === 'message') {
            setMessages(prev => [...prev, { role: 'assistant', content: data.content }]);
            triggerRefresh();
          } else if (data.type === 'error') {
            setMessages(prev => [...prev, { role: 'error', content: data.content }]);
          }
        } catch {}
      };
      wsRef.current = ws;
    };
    connect();
    return () => {
      shouldReconnect = false;
      wsRef.current?.close();
    };
  }, [triggerRefresh, token, handleLogout]);

  // Persist messages for active tab
  useEffect(() => {
    saveTabMessages(activeTab, messages);
  }, [messages, activeTab]);

  // Save tabs
  useEffect(() => {
    saveChatTabs(chatTabs);
  }, [chatTabs]);

  // Scroll to bottom — scroll whichever ref is currently mounted
  useEffect(() => {
    desktopEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    mobileEndRef.current?.scrollIntoView({ behavior: 'smooth' });
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
    // Focus whichever input is visible
    desktopInputRef.current?.focus();
    mobileInputRef.current?.focus();
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
      {!isMobile && (
      <div className="split-layout desktop-layout" ref={layoutRef}>
        {/* Top — uEquity Portfolio / Analysis */}
        {showPortfolio && (
          <div
            className="split-top"
            style={panelMode === 'both' ? { height: `calc(${splitPct}% - 14px)` } : { height: 'calc(100vh - 56px)' }}
          >
            {/* View switcher tabs */}
            <div className="top-view-tabs">
              <button
                className={`top-view-tab ${topView === 'portfolio' ? 'active' : ''}`}
                onClick={() => setTopView('portfolio')}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 3v18h18" /><path d="M7 16l4-8 4 4 4-6" />
                </svg>
                Portfolio
              </button>
              <button
                className={`top-view-tab ${topView === 'analysis' ? 'active' : ''}`}
                onClick={() => setTopView('analysis')}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
                  <path d="M8 11h6" /><path d="M11 8v6" />
                </svg>
                Analysis
              </button>
              <button
                className={`top-view-tab ${topView === 'news' ? 'active' : ''}`}
                onClick={() => setTopView('news')}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 22h16a2 2 0 002-2V4a2 2 0 00-2-2H8a2 2 0 00-2 2v16a2 2 0 01-2 2zm0 0a2 2 0 01-2-2v-9c0-1.1.9-2 2-2h2" />
                  <path d="M18 14h-8" /><path d="M15 18h-5" /><path d="M10 6h8v4h-8z" />
                </svg>
                News
              </button>
              <div className="top-view-spacer" />
              <button
                className="shortcuts-btn"
                onClick={() => setShowShortcuts(prev => !prev)}
                title="Keyboard shortcuts (?)"
              >?</button>
            </div>
            {topView === 'portfolio' && (
              <Portfolio
                refreshKey={refreshKey}
                onPortfolioChange={triggerRefresh}
                onLogout={handleLogout}
                theme={theme}
                onToggleTheme={toggleTheme}
              />
            )}
            {topView === 'analysis' && <Analysis refreshKey={refreshKey} />}
            {topView === 'news' && <NewsFeed />}
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

        {/* Bottom — SAM Chat (Desktop) */}
        {showChat && (
          <div
            className="split-bottom"
            style={panelMode === 'both' ? { height: `calc(${100 - splitPct}% - 14px)` } : { height: 'calc(100vh - 56px)' }}
          >
            <ChatPanel
              messages={messages} setMessages={setMessages}
              input={input} setInput={setInput}
              isTyping={isTyping} connected={connected}
              chatTabs={chatTabs} activeTab={activeTab}
              switchTab={switchTab} addTab={addTab} closeTab={closeTab}
              sendMessage={sendMessage} handleKeyDown={handleKeyDown}
              messagesEndRef={desktopEndRef} inputRef={desktopInputRef}
              showTabs={true}
            />
          </div>
        )}
      </div>
      )}

      {/* Mobile layout — tab-based switching */}
      {isMobile && (
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
          {mobileTab === 'analysis' && (
            <div className="mobile-panel">
              <Analysis refreshKey={refreshKey} />
            </div>
          )}
          {mobileTab === 'news' && (
            <div className="mobile-panel">
              <NewsFeed />
            </div>
          )}
          {mobileTab === 'chat' && (
            <div className="mobile-panel mobile-chat-panel">
              <ChatPanel
                messages={messages} setMessages={setMessages}
                input={input} setInput={setInput}
                isTyping={isTyping} connected={connected}
                chatTabs={chatTabs} activeTab={activeTab}
                switchTab={switchTab} addTab={addTab} closeTab={closeTab}
                sendMessage={sendMessage} handleKeyDown={handleKeyDown}
                messagesEndRef={mobileEndRef} inputRef={mobileInputRef}
                showTabs={true}
              />
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
            className={`mobile-nav-btn ${mobileTab === 'analysis' ? 'active' : ''}`}
            onClick={() => setMobileTab('analysis')}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
              <path d="M8 11h6" /><path d="M11 8v6" />
            </svg>
            <span>Analysis</span>
          </button>
          <button
            className={`mobile-nav-btn ${mobileTab === 'news' ? 'active' : ''}`}
            onClick={() => setMobileTab('news')}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 22h16a2 2 0 002-2V4a2 2 0 00-2-2H8a2 2 0 00-2 2v16a2 2 0 01-2 2zm0 0a2 2 0 01-2-2v-9c0-1.1.9-2 2-2h2" />
            </svg>
            <span>News</span>
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
      )}

      {/* Keyboard Shortcuts Tooltip */}
      {showShortcuts && (
        <div className="shortcuts-overlay" onClick={() => setShowShortcuts(false)}>
          <div className="shortcuts-panel" onClick={e => e.stopPropagation()}>
            <div className="shortcuts-header">
              <h3>Keyboard Shortcuts</h3>
              <button className="shortcuts-close" onClick={() => setShowShortcuts(false)}>&times;</button>
            </div>
            <div className="shortcuts-list">
              <div className="shortcut-item"><kbd>/</kbd><span>Focus search</span></div>
              <div className="shortcut-item"><kbd>P</kbd><span>Portfolio view</span></div>
              <div className="shortcut-item"><kbd>A</kbd><span>Analysis view</span></div>
              <div className="shortcut-item"><kbd>N</kbd><span>News feed</span></div>
              <div className="shortcut-item"><kbd>C</kbd><span>Chat / Focus input</span></div>
              <div className="shortcut-item"><kbd>?</kbd><span>Toggle this help</span></div>
              <div className="shortcut-item"><kbd>Esc</kbd><span>Close modal / Reset panels</span></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
