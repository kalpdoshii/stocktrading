import { useEffect, useState } from 'react';
import { useApi } from '../hooks/useApi';
import { getTickers } from '../services/api';

const STORAGE_KEY = 'indian-trading-watchlist';

export default function Watchlist({ selected, onSelect }) {
  const { data } = useApi(getTickers);
  const tickers = data?.tickers || [];
  const [watchlist, setWatchlist] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || ['RELIANCE.NS', 'TCS.NS', 'INFY.NS'];
    } catch {
      return ['RELIANCE.NS', 'TCS.NS', 'INFY.NS'];
    }
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(watchlist));
  }, [watchlist]);

  const toggleTicker = (ticker) => {
    setWatchlist((current) => (
      current.includes(ticker)
        ? current.filter((item) => item !== ticker)
        : [...current, ticker]
    ));
  };

  const getName = (ticker) => tickers.find((item) => item.ticker === ticker)?.name || ticker;

  return (
    <section className="watchlist">
      <div className="watchlist__heading">
        <span>Watchlist</span>
        <small>{watchlist.length} stocks</small>
      </div>
      <div className="watchlist__items">
        {watchlist.map((ticker) => (
          <button
            className={ticker === selected ? 'watchlist__item watchlist__item--active' : 'watchlist__item'}
            key={ticker}
            type="button"
            onClick={() => onSelect(ticker)}
            title={getName(ticker)}
          >
            <span>{ticker.replace('.NS', '')}</span>
            <span
              className="watchlist__remove"
              role="button"
              tabIndex={0}
              aria-label={`Remove ${ticker}`}
              onClick={(event) => {
                event.stopPropagation();
                toggleTicker(ticker);
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  event.stopPropagation();
                  toggleTicker(ticker);
                }
              }}
            >
              x
            </span>
          </button>
        ))}
      </div>
      <select
        className="watchlist__add"
        value=""
        onChange={(event) => {
          if (event.target.value) toggleTicker(event.target.value);
        }}
        aria-label="Add stock to watchlist"
      >
        <option value="">Add stock...</option>
        {tickers
          .filter((item) => !watchlist.includes(item.ticker) && item.status !== 'unavailable')
          .map((item) => (
            <option key={item.ticker} value={item.ticker}>{item.name}</option>
          ))}
      </select>
    </section>
  );
}
