/**
 * PriceChart.jsx — Price Chart with Signal Overlay
 * ===================================================
 * Recharts line chart showing closing price with UP/DOWN
 * prediction markers overlaid.
 */

import { useApi } from '../hooks/useApi';
import { getPriceData, getPrediction } from '../services/api';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceDot,
} from 'recharts';

/* Custom tooltip with glass styling */
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="custom-tooltip">
      <div className="custom-tooltip__label">{label}</div>
      {payload.map((p, i) => (
        <div key={i} className="custom-tooltip__value" style={{ color: p.color }}>
          {p.name}: ${Number(p.value).toFixed(2)}
        </div>
      ))}
    </div>
  );
}

export default function PriceChart({ ticker }) {
  const { data: priceData, loading: priceLoading } = useApi(getPriceData, ticker);
  const { data: prediction } = useApi(getPrediction, ticker);

  if (priceLoading) {
    return (
      <div className="glass-card">
        <div className="section-title">
          <span className="section-title__dot" />
          Price Chart
        </div>
        <div className="skeleton skeleton--chart" />
      </div>
    );
  }

  const chartData = priceData?.data?.slice(-120) || []; // last 120 days

  // Format dates for display
  const formattedData = chartData.map((d) => ({
    ...d,
    dateLabel: new Date(d.date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    }),
  }));

  // Find the prediction point (last data point)
  const predSignal = prediction?.signal;
  const predConfidence = prediction?.confidence;

  return (
    <div className="glass-card">
      <div className="section-title" style={{ marginBottom: '0.5rem' }}>
        <span className="section-title__dot" />
        Price Chart — {ticker}
        {predSignal && (
          <span
            className={`signal-badge signal-badge--${predSignal.toLowerCase()}`}
            style={{ marginLeft: 'auto' }}
          >
            {predSignal === 'UP' ? '▲' : '▼'} {predSignal}
            {predConfidence && ` ${(predConfidence * 100).toFixed(0)}%`}
          </span>
        )}
      </div>

      <div className="chart-container chart-container--tall">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={formattedData}>
            <defs>
              <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.04)"
              vertical={false}
            />
            <XAxis
              dataKey="dateLabel"
              tick={{ fontSize: 11 }}
              interval={Math.floor(formattedData.length / 8)}
              axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              tickLine={false}
            />
            <YAxis
              domain={['auto', 'auto']}
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `$${v.toFixed(0)}`}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Price area fill */}
            <Area
              type="monotone"
              dataKey="close"
              fill="url(#priceGradient)"
              stroke="none"
            />

            {/* Price line */}
            <Line
              type="monotone"
              dataKey="close"
              stroke="#06b6d4"
              strokeWidth={2}
              dot={false}
              name="Close"
            />

            {/* SMA 20 */}
            <Line
              type="monotone"
              dataKey="sma_20"
              stroke="#8b5cf6"
              strokeWidth={1}
              strokeDasharray="4 4"
              dot={false}
              name="SMA 20"
            />

            {/* Signal marker on the last point */}
            {predSignal && formattedData.length > 0 && (
              <ReferenceDot
                x={formattedData[formattedData.length - 1].dateLabel}
                y={formattedData[formattedData.length - 1].close}
                r={8}
                fill={predSignal === 'UP' ? '#10b981' : '#ef4444'}
                stroke="white"
                strokeWidth={2}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
