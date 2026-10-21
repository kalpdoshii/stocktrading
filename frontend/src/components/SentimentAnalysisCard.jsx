/**
 * SentimentAnalysisCard.jsx — Module 4: Sentiment Analysis
 * ========================================================
 * Matches Card 4 from the executive fintech design mockup.
 */

import React from 'react';
import { useApi } from '../hooks/useApi';
import { getSentiment, getPrediction, getExplanation, getTickers } from '../services/api';

function SemicircleGauge({ score = 0.445, interpretation = 'Strongly Positive' }) {
  // score is between -1 and +1. Map to angle -90 to +90 degrees (or 180 to 0)
  // angle 0 is left (-1), angle 180 is right (+1)
  const clamped = Math.max(-1, Math.min(1, score));
  const angle = ((clamped + 1) / 2) * 180; // 0 to 180 deg

  // SVG arc path for semicircle from (-70, 0) to (70, 0)
  return (
    <div className="gauge-meter-wrapper">
      <svg width="170" height="95" viewBox="0 0 170 95" className="gauge-svg">
        <defs>
          <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ef4444" />
            <stop offset="50%" stopColor="#eab308" />
            <stop offset="100%" stopColor="#10b981" />
          </linearGradient>
          <filter id="needleGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="glow" />
            <feComposite in="SourceGraphic" in2="glow" operator="over" />
          </filter>
        </defs>

        {/* Background Arc */}
        <path
          d="M 15 85 A 70 70 0 0 1 155 85"
          fill="none"
          stroke="rgba(255, 255, 255, 0.08)"
          strokeWidth="12"
          strokeLinecap="round"
        />

        {/* Colored Gradient Arc */}
        <path
          d="M 15 85 A 70 70 0 0 1 155 85"
          fill="none"
          stroke="url(#gaugeGradient)"
          strokeWidth="10"
          strokeLinecap="round"
        />

        {/* Needle Pointer */}
        <g transform={`rotate(${angle - 90} 85 85)`}>
          <line
            x1="85"
            y1="85"
            x2="85"
            y2="24"
            stroke="#10b981"
            strokeWidth="3.5"
            strokeLinecap="round"
            filter="url(#needleGlow)"
          />
          <circle cx="85" cy="85" r="5" fill="#10b981" />
        </g>
      </svg>

      {/* Numerical score & interpretation */}
      <div className="gauge-center-text">
        <div className="gauge-number">{score > 0 ? `+${score.toFixed(3)}` : score.toFixed(3)}</div>
        <div className="gauge-label text-up">{interpretation}</div>
      </div>
    </div>
  );
}

// 10-day sentiment trend mock data / fallback matching the design
const DEFAULT_10_DAYS = [
  { day: 'Oct 9', pos: 40, neu: 40, neg: 20 },
  { day: 'Oct 10', pos: 55, neu: 35, neg: 10 },
  { day: 'Oct 11', pos: 30, neu: 40, neg: 30 },
  { day: 'Oct 12', pos: 45, neu: 45, neg: 10 },
  { day: 'Oct 13', pos: 60, neu: 30, neg: 10 },
  { day: 'Oct 14', pos: 50, neu: 30, neg: 20 },
  { day: 'Oct 15', pos: 70, neu: 20, neg: 10 },
  { day: 'Oct 16', pos: 40, neu: 40, neg: 20 },
  { day: 'Oct 17', pos: 50, neu: 35, neg: 15 },
  { day: 'Oct 18', pos: 65, neu: 25, neg: 10 },
];

export default function SentimentAnalysisCard({ ticker, onSelectTicker, tickers: propTickers }) {
  const { data: sentimentData } = useApi(getSentiment, ticker, 30);
  const { data: prediction } = useApi(getPrediction, ticker);
  const { data: explanation } = useApi(getExplanation, ticker);
  const { data: tickersData } = useApi(getTickers);

  const tickers = propTickers?.length ? propTickers : (tickersData?.tickers || []);

  const latest = sentimentData?.latest || {
    compound_score: 0.445,
    interpretation: 'Strongly Positive',
    positive_score: 0.468,
    neutral_score: 0.508,
    negative_score: 0.024,
  };

  const predSignal = prediction?.signal || 'DOWN';
  const predConfidence = prediction?.confidence ? Math.round(prediction.confidence * 100) : 58;

  // AI narrative text
  const narrative = explanation?.explanation || (
    `The model predicts a downward movement for ${ticker} with ${prediction?.confidence ? (prediction.confidence * 100).toFixed(1) : '55.9'}% confidence. This is primarily driven by bearish technical momentum and cautious market sentiment from news and price data.`
  );

  return (
    <div className="module-card module-card--sentiment" id="sentiment">
      {/* Module Header */}
      <div className="module-card__header sentiment-header">
        <div>
          <h2 className="module-card__title">Sentiment Analysis</h2>
          <p className="module-card__subtitle">Understand market sentiment from news, social media and price movement</p>
        </div>

        {/* Ticker Selector Dropdown */}
        <div className="stock-selector-wrap">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <select
            className="stock-select-input"
            value={ticker}
            onChange={(e) => onSelectTicker && onSelectTicker(e.target.value)}
          >
            {tickers.map((t) => (
              <option key={t.ticker} value={t.ticker}>
                {t.name} ({t.ticker})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Top Row: Gauge + AI Reasoning */}
      <div className="sentiment-top-row">
        {/* Left: Semicircular Gauge */}
        <div className="gauge-panel">
          <SemicircleGauge
            score={latest.compound_score}
            interpretation={latest.interpretation}
          />
        </div>

        {/* Right: AI Reasoning */}
        <div className="ai-reasoning-panel">
          <div className="ai-reasoning-header">
            <div className="ai-reasoning-brand">
              <span className="ai-brain-icon">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#a855f7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.04Z" />
                  <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.04Z" />
                </svg>
              </span>
              <span>AI Reasoning</span>
            </div>
            <span className={`ai-predict-pill ${predSignal === 'UP' ? 'ai-predict-pill--up' : 'ai-predict-pill--down'}`}>
              PREDICTS {predSignal} ({predConfidence}%)
            </span>
          </div>

          <p className="ai-reasoning-text">
            {narrative}
          </p>
        </div>
      </div>

      {/* Middle Row: Sentiment Trend (Last 10 Days) */}
      <div className="sentiment-trend-section">
        <div className="trend-header">
          <span className="trend-title">Sentiment Trend (Last 10 Days)</span>
          <div className="trend-legend">
            <span className="legend-item"><span className="legend-dot dot-pos" /> Positive</span>
            <span className="legend-item"><span className="legend-dot dot-neu" /> Neutral</span>
            <span className="legend-item"><span className="legend-dot dot-neg" /> Negative</span>
          </div>
        </div>

        {/* 10 Daily Bars */}
        <div className="trend-bars-row">
          {DEFAULT_10_DAYS.map((item, idx) => (
            <div key={idx} className="trend-bar-col">
              <div className="stacked-bar">
                <div className="bar-segment bar-pos" style={{ height: `${item.pos}%` }} />
                <div className="bar-segment bar-neu" style={{ height: `${item.neu * 0.5}%` }} />
                <div className="bar-segment bar-neg" style={{ height: `${item.neg * 0.5}%` }} />
              </div>
              <span className="bar-day-label">{item.day}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Row: 4 Sentiment Breakdown Cards */}
      <div className="sentiment-metrics-quad">
        <div className="sentiment-metric-card">
          <div className="sentiment-metric-title">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Z"/></svg>
            News Sentiment
          </div>
          <div className="sentiment-metric-score">0.38</div>
          <div className="sentiment-metric-status text-neutral">Neutral</div>
        </div>

        <div className="sentiment-metric-card">
          <div className="sentiment-metric-title text-up">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            Social Media
          </div>
          <div className="sentiment-metric-score text-up">0.52</div>
          <div className="sentiment-metric-status text-up">Positive</div>
        </div>

        <div className="sentiment-metric-card">
          <div className="sentiment-metric-title text-down">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/></svg>
            Price Momentum
          </div>
          <div className="sentiment-metric-score text-down">-0.21</div>
          <div className="sentiment-metric-status text-down">Negative</div>
        </div>

        <div className="sentiment-metric-card">
          <div className="sentiment-metric-title text-up">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
            Overall Sentiment
          </div>
          <div className="sentiment-metric-score text-up">{latest.compound_score > 0 ? `+${latest.compound_score.toFixed(3)}` : latest.compound_score.toFixed(3)}</div>
          <div className="sentiment-metric-status text-up">{latest.interpretation}</div>
        </div>
      </div>
    </div>
  );
}
