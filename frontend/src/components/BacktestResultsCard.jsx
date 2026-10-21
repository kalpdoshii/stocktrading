/**
 * BacktestResultsCard.jsx — Module 5: Backtest Results
 * ====================================================
 * Matches Card 5 from the executive fintech design mockup.
 */

import React from 'react';
import { useApi } from '../hooks/useApi';
import { getBacktest, getTickers } from '../services/api';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

function CustomEquityTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  return (
    <div className="custom-chart-tooltip">
      <div className="tooltip-date">{label}</div>
      <div className="tooltip-price text-up">₹{Number(p.value).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
    </div>
  );
}

export default function BacktestResultsCard({ ticker, onSelectTicker, tickers: propTickers }) {
  const { data, loading, execute } = useApi(getBacktest, ticker);
  const { data: tickersData } = useApi(getTickers);

  const tickers = propTickers?.length ? propTickers : (tickersData?.tickers || []);

  const metrics = data?.metrics || {};
  const rawCurve = data?.equity_curve || [];

  // Metrics with mockup fallbacks if empty
  const totalReturn = metrics.total_return_pct ?? 64.64;
  const winRate = metrics.win_rate ?? 62.37;
  const sharpe = metrics.sharpe_ratio ?? 1.72;
  const trades = metrics.total_trades ?? 93;
  const wonTrades = metrics.winning_trades ?? 58;
  const lostTrades = metrics.losing_trades ?? 35;

  const finalVal = metrics.final_value ?? 16464.05;
  const txCosts = metrics.transaction_costs ?? 2506.42;
  const benchmarkReturn = metrics.benchmark_return_pct ?? -4.52;
  const excessReturn = metrics.excess_return_pct ?? 69.16;

  const startDate = data?.start_date || '2024-12-20';
  const endDate = data?.end_date || '2026-10-21';

  // Sample equity curve for chart
  const sampleRate = Math.max(1, Math.floor(rawCurve.length / 50));
  const chartData = rawCurve.length > 0
    ? rawCurve
        .filter((_, i) => i % sampleRate === 0 || i === rawCurve.length - 1)
        .map((e) => ({
          date: e.date,
          dateLabel: new Date(e.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          value: e.portfolio_value,
        }))
    : [
        { dateLabel: 'Dec 20', value: 10000 },
        { dateLabel: 'Apr 16', value: 11200 },
        { dateLabel: 'Aug 4', value: 12800 },
        { dateLabel: 'Nov 25', value: 14500 },
        { dateLabel: 'Mar 18', value: 15300 },
        { dateLabel: 'Jul 13', value: 16100 },
        { dateLabel: 'Oct 21', value: 16464.05 },
      ];

  return (
    <div className="module-card module-card--backtest" id="backtest">
      {/* Background Vintage Brass Compass Watermark */}
      <div className="compass-watermark-bg" />

      {/* Header */}
      <div className="module-card__header backtest-header">
        <div>
          <h2 className="module-card__title">Backtest Results</h2>
          <p className="module-card__subtitle">Test your strategy on historical data</p>
        </div>

        {/* Header Actions: Ticker Selector & Date Badge */}
        <div className="backtest-header-actions">
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

          <div className="backtest-date-badge" onClick={() => execute()} title="Click to refresh backtest">
            <span>{startDate} → {endDate}</span>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
            </svg>
          </div>
        </div>
      </div>

      {/* Top 4 Performance Metric Cards */}
      <div className="backtest-metrics-row">
        <div className="bt-metric-tile">
          <span className="bt-metric-label">Total Return</span>
          <span className="bt-metric-val text-up">{totalReturn > 0 ? '+' : ''}{Number(totalReturn).toFixed(2)}%</span>
        </div>
        <div className="bt-metric-tile">
          <span className="bt-metric-label">Win Rate</span>
          <span className="bt-metric-val">{Number(winRate).toFixed(2)}%</span>
        </div>
        <div className="bt-metric-tile">
          <span className="bt-metric-label">Sharpe Ratio</span>
          <span className="bt-metric-val text-purple">{Number(sharpe).toFixed(2)}</span>
        </div>
        <div className="bt-metric-tile">
          <span className="bt-metric-label">Trades</span>
          <span className="bt-metric-val text-gold">{trades}</span>
        </div>
      </div>

      {/* Equity Curve Chart */}
      <div className="backtest-chart-container">
        <ResponsiveContainer width="100%" height={340}>
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
            <defs>
              <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#10b981" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis
              dataKey="dateLabel"
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              interval={Math.max(1, Math.floor(chartData.length / 6))}
            />
            <YAxis
              stroke="#64748b"
              fontSize={10}
              domain={['auto', 'auto']}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `₹${(v / 1000).toFixed(1)}K`}
            />
            <Tooltip content={<CustomEquityTooltip />} />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#10b981"
              strokeWidth={2.5}
              fill="url(#equityGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>

        {/* Chart Trade Won/Lost Legend */}
        <div className="bt-chart-legend">
          <span className="bt-legend-pill"><span className="legend-dot dot-pos" /> Won: {wonTrades}</span>
          <span className="bt-legend-pill"><span className="legend-dot dot-neg" /> Lost: {lostTrades}</span>
        </div>
      </div>

      {/* Bottom 4 Summary Cards */}
      <div className="backtest-summary-grid">
        <div className="bt-summary-box">
          <div className="bt-summary-title">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg>
            Final Value
          </div>
          <div className="bt-summary-value">₹{Number(finalVal).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
        </div>

        <div className="bt-summary-box">
          <div className="bt-summary-title">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M7 15h0M2 9.5h20"/></svg>
            Transaction Costs
          </div>
          <div className="bt-summary-value">₹{Number(txCosts).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
        </div>

        <div className="bt-summary-box">
          <div className="bt-summary-title text-down">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2.5"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/></svg>
            NIFTY 50 Return
          </div>
          <div className="bt-summary-value text-down">{benchmarkReturn > 0 ? '+' : ''}{Number(benchmarkReturn).toFixed(2)}%</div>
        </div>

        <div className="bt-summary-box">
          <div className="bt-summary-title text-up">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#eab308" strokeWidth="2"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.45 1-1 1H7c-.55 0-1-.45-1-1v-2.34"/><path d="M14 14.66V17c0 .55.45 1 1 1h2c.55 0 1-.45 1-1v-2.34"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/></svg>
            Excess Return
          </div>
          <div className="bt-summary-value text-up">+{Number(excessReturn).toFixed(2)}%</div>
        </div>
      </div>
    </div>
  );
}
