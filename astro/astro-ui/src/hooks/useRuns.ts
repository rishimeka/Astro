'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, ApiClientError, ENDPOINTS } from '@/lib/api';
import type { Run, RunSummary, NodeOutput, ConfirmRequest, ConfirmResponse } from '@/types/astro';

interface UseRunsResult {
  runs: RunSummary[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

interface UseRunResult {
  run: Run | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

interface UseRunNodeResult {
  nodeOutput: NodeOutput | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

interface UseRunMutationsResult {
  confirmRun: (runId: string, request: ConfirmRequest) => Promise<ConfirmResponse>;
  isSubmitting: boolean;
  error: string | null;
}

export function useRuns(constellationId?: string): UseRunsResult {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const url = constellationId
        ? `${ENDPOINTS.RUNS}?constellation_id=${constellationId}`
        : ENDPOINTS.RUNS;
      const data = await api.get<RunSummary[]>(url);
      setRuns(data);
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to fetch runs';
      setError(message);
      setRuns([]);
    } finally {
      setIsLoading(false);
    }
  }, [constellationId]);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  return { runs, isLoading, error, refetch: fetchRuns };
}

export function useRun(id: string | null): UseRunResult {
  const [run, setRun] = useState<Run | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRun = useCallback(async () => {
    if (!id) {
      setRun(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await api.get<Run>(ENDPOINTS.RUN(id));
      setRun(data);
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to fetch run';
      setError(message);
      setRun(null);
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchRun();
  }, [fetchRun]);

  return { run, isLoading, error, refetch: fetchRun };
}

export function useRunNode(runId: string | null, nodeId: string | null): UseRunNodeResult {
  const [nodeOutput, setNodeOutput] = useState<NodeOutput | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNodeOutput = useCallback(async () => {
    if (!runId || !nodeId) {
      setNodeOutput(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await api.get<NodeOutput>(ENDPOINTS.RUN_NODE(runId, nodeId));
      setNodeOutput(data);
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to fetch node output';
      setError(message);
      setNodeOutput(null);
    } finally {
      setIsLoading(false);
    }
  }, [runId, nodeId]);

  useEffect(() => {
    fetchNodeOutput();
  }, [fetchNodeOutput]);

  return { nodeOutput, isLoading, error, refetch: fetchNodeOutput };
}

export function useRunMutations(): UseRunMutationsResult {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const confirmRun = useCallback(async (runId: string, request: ConfirmRequest): Promise<ConfirmResponse> => {
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await api.post<ConfirmResponse>(ENDPOINTS.RUN_CONFIRM(runId), request);
      return response;
    } catch (err) {
      const message = err instanceof ApiClientError
        ? err.message
        : 'Failed to confirm run';
      setError(message);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  return { confirmRun, isSubmitting, error };
}
