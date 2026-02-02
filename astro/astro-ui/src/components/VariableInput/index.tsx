'use client';

import type { UIHint } from '@/types/astro';
import styles from './VariableInput.module.scss';

export interface VariableInputProps {
  name: string;
  description?: string;
  required?: boolean;
  uiHint: UIHint;
  uiOptions?: Record<string, unknown>;
  value: string | number | File | null;
  onChange: (value: string | number | File | null) => void;
  error?: string;
  showLabel?: boolean;
  className?: string;
}

export default function VariableInput({
  name,
  description,
  required = false,
  uiHint,
  uiOptions = {},
  value,
  onChange,
  error,
  showLabel = true,
  className = '',
}: VariableInputProps) {
  const renderInput = () => {
    switch (uiHint) {
      case 'text':
        return (
          <input
            type="text"
            className={`input ${error ? 'input-error' : ''} ${styles.textInput}`}
            value={(value as string) || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={uiOptions.placeholder as string}
          />
        );

      case 'textarea':
        return (
          <textarea
            className={`textarea ${error ? 'textarea-error' : ''} ${styles.textarea}`}
            value={(value as string) || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={uiOptions.placeholder as string}
            rows={uiOptions.rows as number || 4}
          />
        );

      case 'number':
        return (
          <input
            type="number"
            className={`input ${error ? 'input-error' : ''} ${styles.numberInput}`}
            value={value !== null && value !== undefined ? (value as string | number) : ''}
            onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
            min={uiOptions.min as number}
            max={uiOptions.max as number}
            step={uiOptions.step as number}
            placeholder={uiOptions.placeholder as string}
          />
        );

      case 'date':
        return (
          <input
            type="date"
            className={`input ${error ? 'input-error' : ''} ${styles.dateInput}`}
            value={(value as string) || ''}
            onChange={(e) => onChange(e.target.value)}
          />
        );

      case 'select': {
        const options = (uiOptions.options as string[]) || [];
        return (
          <select
            className={`select ${error ? 'select-error' : ''} ${styles.select}`}
            value={(value as string) || ''}
            onChange={(e) => onChange(e.target.value)}
          >
            <option value="">Select an option...</option>
            {options.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        );
      }

      case 'file':
        return (
          <input
            type="file"
            className={`${styles.fileInput} ${error ? 'input-error' : ''}`}
            onChange={(e) => onChange(e.target.files?.[0] || null)}
            accept={uiOptions.accept as string}
          />
        );

      default:
        return (
          <input
            type="text"
            className={`input ${error ? 'input-error' : ''} ${styles.textInput}`}
            value={(value as string) || ''}
            onChange={(e) => onChange(e.target.value)}
          />
        );
    }
  };

  return (
    <div className={`${styles.wrapper} ${className}`}>
      {showLabel && (
        <label className={styles.label}>
          <span className={styles.variableName}>{name}</span>
          {required && <span className={styles.required}>*</span>}
          <span className={styles.hintBadge}>{uiHint}</span>
        </label>
      )}
      {description && showLabel && (
        <p className={styles.description}>{description}</p>
      )}
      <div className={styles.inputWrapper}>
        {renderInput()}
      </div>
      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}

export { VariableInput };
