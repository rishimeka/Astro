'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, ApiClientError, ENDPOINTS } from '@/lib/api';
import type { Probe } from '@/types/astro';

interface UseProbesResult {
  probes: Probe[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

interface UseProbeResult {
  probe: Probe | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useProbes(): UseProbesResult {
  const [probes, setProbes] = useState<Probe[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProbes = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await api.get<Probe[]>(ENDPOINTS.PROBES);
      setProbes(data);
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to fetch probes';
      setError(message);
      setProbes([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProbes();
  }, [fetchProbes]);

  return { probes, isLoading, error, refetch: fetchProbes };
}

export function useProbe(name: string | null): UseProbeResult {
  const [probe, setProbe] = useState<Probe | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProbe = useCallback(async () => {
    if (!name) {
      setProbe(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await api.get<Probe>(ENDPOINTS.PROBE(name));
      setProbe(data);
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to fetch probe';
      setError(message);
      setProbe(null);
    } finally {
      setIsLoading(false);
    }
  }, [name]);

  useEffect(() => {
    fetchProbe();
  }, [fetchProbe]);

  return { probe, isLoading, error, refetch: fetchProbe };
}
