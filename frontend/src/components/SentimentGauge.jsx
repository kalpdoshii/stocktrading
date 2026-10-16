/**
 * SentimentGauge.jsx — Visual Sentiment Indicator
 * ==================================================
 * Shows a gradient gauge bar with a sliding marker,
 * plus the numeric score and interpretation.
 */

import { useApi } from '../hooks/useApi';
import { getSentiment } from '../services/api';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts';

export default function SentimentGauge({ ticker }) {
  const { data, loading } = useApi(getSentiment, ticker);

  if (loading) {
    return (
      <div className="glass-card">
        <div className="section-title">
          <span className="section-title__dot" />
          Sentiment Analysis
        </div>
        <div className="skeleton skeleton--chart" style={{ height: '200px' }} />
      </div>
    );
  }

  const latest = data?.latest;
  const history = data?.history || [];
  const score = latest?.compound_score ?? 0;
  const interpretation = latest?.interpretation || 'No data';

  // Position of marker on gauge (0-100% based on -1 to +1 score)
  const markerPosition = ((score + 1) / 2) * 100;

  // Color based on score
  const scoreColor =
    score > 0.1 ? 'var(--color-up)' :
    score < -0.1 ? 'var(--color-down)' :
    'var(--color-warning)';

  // Prepare history chart data (last 14 days)
  const chartData = history.slice(-14).map((h) => ({
    date: new Date(h.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    score: h.compound_score,
  }));

  return (
    <div className="glass-card">
      <div className="section-title">
        <span className="section-title__dot" />
        Sentiment Analysis — {ticker}
      </div>

      <div className="sentiment-gauge fade-in">
        {/* Numeric Score */}
        <div className="sentiment-gauge__score" style={{ color: scoreColor }}>
          {score.toFixed(3)}
        </div>
        <div className="sentiment-gauge__interpretation">
          {interpretation}
        </div>

        {/* Gradient Gauge Bar */}
        <div className="sentiment-gauge__bar">
          <div
            className="sentiment-gauge__marker"
            style={{ left: `${Math.max(2, Math.min(98, markerPosition))}%` }}
          />
        </div>
        <div className="sentiment-gauge__labels">
          <span>Bearish</span>
          <span>Neutral</span>
          <span>Bullish</span>
        </div>
      </div>

      {/* History Mini Chart */}
      {chartData.length > 0 && (
        <div style={{ marginTop: '1.5rem', height: '140px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.04)"
                vertical={false}
              />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={[-1, 1]}
                tick={{ fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-hover)',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
                labelStyle={{ color: 'var(--text-secondary)' }}
              />
              <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, idx) => (
                  <Cell
                    key={idx}
                    fill={
                      entry.score > 0.1 ? '#10b981' :
                      entry.score < -0.1 ? '#ef4444' :
                      '#f59e0b'
                    }
                    fillOpacity={0.7}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {latest?.sample_count && (
        <div style={{
          textAlign: 'center',
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
          marginTop: '0.75rem',
        }}>
          Based on {latest.sample_count} analyzed texts
        </div>
      )}
    </div>
  );
}
