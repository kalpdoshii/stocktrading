import { useApi } from '../hooks/useApi';
import { getPredictionHistory } from '../services/api';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';

export default function PredictionHistory({ ticker }) {
  const { data, loading, error } = useApi(getPredictionHistory, ticker, 30);

  if (loading) {
    return (
      <div className="glass-card">
        <div className="section-title">
          <span className="section-title__dot" />
          Prediction Confidence
        </div>
        <div className="skeleton skeleton--chart" />
      </div>
    );
  }

  if (error || !data?.history?.length) {
    return null;
  }

  const chartData = data.history.map((item) => ({
    date: new Date(item.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }),
    confidence: Number((item.confidence * 100).toFixed(2)),
    signal: item.signal,
  }));

  return (
    <section className="glass-card fade-in">
      <div className="section-title">
        <span className="section-title__dot" />
        Prediction Confidence — {ticker}
        <span className="market-overview__as-of">{data.model_version}</span>
      </div>
      <div className="chart-container chart-container--compact">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis dataKey="date" axisLine={false} tickLine={false} />
            <YAxis domain={[0, 100]} tickFormatter={(value) => `${value}%`} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-hover)',
                borderRadius: '8px',
              }}
              formatter={(value, name, item) => [`${value}% (${item.payload.signal})`, 'Confidence']}
            />
            <Line type="monotone" dataKey="confidence" stroke="var(--text-accent)" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
