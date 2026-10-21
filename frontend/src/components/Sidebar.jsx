/**
 * Sidebar.jsx — Left Navigation Sidebar
 * =====================================
 * Recreates the executive dark fintech sidebar matching the design mockup.
 */

import React from 'react';

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: 'grid' },
  { id: 'news', label: 'Market News', icon: 'newspaper' },
  { id: 'analysis', label: 'Stock Analysis', icon: 'chart' },
  { id: 'sentiment', label: 'Sentiment', icon: 'gauge' },
  { id: 'backtest', label: 'Backtest', icon: 'analytics' },
];

function NavIcon({ type }) {
  if (type === 'grid') {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
      </svg>
    );
  }
  if (type === 'newspaper') {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2" />
        <path d="M18 14h-8" />
        <path d="M15 18h-5" />
        <path d="M10 6h8v4h-8V6Z" />
      </svg>
    );
  }
  if (type === 'chart') {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 3v18h18" />
        <path d="m19 9-5 5-4-4-3 3" />
      </svg>
    );
  }
  if (type === 'gauge') {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m12 14 4-4" />
        <path d="M3.34 19a10 10 0 1 1 17.32 0" />
      </svg>
    );
  }
  if (type === 'analytics') {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
      </svg>
    );
  }
  return null;
}

export default function Sidebar({ activeSection, onSelectSection }) {
  const handleClick = (id) => {
    onSelectSection(id);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <aside className="app-sidebar">
      {/* Brand Header */}
      <div className="app-sidebar__brand">
        <div className="app-sidebar__logo">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
            <polyline points="16 7 22 7 22 13" />
          </svg>
        </div>
        <span className="app-sidebar__brand-name">StockTrading</span>
      </div>

      {/* Nav Menu */}
      <nav className="app-sidebar__nav">
        {NAV_ITEMS.map((item) => {
          const isActive = activeSection === item.id;
          return (
            <button
              key={item.id}
              className={`app-sidebar__nav-item ${isActive ? 'app-sidebar__nav-item--active' : ''}`}
              onClick={() => handleClick(item.id)}
            >
              <span className="app-sidebar__nav-icon">
                <NavIcon type={item.icon} />
              </span>
              <span className="app-sidebar__nav-label">{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Sidebar Footer Quote */}
      <div className="app-sidebar__footer">
        <div className="app-sidebar__quote">
          <span>DISCIPLINE</span>
          <span>LEADS TO</span>
          <span>BETTER TRADES.</span>
        </div>
      </div>
    </aside>
  );
}
