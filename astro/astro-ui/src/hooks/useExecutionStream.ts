'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { ENDPOINTS } from '@/lib/api/endpoints';
import type {
  SSENodeStarted,
  SSENodeProgress,
  SSENodeCompleted,
  SSENodeFailed,
  SSEAwaitingConfirmation,
  SSERunCompleted,
  SSERunFailed,
  RunStatus,
} from '@/types/astro';

// Node execution state
export type NodeExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'retrying';

export interface NodeExecutionState {
  nodeId: string;
  starId?: string;
  status: NodeExecutionStatus;
  progress?: string;
  output?: string;
  error?: string;
}

// Overall execution state
export interface ExecutionState {
  runId: string;
  status: RunStatus;
  nodeStates: Record<string, NodeExecutionState>;
  currentNodeId: string | null;
  awaitingConfirmation: {
    nodeId: string;
    prompt: string;
  } | null;
  finalOutput: string | null;
  error: string | null;
}

// SSE Event types
type SSEEventType =
  | 'run_started'
  | 'node_started'
  | 'node_progress'
  | 'node_completed'
  | 'node_failed'
  | 'node_retrying'
  | 'awaiting_confirmation'
  | 'run_resumed'
  | 'run_completed'
  | 'run_failed';

interface UseExecutionStreamOptions {
  runId: string;
  enabled?: boolean; // Set to false to not connect (e.g., for completed runs)
  initialStatus?: RunStatus; // If provided and terminal, don't connect
  onComplete?: (output: string) => void;
  onError?: (error: string) => void;
  onAwaitingConfirmation?: (nodeId: string, prompt: string) => void;
}

// Terminal statuses that don't need streaming
const TERMINAL_STATUSES: RunStatus[] = ['completed', 'failed', 'cancelled'];

export function useExecutionStream({
  runId,
  enabled = true,
  initialStatus,
  onComplete,
  onError,
  onAwaitingConfirmation,
}: UseExecutionStreamOptions) {
  // Don't connect if initial status is terminal
  const shouldConnect = enabled && (!initialStatus || !TERMINAL_STATUSES.includes(initialStatus));

  const [state, setState] = useState<ExecutionState>({
    runId,
    status: initialStatus || 'running',
    nodeStates: {},
    currentNodeId: null,
    awaitingConfirmation: null,
    finalOutput: null,
    error: null,
  });

  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  // Track if we've received a terminal event to prevent reconnection
  const isTerminalRef = useRef(initialStatus ? TERMINAL_STATUSES.includes(initialStatus) : false);
  const MAX_RETRIES = 3; // Reduced from 5
  const BASE_DELAY_MS = 2000; // Increased from 1000

  // Handle SSE events
  const handleEvent = useCallback(
    (eventType: SSEEventType, data: unknown) => {
      setState((prev) => {
        const newState = { ...prev };

        switch (eventType) {
          case 'run_started':
            newState.status = 'running';
            break;

          case 'node_started': {
            const nodeData = data as SSENodeStarted;
            newState.currentNodeId = nodeData.node_id;
            newState.nodeStates = {
              ...newState.nodeStates,
              [nodeData.node_id]: {
                nodeId: nodeData.node_id,
                starId: nodeData.star_id,
                status: 'running',
              },
            };
            break;
          }

          case 'node_progress': {
            const progressData = data as SSENodeProgress;
            const existingNode = newState.nodeStates[progressData.node_id];
            newState.nodeStates = {
              ...newState.nodeStates,
              [progressData.node_id]: {
                ...existingNode,
                nodeId: progressData.node_id,
                status: 'running',
                progress: progressData.message,
              },
            };
            break;
          }

          case 'node_completed': {
            const completedData = data as SSENodeCompleted;
            const existingCompletedNode = newState.nodeStates[completedData.node_id];
            newState.nodeStates = {
              ...newState.nodeStates,
              [completedData.node_id]: {
                ...existingCompletedNode,
                nodeId: completedData.node_id,
                status: 'completed',
                output: completedData.output,
              },
            };
            if (newState.currentNodeId === completedData.node_id) {
              newState.currentNodeId = null;
            }
            break;
          }

          case 'node_failed': {
            const failedData = data as SSENodeFailed;
            const existingFailedNode = newState.nodeStates[failedData.node_id];
            newState.nodeStates = {
              ...newState.nodeStates,
              [failedData.node_id]: {
                ...existingFailedNode,
                nodeId: failedData.node_id,
                status: 'failed',
                error: failedData.error,
              },
            };
            if (newState.currentNodeId === failedData.node_id) {
              newState.currentNodeId = null;
            }
            break;
          }

          case 'node_retrying': {
            const retryData = data as { node_id: string };
            const existingRetryNode = newState.nodeStates[retryData.node_id];
            newState.nodeStates = {
              ...newState.nodeStates,
              [retryData.node_id]: {
                ...existingRetryNode,
                nodeId: retryData.node_id,
                status: 'retrying',
              },
            };
            break;
          }

          case 'awaiting_confirmation': {
            const confirmData = data as SSEAwaitingConfirmation;
            newState.status = 'awaiting_confirmation';
            newState.awaitingConfirmation = {
              nodeId: confirmData.node_id,
              prompt: confirmData.prompt,
            };
            onAwaitingConfirmation?.(confirmData.node_id, confirmData.prompt);
            break;
          }

          case 'run_resumed': {
            // Run was resumed after user confirmation
            newState.status = 'running';
            newState.awaitingConfirmation = null;
            break;
          }

          case 'run_completed': {
            const completedRunData = data as SSERunCompleted;
            newState.status = 'completed';
            newState.finalOutput = completedRunData.final_output;
            newState.currentNodeId = null;
            // Mark as terminal to prevent any reconnection attempts
            isTerminalRef.current = true;
            onComplete?.(completedRunData.final_output);
            // Close the connection to prevent auto-reconnect
            if (eventSourceRef.current) {
              eventSourceRef.current.close();
              eventSourceRef.current = null;
            }
            break;
          }

          case 'run_failed': {
            const failedRunData = data as SSERunFailed;
            newState.status = 'failed';
            newState.error = failedRunData.error;
            newState.currentNodeId = null;
            // Mark as terminal to prevent any reconnection attempts
            isTerminalRef.current = true;
            onError?.(failedRunData.error);
            // Close the connection to prevent auto-reconnect
            if (eventSourceRef.current) {
              eventSourceRef.current.close();
              eventSourceRef.current = null;
            }
            break;
          }
        }

        return newState;
      });
    },
    [onComplete, onError, onAwaitingConfirmation]
  );

  // Connect to SSE stream
  useEffect(() => {
    // Don't connect if disabled, terminal, or already in terminal state
    if (!shouldConnect || isTerminalRef.current) {
      return;
    }

    const eventSource = new EventSource(ENDPOINTS.RUN_STREAM(runId));
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      retryCountRef.current = 0; // Reset retry count on successful connection
    };

    eventSource.onerror = () => {
      setIsConnected(false);

      // Don't reconnect if we've reached a terminal state
      if (isTerminalRef.current) {
        eventSource.close();
        eventSourceRef.current = null;
        return;
      }

      // Only handle reconnection if the connection was closed unexpectedly
      if (eventSource.readyState === EventSource.CLOSED) {
        retryCountRef.current += 1;

        if (retryCountRef.current >= MAX_RETRIES) {
          // Max retries exceeded - close and surface error
          console.error(`SSE connection failed after ${MAX_RETRIES} attempts`);
          eventSource.close();
          eventSourceRef.current = null;
          isTerminalRef.current = true; // Prevent further retries

          setState((prev) => ({
            ...prev,
            status: 'failed',
            error: `Connection lost after ${MAX_RETRIES} retry attempts`,
          }));
          onError?.(`Connection lost after ${MAX_RETRIES} retry attempts`);
        } else {
          // Exponential backoff: 2s, 4s, 8s
          const delay = BASE_DELAY_MS * Math.pow(2, retryCountRef.current - 1);
          console.log(`SSE reconnecting in ${delay}ms (attempt ${retryCountRef.current}/${MAX_RETRIES})`);

          // Close current connection to prevent auto-reconnect
          eventSource.close();
          eventSourceRef.current = null;
        }
      }
    };

    // Generic message handler
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleEvent('node_progress', data);
      } catch (error) {
        console.error('Failed to parse SSE message:', error);
      }
    };

    // Register specific event handlers
    const eventTypes: SSEEventType[] = [
      'run_started',
      'node_started',
      'node_progress',
      'node_completed',
      'node_failed',
      'node_retrying',
      'awaiting_confirmation',
      'run_resumed',
      'run_completed',
      'run_failed',
    ];

    eventTypes.forEach((eventType) => {
      eventSource.addEventListener(eventType, (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          handleEvent(eventType, data);
        } catch (error) {
          console.error(`Failed to parse SSE event (${eventType}):`, error);
        }
      });
    });

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
      setIsConnected(false);
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }
    };
  }, [runId, shouldConnect, handleEvent, onError]);

  // Disconnect function for manual cleanup
  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    retryCountRef.current = 0;
  }, []);

  // Clear awaiting confirmation state after user responds
  const clearAwaitingConfirmation = useCallback(() => {
    setState((prev) => ({
      ...prev,
      awaitingConfirmation: null,
      status: 'running',
    }));
  }, []);

  return {
    state,
    isConnected,
    disconnect,
    clearAwaitingConfirmation,
  };
}
