'use client';

import { useRef, useCallback, KeyboardEvent, ChangeEvent, useEffect, useState } from 'react';
import { ArrowUp, Paperclip, X } from 'lucide-react';
import styles from './Chat.module.scss';

interface ChatInputProps {
  onSend: (message: string, file?: File) => void;
  disabled?: boolean;
  value: string;
  onChange: (value: string) => void;
}

export default function ChatInput({ onSend, disabled, value, onChange }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

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

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleAttachClick = () => {
    fileInputRef.current?.click();
  };

  const handleSend = useCallback(() => {
    if (value.trim() && !disabled) {
      onSend(value.trim(), selectedFile || undefined);
      onChange('');
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      // Reset height after sending
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  }, [value, disabled, onSend, onChange, selectedFile]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div>
      {selectedFile && (
        <div className={styles.filePreview}>
          <div className={styles.filePreviewContent}>
            <Paperclip className={styles.filePreviewIcon} />
            <span className={styles.filePreviewName}>{selectedFile.name}</span>
            <span className={styles.filePreviewSize}>
              ({(selectedFile.size / 1024).toFixed(1)} KB)
            </span>
          </div>
          <button
            type="button"
            className={styles.filePreviewRemove}
            onClick={handleRemoveFile}
            aria-label="Remove file"
          >
            <X />
          </button>
        </div>
      )}
      <div className={styles.inputWrapper}>
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileSelect}
          className={styles.fileInput}
          accept=".xlsx,.xls,.pdf,.png,.jpg,.jpeg,.txt"
          aria-label="File upload"
        />
        <button
          type="button"
          className={styles.attachButton}
          onClick={handleAttachClick}
          disabled={disabled}
          aria-label="Attach file"
        >
          <Paperclip className={styles.attachIcon} />
        </button>
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
    </div>
  );
}
