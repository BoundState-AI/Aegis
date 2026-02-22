import { useEffect, useRef } from 'react';
import { apiGet } from '@/lib/apiClient';
import { healthSchema } from '@/lib/apiSchemas';

// Railway idles after ~5 minutes of inactivity, so ping every 4 minutes
const WARMUP_INTERVAL_MS = 4 * 60 * 1000;

/**
 * Hook to keep the Railway backend warm and prevent cold start delays.
 * Pings the health endpoint immediately on mount and every 4 minutes thereafter.
 */
export function useBackendWarmup() {
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    const ping = async () => {
      try {
        await apiGet('/health', healthSchema);
      } catch {
        // Silently ignore - warmup is best-effort
      }
    };

    // Ping immediately on mount
    ping();

    // Set up periodic keep-alive
    intervalRef.current = window.setInterval(ping, WARMUP_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);
}
