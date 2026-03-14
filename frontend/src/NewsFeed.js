// Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
// SAM (Smart Analyst for Markets) — Proprietary Software

import React, { useState, useEffect, useCallback } from 'react';
import './NewsFeed.css';

const BACKEND = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const API_URL = BACKEND + '/api';

function getToken() { return localStorage.getItem('sam_token') || ''; }
function authHeaders() { return { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' }; }

function timeAgo(isoStr) {
  if (!isoStr) return '';
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function NewsFeed() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, portfolio, positive, negative

  const fetchNews = useCallback(() => {
    setLoading(true);
    fetch(`${API_URL}/news-feed`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : null)
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchNews();
    const interval = setInterval(fetchNews, 60000);
    return () => clearInterval(interval);
  }, [fetchNews]);

  const articles = data?.articles || [];
  const summary = data?.sentiment_summary || {};

  const filtered = articles.filter(a => {
    if (filter === 'portfolio') return a.portfolio_related;
    if (filter === 'positive') return a.sentiment === 'positive';
    if (filter === 'negative') return a.sentiment === 'negative';
    return true;
  });

  return (
    <div className="news-panel">
      <div className="news-header">
        <div className="news-title-row">
          <h2>News Feed</h2>
          <span className={`news-overall ${summary.overall || 'neutral'}`}>
            {(summary.overall || 'neutral').toUpperCase()}
          </span>
        </div>
        <div className="news-sentiment-bar">
          <span className="news-sent-item pos">{summary.positive || 0} Positive</span>
          <span className="news-sent-item neg">{summary.negative || 0} Negative</span>
          <span className="news-sent-item neu">{summary.neutral || 0} Neutral</span>
          <button className="news-refresh" onClick={fetchNews} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="news-filters">
        {['all', 'portfolio', 'positive', 'negative'].map(f => (
          <button
            key={f}
            className={`news-filter ${filter === f ? 'active' : ''}`}
            onClick={() => setFilter(f)}
          >
            {f === 'all' ? 'All' : f === 'portfolio' ? 'Portfolio' : f === 'positive' ? 'Bullish' : 'Bearish'}
            {f === 'all' && ` (${articles.length})`}
            {f === 'portfolio' && ` (${articles.filter(a => a.portfolio_related).length})`}
            {f === 'positive' && ` (${articles.filter(a => a.sentiment === 'positive').length})`}
            {f === 'negative' && ` (${articles.filter(a => a.sentiment === 'negative').length})`}
          </button>
        ))}
      </div>

      {/* News list */}
      <div className="news-list">
        {loading && !data && (
          <div className="news-loading">Loading news feed...</div>
        )}
        {filtered.length === 0 && !loading && (
          <div className="news-empty">No news articles found</div>
        )}
        {filtered.map((article, i) => (
          <a
            key={i}
            className={`news-item news-${article.sentiment}`}
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            <div className="news-item-left">
              <span className={`news-dot ${article.sentiment}`} />
            </div>
            <div className="news-item-body">
              <div className="news-headline">{article.headline}</div>
              <div className="news-meta">
                <span className="news-source">{article.source}</span>
                <span className="news-time">{timeAgo(article.datetime)}</span>
                {article.symbol && (
                  <span className={`news-ticker ${article.portfolio_related ? 'news-ticker-portfolio' : ''}`}>
                    {article.symbol}
                  </span>
                )}
                {article.portfolio_related && <span className="news-portfolio-badge">PORTFOLIO</span>}
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

export default NewsFeed;
