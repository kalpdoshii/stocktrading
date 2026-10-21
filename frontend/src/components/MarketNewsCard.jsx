/**
 * MarketNewsCard.jsx — Module 2: Market News
 * ==========================================
 * Matches Card 2 from the executive fintech design mockup.
 */

import React, { useState, useMemo } from 'react';
import { useApi } from '../hooks/useApi';
import { getMarketNews } from '../services/api';

const FILTER_PILLS = ['All', 'Stocks', 'Sectors', 'Economy', 'Global', 'Bookmarks'];

// Sample high-quality images for news cards
const NEWS_IMAGES = [
  'https://images.unsplash.com/photo-1578328819058-b69f3a3b0f6b?auto=format&fit=crop&w=400&q=80',
  'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=400&q=80',
  'https://images.unsplash.com/photo-1532375810709-75b1da00537c?auto=format&fit=crop&w=400&q=80',
  'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=400&q=80',
];

export default function MarketNewsCard({ onSelectTicker }) {
  const { data } = useApi(getMarketNews, 20);
  const [activeFilter, setActiveFilter] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [bookmarkedIds, setBookmarkedIds] = useState(new Set());

  const toggleBookmark = (id, e) => {
    e.stopPropagation();
    setBookmarkedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const rawItems = data?.items || [];

  // Filter items
  const filteredItems = useMemo(() => {
    let list = rawItems;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter((item) =>
        item.headline.toLowerCase().includes(q) ||
        (item.name && item.name.toLowerCase().includes(q)) ||
        (item.source && item.source.toLowerCase().includes(q))
      );
    }

    if (activeFilter === 'Bookmarks') {
      list = list.filter((_, idx) => bookmarkedIds.has(idx));
    } else if (activeFilter === 'Stocks') {
      list = list.filter((item) => item.ticker);
    } else if (activeFilter === 'Sectors') {
      list = list.filter((item) => item.sector);
    }

    return list;
  }, [rawItems, searchQuery, activeFilter, bookmarkedIds]);

  // Featured top 3 cards
  const featured = filteredItems.slice(0, 3);
  // Feed items below
  const feedItems = filteredItems.slice(3, 10);

  return (
    <div className="module-card module-card--news" id="news">
      {/* Background Earth Cosmic Watermark */}
      <div className="news-watermark-bg" />

      {/* Module Header */}
      <div className="module-card__header news-header">
        <div>
          <h2 className="module-card__title">Market News</h2>
          <p className="module-card__subtitle">Stay updated with the latest news moving the Indian markets</p>
        </div>

        {/* Search Bar */}
        <div className="news-search">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            placeholder="Search news, companies, trends..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Filter Pills */}
      <div className="news-pills">
        {FILTER_PILLS.map((pill) => (
          <button
            key={pill}
            className={`news-pill ${activeFilter === pill ? 'news-pill--active' : ''}`}
            onClick={() => setActiveFilter(pill)}
          >
            {pill}
          </button>
        ))}
      </div>

      {/* Top 3 Featured Cards */}
      <div className="news-featured-grid">
        {/* Card 1 */}
        {featured[0] && (
          <div className="featured-card featured-card--lead">
            <div className="featured-card__thumb-wrapper">
              <img
                src={NEWS_IMAGES[0]}
                alt="Coal industry"
                className="featured-card__img"
              />
              <span className="featured-badge featured-badge--alert">TOP STORY</span>
              <span className="featured-time">2h ago</span>
            </div>
            <div className="featured-card__content">
              <h4 className="featured-card__title">
                {featured[0].headline}
              </h4>
              <p className="featured-card__source">{featured[0].source || 'Business Standard'}</p>
              <p className="featured-card__snippet">
                Newsprint manufacturers have urged the government to ensure uninterrupted coal supply amid growing disruptions across key regions.
              </p>
            </div>
          </div>
        )}

        {/* Card 2 */}
        {featured[1] && (
          <div className="featured-card">
            <div className="featured-card__thumb-wrapper">
              <img
                src={NEWS_IMAGES[1]}
                alt="Oil Refinery"
                className="featured-card__img"
              />
              <span className="featured-time">3h ago</span>
            </div>
            <div className="featured-card__content">
              <span className="featured-tag">Reliance Industries</span>
              <h4 className="featured-card__title">
                {featured[1].headline}
              </h4>
              <p className="featured-card__source">{featured[1].source || 'Al Jazeera English'}</p>
            </div>
          </div>
        )}

        {/* Card 3 */}
        {featured[2] && (
          <div className="featured-card">
            <div className="featured-card__thumb-wrapper">
              <img
                src={NEWS_IMAGES[2]}
                alt="Trade summit"
                className="featured-card__img"
              />
              <span className="featured-time">4h ago</span>
            </div>
            <div className="featured-card__content">
              <span className="featured-tag featured-tag--accent">Oil and Gas</span>
              <h4 className="featured-card__title">
                {featured[2].headline}
              </h4>
              <p className="featured-card__source">{featured[2].source || 'ABC News'}</p>
            </div>
          </div>
        )}
      </div>

      {/* Latest Headlines Section */}
      <div className="news-feed">
        <div className="news-feed__header">
          <span className="yellow-dot" />
          <span>Latest Headlines</span>
        </div>

        <div className="news-feed__list">
          {(feedItems.length ? feedItems : rawItems.slice(0, 5)).map((item, idx) => {
            const timeStr = item.published_at
              ? new Date(item.published_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true }).toLowerCase()
              : `${12 - idx}:3${idx} pm`;
            const isBookmarked = bookmarkedIds.has(idx);

            return (
              <div key={idx} className="feed-row" onClick={() => item.ticker && onSelectTicker && onSelectTicker(item.ticker)}>
                <span className="feed-time">{timeStr}</span>
                <span className="feed-tag">{item.name || item.sector || 'Equities'}</span>
                <a
                  href={item.url || '#'}
                  target="_blank"
                  rel="noreferrer"
                  className="feed-headline"
                  onClick={(e) => { if (!item.url) e.preventDefault(); }}
                >
                  {item.headline}
                </a>
                <div className="feed-actions">
                  <div className="feed-thumb-preview">
                    <img src={NEWS_IMAGES[idx % NEWS_IMAGES.length]} alt="" />
                  </div>
                  <button
                    className={`bookmark-btn ${isBookmarked ? 'bookmark-btn--active' : ''}`}
                    onClick={(e) => toggleBookmark(idx, e)}
                    title={isBookmarked ? 'Remove bookmark' : 'Bookmark headline'}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill={isBookmarked ? '#38bdf8' : 'none'} stroke={isBookmarked ? '#38bdf8' : 'currentColor'} strokeWidth="2">
                      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                    </svg>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
