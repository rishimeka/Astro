'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, ApiClientError, ENDPOINTS } from '@/lib/api';
import type { Constellation, ConstellationSummary, ConstellationCreate, TemplateVariable, RunRequest } from '@/types/astro';
import type { ConstellationResponse } from '@/lib/api/types';

interface UseConstellationsResult {
  constellations: ConstellationSummary[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

interface UseConstellationResult {
  constellation: Constellation | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

interface UseConstellationVariablesResult {
  variables: TemplateVariable[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

interface UseConstellationMutationsResult {
  createConstellation: (data: ConstellationCreate) => Promise<ConstellationResponse>;
  updateConstellation: (id: string, data: Partial<ConstellationCreate>) => Promise<ConstellationResponse>;
  deleteConstellation: (id: string) => Promise<void>;
  runConstellation: (id: string, variables: RunRequest) => Promise<string>; // Returns SSE URL
  isSubmitting: boolean;
  error: string | null;
}

export function useConstellations(): UseConstellationsResult {
  const [constellations, setConstellations] = useState<ConstellationSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConstellations = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await api.get<ConstellationSummary[]>(ENDPOINTS.CONSTELLATIONS);
      setConstellations(data);
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to fetch constellations';
      setError(message);
      setConstellations([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConstellations();
  }, [fetchConstellations]);

  return { constellations, isLoading, error, refetch: fetchConstellations };
}

export function useConstellation(id: string | null): UseConstellationResult {
  const [constellation, setConstellation] = useState<Constellation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConstellation = useCallback(async () => {
    if (!id) {
      setConstellation(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await api.get<Constellation>(ENDPOINTS.CONSTELLATION(id));
      setConstellation(data);
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to fetch constellation';
      setError(message);
      setConstellation(null);
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchConstellation();
  }, [fetchConstellation]);

  return { constellation, isLoading, error, refetch: fetchConstellation };
}

export function useConstellationVariables(id: string | null): UseConstellationVariablesResult {
  const [variables, setVariables] = useState<TemplateVariable[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchVariables = useCallback(async () => {
    if (!id) {
      setVariables([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await api.get<TemplateVariable[]>(ENDPOINTS.CONSTELLATION_VARIABLES(id));
      setVariables(data);
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to fetch constellation variables';
      setError(message);
      setVariables([]);
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchVariables();
  }, [fetchVariables]);

  return { variables, isLoading, error, refetch: fetchVariables };
}

export function useConstellationMutations(): UseConstellationMutationsResult {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createConstellation = useCallback(async (data: ConstellationCreate): Promise<ConstellationResponse> => {
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await api.post<ConstellationResponse>(ENDPOINTS.CONSTELLATIONS, data);
      return response;
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to create constellation';
      setError(message);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const updateConstellation = useCallback(async (id: string, data: Partial<ConstellationCreate>): Promise<ConstellationResponse> => {
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await api.put<ConstellationResponse>(ENDPOINTS.CONSTELLATION(id), data);
      return response;
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to update constellation';
      setError(message);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const deleteConstellation = useCallback(async (id: string): Promise<void> => {
    setIsSubmitting(true);
    setError(null);

    try {
      await api.delete(ENDPOINTS.CONSTELLATION(id));
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to delete constellation';
      setError(message);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const runConstellation = useCallback(async (id: string, _variables: RunRequest): Promise<string> => {
    setIsSubmitting(true);
    setError(null);

    // The run endpoint returns an SSE stream, so we return the URL for the SSE connection
    // The actual POST will be handled by the SSE client
    try {
      // For SSE, we just return the URL - the caller will use EventSource
      return ENDPOINTS.CONSTELLATION_RUN(id);
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  return { createConstellation, updateConstellation, deleteConstellation, runConstellation, isSubmitting, error };
}

// Helper to get all unique tags from constellations
export function getUniqueTags(constellations: ConstellationSummary[]): string[] {
  const tagSet = new Set<string>();
  constellations.forEach(c => c.tags.forEach(t => tagSet.add(t)));
  return Array.from(tagSet).sort();
}
