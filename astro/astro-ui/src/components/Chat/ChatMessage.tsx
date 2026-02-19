import Link from 'next/link';
import { Bot, CheckCircle, Paperclip, User } from 'lucide-react';
import type { ChatMessage as ChatMessageType } from '@/hooks/useChat';
import { Markdown } from '@/components/Markdown';
import styles from './Chat.module.scss';
import StreamingIndicator from './StreamingIndicator';

interface ChatMessageProps {
  message: ChatMessageType;
  isStreaming?: boolean;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const isAssistant = message.role === 'assistant';
  const isEmpty = !message.content.trim();

  return (
    <div className={`${styles.messageRow} ${styles[message.role]}`}>
      <div className={`${styles.messageAvatar} ${styles[message.role]}`}>
        {isAssistant ? <Bot size={20} /> : <User size={18} />}
      </div>
      <div className={styles.messageContent}>
        {isAssistant && (
          <div className={styles.messageHeader}>
            <span className={styles.messageSender}>Launchpad AI</span>
            <span className={styles.messageBadge}>Bot</span>
          </div>
        )}
        <div className={styles.messageBubble}>
          {isEmpty && isStreaming ? (
            <StreamingIndicator />
          ) : (
            <Markdown>{message.content}</Markdown>
          )}
          {message.fileName && (
            <div className={styles.messageFileCard}>
              <Paperclip className={styles.messageFileIcon} />
              <span className={styles.messageFileName}>{message.fileName}</span>
            </div>
          )}
        </div>
        <span className={styles.messageTimestamp}>{formatTime(message.timestamp)}</span>
        {isAssistant && message.runId && message.constellationName && (
          <Link
            href={`/runs/${message.runId}`}
            className={styles.runInfo}
          >
            <CheckCircle size={16} />
            Ran: {message.constellationName}
          </Link>
        )}
      </div>
    </div>
  );
}
