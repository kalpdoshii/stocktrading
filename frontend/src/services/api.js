

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

/**
 * Generic fetch wrapper with error handling.
 */
async function fetchApi(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, options);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `API error: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`API call failed: ${endpoint}`, error);
    throw error;
  }
}

/** Get list of available tickers */
export const getTickers = () => fetchApi('/tickers');

/** Get OHLCV price data with indicators for a ticker */
export const getPriceData = (ticker, limit = 365) =>
  fetchApi(`/price/${ticker}?limit=${limit}`);

/** Get latest prediction for a ticker */
export const getPrediction = (ticker) =>
  fetchApi(`/predict/${ticker}`);

/** Get sentiment data for a ticker */
export const getSentiment = (ticker, days = 30) =>
  fetchApi(`/sentiment/${ticker}?days=${days}`);

/** Get LLM explanation for a ticker */
export const getExplanation = (ticker) =>
  fetchApi(`/explain/${ticker}`);

/** Get backtest results for a ticker */
export const getBacktest = (ticker, model = 'sentiment_v1') =>
  fetchApi(`/backtest/${ticker}?model_version=${model}`);

/** Get model metrics comparison */
export const getMetricsComparison = () =>
  fetchApi('/metrics/compare');

/** Health check */
export const healthCheck = () => fetchApi('/health');

/** Get the Indian market overview and daily movers */
export const getMarketOverview = () => fetchApi('/market-overview');

/** Get the latest stored Indian market headlines */
export const getMarketNews = (limit = 12) => fetchApi(`/market-news?limit=${limit}`);

/** Get recent prediction confidence history for a ticker */
export const getPredictionHistory = (ticker, limit = 30) =>
  fetchApi(`/predict-history/${ticker}?limit=${limit}`);

/** Start and monitor the live data refresh */
export const startRefresh = () => fetchApi('/refresh', { method: 'POST' });
export const getRefreshStatus = () => fetchApi('/refresh/status');
