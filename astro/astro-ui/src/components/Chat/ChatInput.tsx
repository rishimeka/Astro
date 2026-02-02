'use client';

import { useRef, useCallback, KeyboardEvent, ChangeEvent, useEffect } from 'react';
import { ArrowUp } from 'lucide-react';
import styles from './Chat.module.scss';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  value: string;
  onChange: (value: string) => void;
}

export default function ChatInput({ onSend, disabled, value, onChange }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, []);

  useEffect(() => {
    adjustHeight();
  }, [value, adjustHeight]);

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
  };

  const handleSend = useCallback(() => {
    if (value.trim() && !disabled) {
      onSend(value.trim());
      onChange('');
      // Reset height after sending
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  }, [value, disabled, onSend, onChange]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className={styles.inputWrapper}>
      <div className={styles.textareaWrapper}>
        <textarea
          ref={textareaRef}
          className={styles.textarea}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything..."
          disabled={disabled}
          rows={1}
          aria-label="Message input"
        />
      </div>
      <button
        type="button"
        className={styles.sendButton}
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        aria-label="Send message"
      >
        <ArrowUp className={styles.sendIcon} />
      </button>
    </div>
  );
}
