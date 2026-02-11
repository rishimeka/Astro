'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Building2, GitCompare, Search, Bot } from 'lucide-react';
import { useChat } from '@/hooks/useChat';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import ExecutionProgress from './ExecutionProgress';
import ZeroShotProgress from './ZeroShotProgress';
import DirectiveGenerationCard from './DirectiveGenerationCard';
import { ConfirmationModal } from '@/components/Execution/ConfirmationModal';
import styles from './Chat.module.scss';

const SUGGESTED_ACTIONS = [
  { label: 'Analyze a company', icon: Building2 },
  { label: 'Compare competitors', icon: GitCompare },
  { label: 'Research a topic', icon: Search },
];

export default function Chat() {
  const {
    messages,
    sendMessage,
    isStreaming,
    error,
    clearChat,
    variableCollection,
    executionProgress,
    zeroShotProgress,
    confirmationRequest,
    respondToConfirmation,
  } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [inputValue, setInputValue] = useState('');
  const [isConfirmationSubmitting, setIsConfirmationSubmitting] = useState(false);

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
  };

  const handleInputChange = useCallback((value: string) => {
    setInputValue(value);
  }, []);

  const handleConfirm = async (additionalContext?: string) => {
    setIsConfirmationSubmitting(true);
    try {
      await respondToConfirmation(true, additionalContext);
    } finally {
      setIsConfirmationSubmitting(false);
    }
  };

  const handleCancelConfirmation = async () => {
    setIsConfirmationSubmitting(true);
    try {
      await respondToConfirmation(false);
    } finally {
      setIsConfirmationSubmitting(false);
    }
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const handleSend = async (content: string) => {
    await sendMessage(content);
  };

  return (
    <div className={styles.chatContainer}>
      <header className={styles.chatHeader}>
        <h1 className={styles.chatTitle}>Launchpad</h1>
        <button
          type="button"
          className="btn btn-primary btn-outline btn-sm"
          onClick={clearChat}
          disabled={messages.length === 0 && !isStreaming}
        >
          New Chat
        </button>
      </header>

      {error && (
        <div className={styles.errorMessage}>
          <svg
            className={styles.errorIcon}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
          {error}
        </div>
      )}

      <div className={styles.messagesContainer}>
        {messages.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyStateIcon}>
              <Bot strokeWidth={1.5} />
            </div>
            <h2 className={styles.emptyStateHeading}>
              How can I help you today?
            </h2>
            <p className={styles.emptyStateSubtext}>
              I&apos;m ready to assist with your analysis and research.
            </p>
            <div className={styles.suggestedActions}>
              {SUGGESTED_ACTIONS.map(({ label, icon: Icon }) => (
                <button
                  key={label}
                  type="button"
                  className={styles.suggestedAction}
                  onClick={() => handleSuggestionClick(label)}
                >
                  <Icon />
                  {label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div key={message.id}>
              <ChatMessage
                message={message}
                isStreaming={isStreaming && index === messages.length - 1 && message.role === 'assistant'}
              />
              {/* Show zero-shot progress for the most recent assistant message */}
              {message.role === 'assistant' &&
                index === messages.length - 1 &&
                isStreaming &&
                (zeroShotProgress.thinkingMessage ||
                  zeroShotProgress.selectedDirectives.length > 0 ||
                  zeroShotProgress.boundTools.length > 0) && (
                  <ZeroShotProgress
                    thinkingMessage={zeroShotProgress.thinkingMessage}
                    selectedDirectives={zeroShotProgress.selectedDirectives}
                    directiveReasoning={zeroShotProgress.directiveReasoning}
                    boundTools={zeroShotProgress.boundTools}
                  />
                )}
              {/* Show directive generation card if generating */}
              {message.role === 'assistant' &&
                isStreaming &&
                (zeroShotProgress.directiveGeneration.offered ||
                  zeroShotProgress.directiveGeneration.previewContent) && (
                  <DirectiveGenerationCard
                    offered={zeroShotProgress.directiveGeneration.offered}
                    previewContent={zeroShotProgress.directiveGeneration.previewContent}
                    directiveName={zeroShotProgress.directiveGeneration.directiveName}
                    selectedProbes={zeroShotProgress.directiveGeneration.selectedProbes}
                    isApproving={zeroShotProgress.directiveGeneration.isApproving}
                  />
                )}
              {/* Show execution progress below the assistant message that triggered the run */}
              {message.role === 'assistant' &&
                executionProgress.runId &&
                message.runId === executionProgress.runId && (
                  <ExecutionProgress
                    runId={executionProgress.runId}
                    constellationName={executionProgress.constellationName || message.constellationName || 'Constellation'}
                    currentNode={executionProgress.currentNodeName}
                    nodes={executionProgress.nodes}
                    toolCalls={executionProgress.toolCalls}
                    thoughts={executionProgress.thoughts}
                    totalNodes={executionProgress.totalNodes}
                    durationMs={executionProgress.durationMs}
                    isRunning={executionProgress.isRunning}
                  />
                )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className={styles.inputContainer}>
        <div className={styles.inputInner}>
          {variableCollection.isCollecting && (
            <div className={styles.variableCollectionIndicator}>
              <span className={styles.variableCollectionDot} />
              Collecting info for {variableCollection.constellationName || 'constellation'}...
            </div>
          )}
          <ChatInput
            onSend={handleSend}
            disabled={isStreaming}
            value={inputValue}
            onChange={handleInputChange}
          />
          <div className={styles.inputHint}>
            <kbd>Enter</kbd> to send, <kbd>Shift + Enter</kbd> for new line
          </div>
        </div>
      </div>

      {confirmationRequest && (
        <ConfirmationModal
          nodeId={confirmationRequest.nodeId}
          nodeName={confirmationRequest.nodeName}
          prompt={confirmationRequest.prompt}
          onConfirm={handleConfirm}
          onCancel={handleCancelConfirmation}
          isSubmitting={isConfirmationSubmitting}
        />
      )}
    </div>
  );
}
