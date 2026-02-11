'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { api, ApiClientError, ENDPOINTS } from '@/lib/api';
import type {
  SSERunStarted,
  SSENodeStarted,
  SSENodeProgress,
  SSENodeCompleted,
  SSENodeFailed,
  SSEAwaitingConfirmation,
  SSERunCompleted,
  SSERunFailed,
  ConfirmResponse,
} from '@/types/astro';

// ============================================================================
// Types
// ============================================================================

export type ExecutionStatusType =
  | 'idle'
  | 'running'
  | 'awaiting_confirmation'
  | 'completed'
  | 'failed';

export type NodeStatusType =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'awaiting_confirmation'
  | 'retrying';

export interface NodeStatus {
  status: NodeStatusType;
  retryInfo?: {
    attempt: number;
    maxAttempts: number;
    lastError: string;
  };
}

export interface NodeOutput {
  node_id: string;
  star_id: string;
  status: string;
  output?: string;
  error?: string;
  tool_calls?: unknown[];
  started_at?: string;
  completed_at?: string;
}

export interface AwaitingConfirmation {
  nodeId: string;
  output: string;
  prompt: string;
}

export interface ExecutionState {
  status: ExecutionStatusType;
  runId: string | null;
  nodeStatuses: Record<string, NodeStatus>;
  nodeOutputs: Record<string, NodeOutput>;
  progressMessages: string[];
  finalOutput: string | null;
  error: string | null;
  awaitingConfirmation: AwaitingConfirmation | null;
}

export interface UseConstellationExecutionResult {
  state: ExecutionState;
  execute: (variables: Record<string, string>) => Promise<void>;
  confirmContinue: (additionalContext?: string) => Promise<void>;
  confirmCancel: () => Promise<void>;
  reset: () => void;
}

// SSE Event types
type SSEEventType =
  | 'run_started'
  | 'node_started'
  | 'node_progress'
  | 'node_completed'
  | 'node_failed'
  | 'node_retrying'
  | 'node_awaiting_confirmation'
  | 'run_completed'
  | 'run_failed';

// SSE node retrying event data
interface SSENodeRetrying {
  node_id: string;
  attempt: number;
  max_attempts: number;
  error: string;
}

// SSE node awaiting confirmation event data (if different from run-level)
interface SSENodeAwaitingConfirmation {
  node_id: string;
  star_id?: string;
  output?: string;
  prompt: string;
}

// Run start response from API
interface RunStartResponse {
  run_id: string;
  constellation_id: string;
  constellation_name: string;
  status: string;
  message: string;
}

// ============================================================================
// Initial State
// ============================================================================

const initialState: ExecutionState = {
  status: 'idle',
  runId: null,
  nodeStatuses: {},
  nodeOutputs: {},
  progressMessages: [],
  finalOutput: null,
  error: null,
  awaitingConfirmation: null,
};

// ============================================================================
// Hook Implementation
// ============================================================================

export function useConstellationExecution(
  constellationId: string
): UseConstellationExecutionResult {
  const [state, setState] = useState<ExecutionState>(initialState);

  // Refs for managing SSE connection
  const eventSourceRef = useRef<EventSource | null>(null);
  const isTerminalRef = useRef(false);

  // Cleanup function for SSE connection
  const cleanupSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupSSE();
    };
  }, [cleanupSSE]);

  // Handle SSE events
  const handleSSEEvent = useCallback((eventType: SSEEventType, data: unknown) => {
    setState((prev) => {
      const newState = { ...prev };

      switch (eventType) {
        case 'run_started': {
          const runData = data as SSERunStarted;
          newState.status = 'running';
          newState.runId = runData.run_id;
          newState.progressMessages = [
            ...prev.progressMessages,
            `Run ${runData.run_id} started`,
          ];
          break;
        }

        case 'node_started': {
          const nodeData = data as SSENodeStarted;
          newState.nodeStatuses = {
            ...prev.nodeStatuses,
            [nodeData.node_id]: {
              status: 'running',
            },
          };
          newState.nodeOutputs = {
            ...prev.nodeOutputs,
            [nodeData.node_id]: {
              node_id: nodeData.node_id,
              star_id: nodeData.star_id,
              status: 'running',
              started_at: new Date().toISOString(),
            },
          };
          newState.progressMessages = [
            ...prev.progressMessages,
            `Node ${nodeData.node_id} started`,
          ];
          break;
        }

        case 'node_progress': {
          const progressData = data as SSENodeProgress;
          newState.progressMessages = [
            ...prev.progressMessages,
            progressData.message,
          ];
          break;
        }

        case 'node_completed': {
          const completedData = data as SSENodeCompleted;
          newState.nodeStatuses = {
            ...prev.nodeStatuses,
            [completedData.node_id]: {
              status: 'completed',
            },
          };
          const existingOutput = prev.nodeOutputs[completedData.node_id] || {
            node_id: completedData.node_id,
            star_id: '',
          };
          newState.nodeOutputs = {
            ...prev.nodeOutputs,
            [completedData.node_id]: {
              ...existingOutput,
              status: 'completed',
              output: completedData.output,
              completed_at: new Date().toISOString(),
            },
          };
          newState.progressMessages = [
            ...prev.progressMessages,
            `Node ${completedData.node_id} completed`,
          ];
          break;
        }

        case 'node_failed': {
          const failedData = data as SSENodeFailed;
          newState.nodeStatuses = {
            ...prev.nodeStatuses,
            [failedData.node_id]: {
              status: 'failed',
            },
          };
          const existingFailedOutput = prev.nodeOutputs[failedData.node_id] || {
            node_id: failedData.node_id,
            star_id: '',
          };
          newState.nodeOutputs = {
            ...prev.nodeOutputs,
            [failedData.node_id]: {
              ...existingFailedOutput,
              status: 'failed',
              error: failedData.error,
              completed_at: new Date().toISOString(),
            },
          };
          newState.progressMessages = [
            ...prev.progressMessages,
            `Node ${failedData.node_id} failed: ${failedData.error}`,
          ];
          break;
        }

        case 'node_retrying': {
          const retryData = data as SSENodeRetrying;
          newState.nodeStatuses = {
            ...prev.nodeStatuses,
            [retryData.node_id]: {
              status: 'retrying',
              retryInfo: {
                attempt: retryData.attempt,
                maxAttempts: retryData.max_attempts,
                lastError: retryData.error,
              },
            },
          };
          newState.progressMessages = [
            ...prev.progressMessages,
            `Node ${retryData.node_id} retrying (attempt ${retryData.attempt}/${retryData.max_attempts})`,
          ];
          break;
        }

        case 'node_awaiting_confirmation': {
          const confirmData = data as SSENodeAwaitingConfirmation;
          newState.status = 'awaiting_confirmation';
          newState.nodeStatuses = {
            ...prev.nodeStatuses,
            [confirmData.node_id]: {
              status: 'awaiting_confirmation',
            },
          };
          newState.awaitingConfirmation = {
            nodeId: confirmData.node_id,
            output: confirmData.output || '',
            prompt: confirmData.prompt,
          };
          newState.progressMessages = [
            ...prev.progressMessages,
            `Awaiting confirmation for node ${confirmData.node_id}`,
          ];
          break;
        }

        case 'run_completed': {
          const completedRunData = data as SSERunCompleted;
          newState.status = 'completed';
          newState.finalOutput = completedRunData.final_output;
          newState.progressMessages = [
            ...prev.progressMessages,
            'Run completed successfully',
          ];
          isTerminalRef.current = true;
          break;
        }

        case 'run_failed': {
          const failedRunData = data as SSERunFailed;
          newState.status = 'failed';
          newState.error = failedRunData.error;
          newState.progressMessages = [
            ...prev.progressMessages,
            `Run failed: ${failedRunData.error}`,
          ];
          isTerminalRef.current = true;
          break;
        }
      }

      return newState;
    });
  }, []);

  // Also handle the awaiting_confirmation event (backend may send either name)
  const handleAwaitingConfirmation = useCallback((data: unknown) => {
    const confirmData = data as SSEAwaitingConfirmation;
    setState((prev) => ({
      ...prev,
      status: 'awaiting_confirmation',
      nodeStatuses: {
        ...prev.nodeStatuses,
        [confirmData.node_id]: {
          status: 'awaiting_confirmation',
        },
      },
      awaitingConfirmation: {
        nodeId: confirmData.node_id,
        output: '',
        prompt: confirmData.prompt,
      },
      progressMessages: [
        ...prev.progressMessages,
        `Awaiting confirmation for node ${confirmData.node_id}`,
      ],
    }));
  }, []);

  // Connect to SSE stream
  const connectToSSE = useCallback(
    (runId: string) => {
      // Clean up any existing connection
      cleanupSSE();
      isTerminalRef.current = false;

      const streamUrl = ENDPOINTS.RUN_STREAM(runId);
      const eventSource = new EventSource(streamUrl);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('SSE connection opened for run:', runId);
      };

      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);

        // If in terminal state, just clean up
        if (isTerminalRef.current) {
          cleanupSSE();
          return;
        }

        // If connection was closed unexpectedly, surface error
        if (eventSource.readyState === EventSource.CLOSED) {
          setState((prev) => ({
            ...prev,
            status: 'failed',
            error: 'Connection to server lost',
            progressMessages: [
              ...prev.progressMessages,
              'Connection to server lost',
            ],
          }));
          isTerminalRef.current = true;
        }
      };

      // Register event handlers for all SSE event types
      const eventTypes: SSEEventType[] = [
        'run_started',
        'node_started',
        'node_progress',
        'node_completed',
        'node_failed',
        'node_retrying',
        'node_awaiting_confirmation',
        'run_completed',
        'run_failed',
      ];

      eventTypes.forEach((eventType) => {
        eventSource.addEventListener(eventType, (event: MessageEvent) => {
          try {
            const data = JSON.parse(event.data);
            handleSSEEvent(eventType, data);

            // Close connection on terminal events
            if (eventType === 'run_completed' || eventType === 'run_failed') {
              cleanupSSE();
            }
          } catch (parseError) {
            console.error(`Failed to parse SSE event (${eventType}):`, parseError);
          }
        });
      });

      // Also listen for 'awaiting_confirmation' (alternate event name from backend)
      eventSource.addEventListener('awaiting_confirmation', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          handleAwaitingConfirmation(data);
        } catch (parseError) {
          console.error('Failed to parse awaiting_confirmation event:', parseError);
        }
      });

      // Handle run_resumed event (after confirmation)
      eventSource.addEventListener('run_resumed', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          setState((prev) => ({
            ...prev,
            status: 'running',
            awaitingConfirmation: null,
            progressMessages: [
              ...prev.progressMessages,
              `Run resumed${data.message ? `: ${data.message}` : ''}`,
            ],
          }));
        } catch (parseError) {
          console.error('Failed to parse run_resumed event:', parseError);
        }
      });

      // Generic message handler as fallback
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // Treat generic messages as progress
          if (data.message) {
            setState((prev) => ({
              ...prev,
              progressMessages: [...prev.progressMessages, data.message],
            }));
          }
        } catch (parseError) {
          console.error('Failed to parse SSE message:', parseError);
        }
      };
    },
    [cleanupSSE, handleSSEEvent, handleAwaitingConfirmation]
  );

  // Execute constellation
  const execute = useCallback(
    async (variables: Record<string, string>): Promise<void> => {
      // Reset state before starting
      setState({
        ...initialState,
        status: 'running',
        progressMessages: ['Starting execution...'],
      });
      isTerminalRef.current = false;

      try {
        // Start the run via API
        const response = await api.post<RunStartResponse>(
          ENDPOINTS.CONSTELLATION_RUN(constellationId),
          { variables }
        );

        // Update state with run ID
        setState((prev) => ({
          ...prev,
          runId: response.run_id,
          progressMessages: [
            ...prev.progressMessages,
            `Run created: ${response.run_id}`,
          ],
        }));

        // Connect to SSE stream
        connectToSSE(response.run_id);
      } catch (err) {
        const errorMessage =
          err instanceof ApiClientError
            ? err.message
            : 'Failed to start execution';

        setState((prev) => ({
          ...prev,
          status: 'failed',
          error: errorMessage,
          progressMessages: [...prev.progressMessages, `Error: ${errorMessage}`],
        }));

        isTerminalRef.current = true;
        throw err;
      }
    },
    [constellationId, connectToSSE]
  );

  // Confirm and continue execution
  const confirmContinue = useCallback(
    async (additionalContext?: string): Promise<void> => {
      const { runId } = state;
      if (!runId) {
        throw new Error('No active run to confirm');
      }

      try {
        setState((prev) => ({
          ...prev,
          progressMessages: [...prev.progressMessages, 'Sending confirmation...'],
        }));

        await api.post<ConfirmResponse>(ENDPOINTS.RUN_CONFIRM(runId), {
          proceed: true,
          additional_context: additionalContext,
        });

        // State will be updated by SSE 'run_resumed' event
        // But we can optimistically update some state
        setState((prev) => ({
          ...prev,
          status: 'running',
          awaitingConfirmation: null,
          progressMessages: [...prev.progressMessages, 'Confirmation sent, resuming...'],
        }));
      } catch (err) {
        const errorMessage =
          err instanceof ApiClientError
            ? err.message
            : 'Failed to confirm continuation';

        setState((prev) => ({
          ...prev,
          error: errorMessage,
          progressMessages: [...prev.progressMessages, `Confirmation error: ${errorMessage}`],
        }));

        throw err;
      }
    },
    [state]
  );

  // Cancel execution
  const confirmCancel = useCallback(async (): Promise<void> => {
    const { runId } = state;
    if (!runId) {
      throw new Error('No active run to cancel');
    }

    try {
      setState((prev) => ({
        ...prev,
        progressMessages: [...prev.progressMessages, 'Cancelling execution...'],
      }));

      await api.post<ConfirmResponse>(ENDPOINTS.RUN_CONFIRM(runId), {
        proceed: false,
      });

      // Clean up SSE connection
      cleanupSSE();

      setState((prev) => ({
        ...prev,
        status: 'failed',
        error: 'Execution cancelled by user',
        awaitingConfirmation: null,
        progressMessages: [...prev.progressMessages, 'Execution cancelled'],
      }));

      isTerminalRef.current = true;
    } catch (err) {
      const errorMessage =
        err instanceof ApiClientError
          ? err.message
          : 'Failed to cancel execution';

      setState((prev) => ({
        ...prev,
        error: errorMessage,
        progressMessages: [...prev.progressMessages, `Cancel error: ${errorMessage}`],
      }));

      throw err;
    }
  }, [state, cleanupSSE]);

  // Reset to initial state
  const reset = useCallback(() => {
    cleanupSSE();
    isTerminalRef.current = false;
    setState(initialState);
  }, [cleanupSSE]);

  return {
    state,
    execute,
    confirmContinue,
    confirmCancel,
    reset,
  };
}
