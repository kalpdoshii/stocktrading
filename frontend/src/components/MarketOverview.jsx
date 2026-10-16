import { useApi } from '../hooks/useApi';
import { getMarketOverview } from '../services/api';

function Change({ value }) {
  const positive = value >= 0;
  return (
    <span className={positive ? 'market-overview__change market-overview__change--up' : 'market-overview__change market-overview__change--down'}>
      {positive ? '+' : ''}{value.toFixed(2)}%
    </span>
  );
}

function Movers({ title, stocks }) {
  return (
    <div className="market-overview__list">
      <h3>{title}</h3>
      {stocks?.map((stock) => (
        <div className="market-overview__row" key={stock.ticker}>
          <div>
            <strong>{stock.name}</strong>
            <span>{stock.ticker}</span>
          </div>
          <Change value={stock.change_pct} />
        </div>
      ))}
    </div>
  );
}

function SectorPerformance({ sectors }) {
  return (
    <div className="market-overview__list">
      <h3>Sector Performance</h3>
      {sectors?.map((sector) => (
        <div className="market-overview__row" key={sector.sector}>
          <div>
            <strong>{sector.sector}</strong>
            <span>{sector.stocks} stocks</span>
          </div>
          <Change value={sector.change_pct} />
        </div>
      ))}
    </div>
  );
}

export default function MarketOverview() {
  const { data, loading, error } = useApi(getMarketOverview);

  if (loading) {
    return <div className="glass-card skeleton skeleton--overview" />;
  }

  if (error || !data) {
    return null;
  }

  const nifty = data.nifty50;
  return (
    <section className="market-overview glass-card fade-in">
      <div className="section-title">
        <span className="section-title__dot" />
        Indian Market Overview
        <span className="market-overview__as-of">Updated {data.as_of}</span>
      </div>

      <div className="market-overview__summary">
        <div className="market-overview__index">
          <span>NIFTY 50</span>
          <strong>{nifty ? nifty.value.toLocaleString('en-IN') : 'Unavailable'}</strong>
          {nifty && <Change value={nifty.change_pct} />}
        </div>
        <div className="market-overview__coverage">
          <span>PRICE COVERAGE</span>
          <strong>{data.coverage.available}/{data.coverage.configured}</strong>
          <small>stocks available</small>
        </div>
      </div>

      <div className="market-overview__movers">
        <Movers title="Top Gainers" stocks={data.top_gainers} />
        <Movers title="Top Losers" stocks={data.top_losers} />
        <SectorPerformance sectors={data.sector_performance} />
      </div>
    </section>
  );
}
