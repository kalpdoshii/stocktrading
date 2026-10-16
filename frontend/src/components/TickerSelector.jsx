/**
 * TickerSelector.jsx — Stock Ticker Dropdown
 * =============================================
 * Dropdown to select which stock to view.
 * Fetches available tickers from the API.
 */

import { useApi } from '../hooks/useApi';
import { getTickers } from '../services/api';

export default function TickerSelector({ selected, onSelect }) {
  const { data, loading } = useApi(getTickers);

  const tickers = data?.tickers || [];

  return (
    <div className="ticker-selector">
      <select
        className="ticker-selector__select"
        value={selected}
        onChange={(e) => onSelect(e.target.value)}
        disabled={loading}
        id="ticker-select"
      >
        {loading ? (
          <option>Loading...</option>
        ) : tickers.length > 0 ? (
          tickers.map((t) => (
            <option key={t.ticker} value={t.ticker} disabled={t.status === 'unavailable'}>
              {t.name || t.ticker} ({t.ticker}) {t.data_points > 0 ? `(${t.data_points} days)` : '(no data)'}
            </option>
          ))
        ) : (
          /* Fallback if API is not running */
          ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS'].map((t) => (
            <option key={t} value={t}>{t}</option>
          ))
        )}
      </select>
    </div>
  );
}
