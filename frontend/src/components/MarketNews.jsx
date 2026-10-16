import { useApi } from '../hooks/useApi';
import { getMarketNews } from '../services/api';

function formatPublishedAt(value) {
  if (!value) return 'Date unavailable';
  return new Date(value).toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function MarketNews() {
  const { data, loading, error } = useApi(getMarketNews, 12);

  if (loading) {
    return <div className="glass-card skeleton skeleton--news" />;
  }

  if (error || !data?.items?.length) {
    return null;
  }

  return (
    <section className="market-news glass-card fade-in">
      <div className="section-title">
        <span className="section-title__dot" />
        Latest Indian Market News
        <span className="market-overview__as-of">{data.count} headlines</span>
      </div>

      <div className="market-news__list">
        {data.items.map((item) => (
          <article className="market-news__item" key={`${item.ticker}-${item.published_at}-${item.headline}`}>
            <div className="market-news__meta">
              <span>{item.name}</span>
              <span>{item.sector || 'Indian equities'}</span>
              <time>{formatPublishedAt(item.published_at)}</time>
            </div>
            {item.url ? (
              <a href={item.url} target="_blank" rel="noreferrer">
                {item.headline}
              </a>
            ) : (
              <p>{item.headline}</p>
            )}
            <small>{item.source || 'Unknown source'}</small>
          </article>
        ))}
      </div>
    </section>
  );
}
