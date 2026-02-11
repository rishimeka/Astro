'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, ApiClientError, ENDPOINTS } from '@/lib/api';
import type { Directive, DirectiveSummary, DirectiveCreate, DirectiveResponse } from '@/types/astro';

interface UseDirectivesResult {
  directives: DirectiveSummary[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

interface UseDirectiveResult {
  directive: Directive | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

interface UseDirectiveMutationsResult {
  createDirective: (data: DirectiveCreate) => Promise<DirectiveResponse>;
  updateDirective: (id: string, data: Partial<DirectiveCreate>) => Promise<DirectiveResponse>;
  deleteDirective: (id: string) => Promise<void>;
  isSubmitting: boolean;
  error: string | null;
}

export function useDirectives(): UseDirectivesResult {
  const [directives, setDirectives] = useState<DirectiveSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDirectives = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await api.get<DirectiveSummary[]>(ENDPOINTS.DIRECTIVES);
      setDirectives(data);
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to fetch directives';
      setError(message);
      setDirectives([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDirectives();
  }, [fetchDirectives]);

  return { directives, isLoading, error, refetch: fetchDirectives };
}

export function useDirective(id: string | null): UseDirectiveResult {
  const [directive, setDirective] = useState<Directive | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDirective = useCallback(async () => {
    if (!id) {
      setDirective(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await api.get<Directive>(ENDPOINTS.DIRECTIVE(id));
      setDirective(data);
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to fetch directive';
      setError(message);
      setDirective(null);
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchDirective();
  }, [fetchDirective]);

  return { directive, isLoading, error, refetch: fetchDirective };
}

export function useDirectiveMutations(): UseDirectiveMutationsResult {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createDirective = useCallback(async (data: DirectiveCreate): Promise<DirectiveResponse> => {
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await api.post<DirectiveResponse>(ENDPOINTS.DIRECTIVES, data);
      return response;
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to create directive';
      setError(message);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const updateDirective = useCallback(async (id: string, data: Partial<DirectiveCreate>): Promise<DirectiveResponse> => {
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await api.put<DirectiveResponse>(ENDPOINTS.DIRECTIVE(id), data);
      return response;
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to update directive';
      setError(message);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const deleteDirective = useCallback(async (id: string): Promise<void> => {
    setIsSubmitting(true);
    setError(null);

    try {
      await api.delete(ENDPOINTS.DIRECTIVE(id));
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to delete directive';
      setError(message);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  return { createDirective, updateDirective, deleteDirective, isSubmitting, error };
}

// Helper to get all unique tags from directives
export function getUniqueTags(directives: DirectiveSummary[]): string[] {
  const tagSet = new Set<string>();
  directives.forEach(d => d.tags.forEach(t => tagSet.add(t)));
  return Array.from(tagSet).sort();
}
