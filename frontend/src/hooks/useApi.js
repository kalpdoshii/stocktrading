/**
 * useApi.js — Custom Hook for API Calls
 * ========================================
 * Handles loading state, error state, and data fetching
 * in a reusable way across all components.
 *
 * Usage:
 *   const { data, loading, error, refetch } = useApi(getPriceData, 'AAPL');
 */

import { useState, useEffect, useCallback } from 'react';

export function useApi(fetchFn, ...args) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchFn(...args);
      setData(result);
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchFn, JSON.stringify(args)]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, loading, error, refetch: fetch };
}
