"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Poll `fetcher` until `stopWhen` returns true or unmount.
 * Interval starts at `intervalMs` and backs off up to `maxIntervalMs` (SDS §15).
 */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  options: {
    enabled: boolean;
    intervalMs?: number;
    maxIntervalMs?: number;
    stopWhen?: (data: T) => boolean;
  },
) {
  const {
    enabled,
    intervalMs = 1500,
    maxIntervalMs = 5000,
    stopWhen,
  } = options;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const tickRef = useRef(intervalMs);
  const fetcherRef = useRef(fetcher);
  const stopRef = useRef(stopWhen);
  fetcherRef.current = fetcher;
  stopRef.current = stopWhen;

  useEffect(() => {
    if (!enabled) {
      setPolling(false);
      return;
    }
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    tickRef.current = intervalMs;
    setPolling(true);

    const tick = async () => {
      try {
        const next = await fetcherRef.current();
        if (cancelled) return;
        setData(next);
        setError(null);
        if (stopRef.current?.(next)) {
          setPolling(false);
          return;
        }
        tickRef.current = Math.min(
          tickRef.current + 500,
          maxIntervalMs,
        );
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Polling failed");
      }
      if (!cancelled) {
        timer = setTimeout(tick, tickRef.current);
      }
    };

    void tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      setPolling(false);
    };
  }, [enabled, intervalMs, maxIntervalMs]);

  return { data, error, polling };
}
