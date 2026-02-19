'use client';

import { useState, useCallback, useRef } from 'react';
import { ENDPOINTS } from '@/lib/api/endpoints';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  runId?: string;
  constellationName?: string;
}

export interface VariableCollectionState {
  isCollecting: boolean;
  constellationName?: string;
}

export interface NodeStatus {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  starType?: string;
  outputPreview?: string;
  error?: string;
  durationMs?: number;
}

export interface ToolCall {
  callId: string;
  toolName: string;
  input: Record<string, unknown>;
  status: 'running' | 'completed' | 'failed';
  resultPreview?: string;
  error?: string;
  durationMs?: number;
}

export interface ExecutionProgressState {
  isRunning: boolean;
  runId?: string;
  constellationId?: string;
  constellationName?: string;
  totalNodes: number;
  nodeNames: string[];
  nodes: NodeStatus[];
  currentNodeId?: string;
  currentNodeName?: string;
  toolCalls: ToolCall[];
  thoughts: string;
  durationMs?: number;
}

export interface ConfirmationRequest {
  nodeId: string;
  nodeName?: string;
  prompt: string;
}

export interface UseChat {
  messages: ChatMessage[];
  sendMessage: (content: string) => Promise<void>;
  isStreaming: boolean;
  error: string | null;
  clearChat: () => void;
  variableCollection: VariableCollectionState;
  executionProgress: ExecutionProgressState;
  confirmationRequest: ConfirmationRequest | null;
  respondToConfirmation: (approved: boolean, additionalContext?: string) => void;
}

// SSE Event Types from backend
interface SSETokenEvent {
  token: string;
}

interface SSERunStartedEvent {
  run_id: string;
  constellation_id?: string;
  constellation_name: string;
  total_nodes?: number;
  node_names?: string[];
}

interface SSERunCompletedEvent {
  run_id: string;
  final_output?: string;
  duration_ms?: number;
}

interface SSERunFailedEvent {
  run_id: string;
  error: string;
  failed_node_id?: string;
}

interface SSERunPausedEvent {
  run_id: string;
  node_id: string;
  node_name: string;
  prompt: string;
}

interface SSENodeStartedEvent {
  run_id: string;
  node_id: string;
  node_name: string;
  star_id: string;
  star_type: string;
  node_index: number;
  total_nodes: number;
}

interface SSENodeCompletedEvent {
  run_id: string;
  node_id: string;
  node_name: string;
  output_preview?: string;
  duration_ms: number;
}

interface SSENodeFailedEvent {
  run_id: string;
  node_id: string;
  node_name: string;
  error: string;
  duration_ms: number;
}

interface SSEToolCallEvent {
  run_id: string;
  node_id: string;
  tool_name: string;
  tool_input: Record<string, unknown>;
  call_id: string;
}

interface SSEToolResultEvent {
  run_id: string;
  node_id: string;
  tool_name: string;
  call_id: string;
  success: boolean;
  result_preview?: string;
  error?: string;
  duration_ms: number;
}

interface SSEThoughtEvent {
  run_id: string;
  node_id: string;
  content: string;
  is_complete: boolean;
}

interface SSEVariableCollectionEvent {
  collecting: boolean;
  constellation_name?: string;
}

interface SSEErrorEvent {
  message: string;
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function parseSSEEvents(buffer: string): { events: Array<{ type: string; data: string }>; remaining: string } {
  const events: Array<{ type: string; data: string }> = [];
  const blocks = buffer.split('\n\n');
  const remaining = blocks.pop() || '';

  for (const block of blocks) {
    if (!block.trim()) continue;

    const lines = block.split('\n');
    let eventType = 'message';
    let eventData = '';

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        eventType = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        eventData = line.slice(6);
      }
    }

    if (eventData.trim()) {
      events.push({ type: eventType, data: eventData });
    }
  }

  return { events, remaining };
}

const initialExecutionProgress: ExecutionProgressState = {
  isRunning: false,
  totalNodes: 0,
  nodeNames: [],
  nodes: [],
  toolCalls: [],
  thoughts: '',
};

export function useChat(): UseChat {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [variableCollection, setVariableCollection] = useState<VariableCollectionState>({
    isCollecting: false,
  });
  const [executionProgress, setExecutionProgress] = useState<ExecutionProgressState>(initialExecutionProgress);
  const [confirmationRequest, setConfirmationRequest] = useState<ConfirmationRequest | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isStreaming) return;

    setError(null);
    setIsStreaming(true);
    // Reset execution progress
    setExecutionProgress(initialExecutionProgress);

    // Add user message
    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Create placeholder assistant message
    const assistantMessageId = generateId();
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, assistantMessage]);

    // Set up SSE via fetch (POST requests require this approach)
    abortControllerRef.current = new AbortController();

    function handleSSEEvent(eventType: string, data: unknown, messageId: string) {
      switch (eventType) {
        case 'token': {
          const tokenData = data as SSETokenEvent;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === messageId ? { ...m, content: m.content + tokenData.token } : m
            )
          );
          break;
        }

        case 'run_started': {
          const runData = data as SSERunStartedEvent;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === messageId
                ? { ...m, runId: runData.run_id, constellationName: runData.constellation_name }
                : m
            )
          );

          // Initialize execution progress with node list
          const nodeStatuses: NodeStatus[] = (runData.node_names || []).map((name, index) => ({
            id: `node_${index}`,
            name,
            status: 'pending' as const,
          }));

          setExecutionProgress({
            isRunning: true,
            runId: runData.run_id,
            constellationId: runData.constellation_id,
            constellationName: runData.constellation_name,
            totalNodes: runData.total_nodes || nodeStatuses.length,
            nodeNames: runData.node_names || [],
            nodes: nodeStatuses,
            toolCalls: [],
            thoughts: '',
          });
          break;
        }

        case 'run_completed': {
          const completedData = data as SSERunCompletedEvent;
          setExecutionProgress((prev) => ({
            ...prev,
            isRunning: false,
            durationMs: completedData.duration_ms,
          }));
          break;
        }

        case 'run_failed': {
          const failedData = data as SSERunFailedEvent;
          setError(failedData.error);
          setExecutionProgress((prev) => ({
            ...prev,
            isRunning: false,
          }));
          break;
        }

        case 'run_paused': {
          const pausedData = data as SSERunPausedEvent;
          setConfirmationRequest({
            nodeId: pausedData.node_id,
            nodeName: pausedData.node_name,
            prompt: pausedData.prompt,
          });
          break;
        }

        case 'node_started': {
          const nodeData = data as SSENodeStartedEvent;
          setExecutionProgress((prev) => {
            // Update or add the node
            const existingIndex = prev.nodes.findIndex(n => n.id === nodeData.node_id);
            const updatedNode: NodeStatus = {
              id: nodeData.node_id,
              name: nodeData.node_name,
              status: 'running',
              starType: nodeData.star_type,
            };

            let nodes = [...prev.nodes];
            if (existingIndex >= 0) {
              nodes[existingIndex] = updatedNode;
            } else {
              // Insert at correct position
              const insertIndex = nodeData.node_index - 1;
              if (insertIndex >= 0 && insertIndex < nodes.length) {
                nodes[insertIndex] = updatedNode;
              } else {
                nodes.push(updatedNode);
              }
            }

            return {
              ...prev,
              currentNodeId: nodeData.node_id,
              currentNodeName: nodeData.node_name,
              totalNodes: nodeData.total_nodes,
              nodes,
              // Clear thoughts for new node
              thoughts: '',
            };
          });
          break;
        }

        case 'node_completed': {
          const nodeData = data as SSENodeCompletedEvent;
          setExecutionProgress((prev) => {
            const nodes = prev.nodes.map(n =>
              n.id === nodeData.node_id
                ? {
                    ...n,
                    status: 'completed' as const,
                    outputPreview: nodeData.output_preview,
                    durationMs: nodeData.duration_ms,
                  }
                : n
            );
            return {
              ...prev,
              nodes,
              currentNodeId: undefined,
              currentNodeName: undefined,
            };
          });
          break;
        }

        case 'node_failed': {
          const nodeData = data as SSENodeFailedEvent;
          setExecutionProgress((prev) => {
            const nodes = prev.nodes.map(n =>
              n.id === nodeData.node_id
                ? {
                    ...n,
                    status: 'failed' as const,
                    error: nodeData.error,
                    durationMs: nodeData.duration_ms,
                  }
                : n
            );
            return {
              ...prev,
              nodes,
              currentNodeId: undefined,
              currentNodeName: undefined,
            };
          });
          break;
        }

        case 'tool_call': {
          const toolData = data as SSEToolCallEvent;
          setExecutionProgress((prev) => ({
            ...prev,
            toolCalls: [
              ...prev.toolCalls,
              {
                callId: toolData.call_id,
                toolName: toolData.tool_name,
                input: toolData.tool_input,
                status: 'running',
              },
            ],
          }));
          break;
        }

        case 'tool_result': {
          const toolData = data as SSEToolResultEvent;
          setExecutionProgress((prev) => ({
            ...prev,
            toolCalls: prev.toolCalls.map(tc =>
              tc.callId === toolData.call_id
                ? {
                    ...tc,
                    status: toolData.success ? 'completed' : 'failed',
                    resultPreview: toolData.result_preview,
                    error: toolData.error,
                    durationMs: toolData.duration_ms,
                  }
                : tc
            ),
          }));
          break;
        }

        case 'thought': {
          const thoughtData = data as SSEThoughtEvent;
          setExecutionProgress((prev) => ({
            ...prev,
            thoughts: prev.thoughts + thoughtData.content,
          }));
          break;
        }

        case 'variable_collection': {
          const varData = data as SSEVariableCollectionEvent;
          setVariableCollection({
            isCollecting: varData.collecting,
            constellationName: varData.constellation_name,
          });
          break;
        }

        case 'error': {
          const errorData = data as SSEErrorEvent;
          setError(errorData.message);
          break;
        }

        case 'conversation_id': {
          const convData = data as { conversation_id: string };
          setConversationId(convData.conversation_id);
          break;
        }

        case 'log': {
          // Could show in UI or just log to console
          const logData = data as { level: string; message: string };
          if (logData.level === 'error') {
            console.error('[Execution Log]', logData.message);
          } else {
            console.log('[Execution Log]', logData.message);
          }
          break;
        }

        case 'progress': {
          // Progress updates within a node
          const progressData = data as { message: string; percent?: number };
          console.log('[Progress]', progressData.message, progressData.percent);
          break;
        }

        case 'done': {
          // Streaming complete
          break;
        }
      }
    }

    try {
      const response = await fetch(ENDPOINTS.CHAT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({
          message: content.trim(),
          conversation_id: conversationId,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Request failed' }));
        throw new Error(errorData.message || `HTTP ${response.status}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const { events, remaining } = parseSSEEvents(buffer);
        buffer = remaining;

        for (const event of events) {
          try {
            const data = JSON.parse(event.data);
            handleSSEEvent(event.type, data, assistantMessageId);
          } catch {
            // Ignore parse errors
          }
        }
      }

      // Process any remaining buffer
      if (buffer.trim()) {
        const { events } = parseSSEEvents(buffer + '\n\n');
        for (const event of events) {
          try {
            const data = JSON.parse(event.data);
            handleSSEEvent(event.type, data, assistantMessageId);
          } catch {
            // Ignore parse errors
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Request was cancelled, not an error
        return;
      }
      const errorMessage = err instanceof Error ? err.message : 'An error occurred';
      setError(errorMessage);
      // Remove the empty assistant message on error
      setMessages((prev) => prev.filter((m) => m.id !== assistantMessageId));
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  }, [isStreaming, conversationId]);

  const clearChat = useCallback(() => {
    // Abort any in-progress request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setMessages([]);
    setError(null);
    setIsStreaming(false);
    setConversationId(undefined);
    setVariableCollection({ isCollecting: false });
    setExecutionProgress(initialExecutionProgress);
    setConfirmationRequest(null);
  }, []);

  const respondToConfirmation = useCallback(async (approved: boolean, additionalContext?: string) => {
    if (!confirmationRequest || !conversationId) return;

    try {
      await fetch(`${ENDPOINTS.CHAT}/confirm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          node_id: confirmationRequest.nodeId,
          approved,
          additional_context: additionalContext,
        }),
      });
      setConfirmationRequest(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send confirmation';
      setError(errorMessage);
    }
  }, [confirmationRequest, conversationId]);

  return {
    messages,
    sendMessage,
    isStreaming,
    error,
    clearChat,
    variableCollection,
    executionProgress,
    confirmationRequest,
    respondToConfirmation,
  };
}
