/**
 * BacktestResults.jsx — Backtesting Results Display
 * ====================================================
 * Shows the equity curve chart and performance stats table.
 */

import { useApi } from '../hooks/useApi';
import { getBacktest } from '../services/api';
import MetricsCard from './MetricsCard';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';

export default function BacktestResults({ ticker }) {
  const { data, loading, error } = useApi(getBacktest, ticker);

  if (loading) {
    return (
      <div className="glass-card">
        <div className="section-title">
          <span className="section-title__dot" />
          Backtest Results
        </div>
        <div className="skeleton skeleton--chart" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card">
        <div className="section-title">
          <span className="section-title__dot" />
          Backtest Results — {ticker}
        </div>
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
          No backtest data available. Run the backtest first:<br />
          <code style={{ color: 'var(--text-accent)' }}>
            python -m scripts.run_backtest --ticker {ticker}
          </code>
        </div>
      </div>
    );
  }

  const metrics = data?.metrics || {};
  const equityCurve = data?.equity_curve || [];
  const finalValue = metrics.final_value ?? equityCurve.at(-1)?.portfolio_value;
  const formatINR = (value) => (
    typeof value === 'number'
      ? new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 2,
      }).format(value)
      : '—'
  );

  // Sample equity curve for chart (show every Nth point for performance)
  const sampleRate = Math.max(1, Math.floor(equityCurve.length / 200));
  const chartData = equityCurve
    .filter((_, i) => i % sampleRate === 0 || i === equityCurve.length - 1)
    .map((e) => ({
      date: new Date(e.date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: '2-digit',
      }),
      value: e.portfolio_value,
    }));

  // Determine if profitable
  const isProfit = (metrics.total_return_pct || 0) > 0;

  return (
    <div className="glass-card fade-in">
      <div className="section-title">
        <span className="section-title__dot" />
        Backtest Results — {ticker}
        <span style={{
          marginLeft: 'auto',
          fontSize: '0.7rem',
          color: 'var(--text-muted)',
        }}>
          {data?.start_date} → {data?.end_date}
        </span>
      </div>

      {/* Metrics Row */}
      <div className="metrics-row" style={{ marginBottom: '1.5rem' }}>
        <MetricsCard
          label="Total Return"
          value={metrics.total_return_pct}
          suffix="%"
          colorize
        />
        <MetricsCard
          label="Win Rate"
          value={metrics.win_rate}
          suffix="%"
        />
        <MetricsCard
          label="Sharpe Ratio"
          value={metrics.sharpe_ratio}
          colorize
        />
        <MetricsCard
          label="Trades"
          value={metrics.total_trades}
        />
      </div>

      {/* Equity Curve Chart */}
      {chartData.length > 0 && (
        <div className="chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor={isProfit ? '#10b981' : '#ef4444'}
                    stopOpacity={0.2}
                  />
                  <stop
                    offset="95%"
                    stopColor={isProfit ? '#10b981' : '#ef4444'}
                    stopOpacity={0}
                  />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.04)"
                vertical={false}
              />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10 }}
                interval={Math.floor(chartData.length / 6)}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `INR ${(v / 1000).toFixed(1)}k`}
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-hover)',
                  borderRadius: '8px',
                }}
                formatter={(v) => [formatINR(v), 'Portfolio']}
                labelStyle={{ color: 'var(--text-secondary)' }}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={isProfit ? '#10b981' : '#ef4444'}
                strokeWidth={2}
                fill="url(#equityGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Win/Loss breakdown */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        gap: '2rem',
        marginTop: '1rem',
        fontSize: '0.8rem',
        color: 'var(--text-secondary)',
      }}>
        <span>
          ✅ Won: <strong style={{ color: 'var(--color-up)' }}>{metrics.winning_trades || 0}</strong>
        </span>
        <span>
          ❌ Lost: <strong style={{ color: 'var(--color-down)' }}>{metrics.losing_trades || 0}</strong>
        </span>
      </div>
      <MetricsCard
        label="Final Value"
        value={formatINR(finalValue)}
      />
      <MetricsCard
        label="Transaction Costs"
        value={formatINR(metrics.transaction_costs)}
      />
      <MetricsCard
        label="Nifty 50 Return"
        value={metrics.benchmark_return_pct}
        suffix="%"
      />
      <MetricsCard
        label="Excess Return"
        value={metrics.excess_return_pct}
        suffix="%"
        colorize
      />
    </div>
  );
}
