'use client';

import { useState, KeyboardEvent } from 'react';
import { X } from 'lucide-react';
import styles from './DirectiveWizard.module.scss';

export interface Step1Data {
  name: string;
  description: string;
  tags: string[];
}

interface Step1IdentityProps {
  data: Step1Data;
  onChange: (data: Step1Data) => void;
  errors: Partial<Record<keyof Step1Data, string>>;
}

export default function Step1Identity({ data, onChange, errors }: Step1IdentityProps) {
  const [tagInput, setTagInput] = useState('');

  const handleAddTag = () => {
    const trimmedTag = tagInput.trim().toLowerCase();
    if (trimmedTag && !data.tags.includes(trimmedTag)) {
      onChange({ ...data, tags: [...data.tags, trimmedTag] });
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    onChange({ ...data, tags: data.tags.filter((tag) => tag !== tagToRemove) });
  };

  const handleTagKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    } else if (e.key === 'Backspace' && !tagInput && data.tags.length > 0) {
      // Remove last tag on backspace when input is empty
      handleRemoveTag(data.tags[data.tags.length - 1]);
    }
  };

  return (
    <div className={styles.stepContent}>
      <h2 className={styles.stepTitle}>Directive Identity</h2>
      <p className={styles.stepDescription}>
        Give your directive a name, description, and optional tags for organization.
      </p>

      <div className={styles.field}>
        <label className={styles.fieldLabel}>
          Name
          <span className={styles.fieldRequired}>*</span>
        </label>
        <input
          type="text"
          className={`input ${errors.name ? 'input-error' : ''}`}
          value={data.name}
          onChange={(e) => onChange({ ...data, name: e.target.value })}
          placeholder="e.g., Code Review Assistant"
        />
        {errors.name && <p className={styles.fieldError}>{errors.name}</p>}
      </div>

      <div className={styles.field}>
        <label className={styles.fieldLabel}>
          Description
          <span className={styles.fieldRequired}>*</span>
        </label>
        <textarea
          className={`textarea ${errors.description ? 'textarea-error' : ''}`}
          value={data.description}
          onChange={(e) => onChange({ ...data, description: e.target.value })}
          placeholder="Describe what this directive does..."
          rows={3}
        />
        {errors.description && <p className={styles.fieldError}>{errors.description}</p>}
      </div>

      <div className={styles.field}>
        <label className={styles.fieldLabel}>Tags</label>
        <div className={styles.tagsInput}>
          {data.tags.map((tag) => (
            <span key={tag} className={styles.tag}>
              {tag}
              <button
                type="button"
                className={styles.tagRemove}
                onClick={() => handleRemoveTag(tag)}
                aria-label={`Remove ${tag} tag`}
              >
                <X size={12} />
              </button>
            </span>
          ))}
          <input
            type="text"
            className={styles.tagInputField}
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={handleTagKeyDown}
            onBlur={handleAddTag}
            placeholder={data.tags.length === 0 ? 'Add tags (press Enter)...' : ''}
          />
        </div>
        <p className={styles.fieldHint}>Press Enter to add a tag. Tags help organize and filter directives.</p>
      </div>
    </div>
  );
}
