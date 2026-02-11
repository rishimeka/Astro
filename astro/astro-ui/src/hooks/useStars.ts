'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, ApiClientError, ENDPOINTS } from '@/lib/api';
import type { Star, StarSummary, StarCreate } from '@/types/astro';
import type { StarResponse } from '@/lib/api/types';

interface UseStarsResult {
  stars: StarSummary[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

interface UseStarResult {
  star: Star | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

interface UseStarMutationsResult {
  createStar: (data: StarCreate) => Promise<StarResponse>;
  updateStar: (id: string, data: Partial<StarCreate>) => Promise<StarResponse>;
  deleteStar: (id: string) => Promise<void>;
  isSubmitting: boolean;
  error: string | null;
}

export function useStars(): UseStarsResult {
  const [stars, setStars] = useState<StarSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStars = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await api.get<StarSummary[]>(ENDPOINTS.STARS);
      setStars(data);
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to fetch stars';
      setError(message);
      setStars([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStars();
  }, [fetchStars]);

  return { stars, isLoading, error, refetch: fetchStars };
}

export function useStar(id: string | null): UseStarResult {
  const [star, setStar] = useState<Star | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStar = useCallback(async () => {
    if (!id) {
      setStar(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await api.get<Star>(ENDPOINTS.STAR(id));
      setStar(data);
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to fetch star';
      setError(message);
      setStar(null);
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchStar();
  }, [fetchStar]);

  return { star, isLoading, error, refetch: fetchStar };
}

export function useStarMutations(): UseStarMutationsResult {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createStar = useCallback(async (data: StarCreate): Promise<StarResponse> => {
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await api.post<StarResponse>(ENDPOINTS.STARS, data);
      return response;
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to create star';
      setError(message);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const updateStar = useCallback(async (id: string, data: Partial<StarCreate>): Promise<StarResponse> => {
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await api.put<StarResponse>(ENDPOINTS.STAR(id), data);
      return response;
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to update star';
      setError(message);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const deleteStar = useCallback(async (id: string): Promise<void> => {
    setIsSubmitting(true);
    setError(null);

    try {
      await api.delete(ENDPOINTS.STAR(id));
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to delete star';
      setError(message);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  return { createStar, updateStar, deleteStar, isSubmitting, error };
}
