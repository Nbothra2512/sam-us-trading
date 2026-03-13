// Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
// SAM (Smart Analyst for Markets) — Proprietary Software

import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import Portfolio from './Portfolio';
import './App.css';

const BACKEND = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const WS_URL = BACKEND.replace(/^http/, 'ws') + '/ws/chat';
const API_URL = BACKEND + '/api';

function App() {
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem('sam_chat');
    return saved ? JSON.parse(saved) : [];
  });
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [connected, setConnected] = useState(false);
  const [portfolioData, setPortfolioData] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Shared portfolio fetch — used by both terminal and chat
  const fetchPortfolio = useCallback(() => {
    fetch(`${API_URL}/portfolio`).then(r => r.json()).then(setPortfolioData).catch(() => {});
  }, []);

  // Trigger terminal refresh from outside
  const triggerRefresh = useCallback(() => {
    setRefreshKey(k => k + 1);
    fetchPortfolio();
  }, [fetchPortfolio]);

  useEffect(() => {
    fetchPortfolio();
    // REST polling is now fallback only — live prices come via WebSocket
    const interval = setInterval(fetchPortfolio, 30000);
    return () => clearInterval(interval);
  }, [fetchPortfolio]);

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
          // Refresh portfolio after every SAM response (might have added/removed holdings)
          triggerRefresh();
        } else if (data.type === 'error') {
          setMessages(prev => [...prev, { role: 'error', content: data.content }]);
        }
      };
      wsRef.current = ws;
    };
    connect();
    return () => wsRef.current?.close();
  }, [triggerRefresh]);

  useEffect(() => {
    localStorage.setItem('sam_chat', JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

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
    <div className="split-layout">
      {/* Top — uEquity Portfolio Terminal */}
      <div className="split-top">
        <Portfolio refreshKey={refreshKey} onPortfolioChange={triggerRefresh} />
      </div>

      <div className="split-divider"></div>

      {/* Bottom — SAM Chat */}
      <div className="split-bottom">
        <div className="chat-header">
          <div className="chat-brand">SAM <span>Smart Analyst for Markets</span></div>
          <div className="chat-controls">
            <span className={`status-dot ${connected ? 'live' : 'off'}`}></span>
            <span className="status-text">{connected ? 'Live' : 'Offline'}</span>
            {messages.length > 0 && (
              <button className="clear-btn" onClick={() => { setMessages([]); localStorage.removeItem('sam_chat'); }}>
                Clear
              </button>
            )}
          </div>
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
    </div>
  );
}

export default App;
