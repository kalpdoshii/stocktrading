import { useEffect, useState } from 'react';
import { getRefreshStatus, startRefresh } from '../services/api';

export default function RefreshControl() {
  const [status, setStatus] = useState('idle');
  const [startedAt, setStartedAt] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [message, setMessage] = useState('');

  const loadStatus = async () => {
    try {
      const result = await getRefreshStatus();
      setStatus(result.status);
      setStartedAt(result.started_at);
    } catch {
      setStatus('unavailable');
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  useEffect(() => {
    if (status !== 'running') return undefined;
    const timer = setInterval(() => {
      loadStatus();
      if (startedAt) {
        setElapsedSeconds(Math.max(0, Math.round((Date.now() - new Date(startedAt).getTime()) / 1000)));
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [status, startedAt]);

  const refresh = async () => {
    setMessage('');
    try {
      await startRefresh();
      setStatus('running');
      setElapsedSeconds(0);
    } catch (error) {
      setMessage(error.message || 'Refresh could not start');
    }
  };

  const isRunning = status === 'running';
  return (
    <div className="refresh-control">
      <button type="button" onClick={refresh} disabled={isRunning}>
        {isRunning ? 'Refreshing...' : 'Refresh data'}
      </button>
      <span className={`refresh-control__status refresh-control__status--${status}`}>
        {status === 'completed'
          ? 'Updated'
          : isRunning
            ? `Refreshing market data... ${elapsedSeconds}s`
            : 'Ready to refresh'}
      </span>
      {message && <span className="refresh-control__error">{message}</span>}
    </div>
  );
}
