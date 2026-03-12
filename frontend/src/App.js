import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import './App.css';

const WS_URL = 'ws://localhost:8000/ws/chat';
const API_URL = 'http://localhost:8000/api';

function App() {
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem('sam_chat');
    return saved ? JSON.parse(saved) : [];
  });
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [connected, setConnected] = useState(false);
  const [portfolio, setPortfolio] = useState(null);
  const [watchlist, setWatchlist] = useState([]);
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(WS_URL);
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, 3000);
      };
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'typing') {
          setIsTyping(data.status);
        } else if (data.type === 'message') {
          setMessages(prev => [...prev, { role: 'assistant', content: data.content }]);
          refreshSidebar();
        } else if (data.type === 'error') {
          setMessages(prev => [...prev, { role: 'error', content: data.content }]);
        }
      };
      wsRef.current = ws;
    };
    connect();
    return () => wsRef.current?.close();
  }, []);

  // Save chat to localStorage
  useEffect(() => {
    localStorage.setItem('sam_chat', JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const refreshSidebar = () => {
    fetch(`${API_URL}/portfolio`).then(r => r.json()).then(setPortfolio).catch(() => {});
    fetch(`${API_URL}/watchlist`).then(r => r.json()).then(setWatchlist).catch(() => {});
  };

  useEffect(() => {
    refreshSidebar();
    const interval = setInterval(refreshSidebar, 30000);
    return () => clearInterval(interval);
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

  return (
    <div className="app">
      {/* Sidebar */}
      <div className="sidebar">
        <h2>SAM</h2>
        <div className="sidebar-row">
          <div className="status-badge" data-connected={connected}>
            {connected ? 'Live' : 'Disconnected'}
          </div>
          {messages.length > 0 && (
            <button className="clear-btn" onClick={() => { setMessages([]); localStorage.removeItem('sam_chat'); }}>
              Clear Chat
            </button>
          )}
        </div>

        {/* Portfolio */}
        {portfolio && portfolio.holdings && portfolio.holdings.length > 0 && (
          <div className="card">
            <h3>Portfolio</h3>
            <div className="stat total">
              <span>Total Value</span>
              <span className="value">${portfolio.total_value.toLocaleString()}</span>
            </div>
            <div className="stat">
              <span>Total P&L</span>
              <span className={`value ${portfolio.total_pl >= 0 ? 'green' : 'red'}`}>
                {portfolio.total_pl >= 0 ? '+' : ''}${portfolio.total_pl.toLocaleString()} ({portfolio.total_pl_pct}%)
              </span>
            </div>
            <div className="divider"></div>
            {portfolio.holdings.map(h => (
              <div key={h.symbol} className="position">
                <div className="position-header">
                  <span className="symbol">{h.symbol}</span>
                  <span className={h.pl >= 0 ? 'green' : 'red'}>
                    {h.pl >= 0 ? '+' : ''}{h.pl_pct.toFixed(1)}%
                  </span>
                </div>
                <div className="position-detail">
                  {h.qty} @ ${h.avg_price} | Now ${h.current_price.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Watchlist */}
        {watchlist.length > 0 && (
          <div className="card">
            <h3>Watchlist</h3>
            {watchlist.map(w => (
              <div key={w.symbol} className="watchlist-item">
                <span className="symbol">{w.symbol}</span>
                <span className="value">${w.mid.toFixed(2)}</span>
              </div>
            ))}
          </div>
        )}

        {/* Quick commands */}
        <div className="quick-actions">
          <h3>Quick Commands</h3>
          {[
            'Price of NVDA',
            'TSLA news sentiment',
            'Analyze AAPL technicals',
            'Show my portfolio',
            'Add MSFT to watchlist',
          ].map(cmd => (
            <button key={cmd} onClick={() => { setInput(cmd); inputRef.current?.focus(); }}>
              {cmd}
            </button>
          ))}
        </div>
      </div>

      {/* Chat */}
      <div className="chat">
        <div className="messages">
          {messages.length === 0 && (
            <div className="welcome">
              <h1>SAM</h1>
              <p className="subtitle">Smart Analyst for Markets</p>
              <p>Live prices, news sentiment, technical analysis, and portfolio tracking for the US stock market.</p>
              <div className="examples">
                <button onClick={() => setInput("What's NVDA trading at?")}>NVDA Price</button>
                <button onClick={() => setInput('News sentiment on TSLA')}>TSLA Sentiment</button>
                <button onClick={() => setInput('Run technical analysis on AAPL')}>Analyze AAPL</button>
                <button onClick={() => setInput('Add 50 shares of MSFT at $420 to my portfolio')}>Track Portfolio</button>
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

        <div className="input-area">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about prices, news, or track your portfolio..."
            rows={1}
          />
          <button onClick={sendMessage} disabled={!connected || !input.trim()}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
