'use client';

import { useState, useEffect, useRef } from 'react';
import {
  AlertCircle,
  Loader2,
  FileText,
  Calendar,
  Hash,
  Type,
  AlignLeft,
  List,
  Upload,
  X,
  Play,
} from 'lucide-react';
import { useConstellationVariables } from '@/hooks/useConstellations';
import type { TemplateVariable, UIHint } from '@/types/astro';
import styles from './VariableForm.module.scss';

interface VariableFormProps {
  constellationId: string;
  onSubmit: (variables: Record<string, string>) => void;
  onCancel: () => void;
}

interface FieldError {
  name: string;
  message: string;
}

function getIconForHint(hint: UIHint | null) {
  switch (hint) {
    case 'textarea':
      return AlignLeft;
    case 'number':
      return Hash;
    case 'date':
      return Calendar;
    case 'select':
      return List;
    case 'file':
      return FileText;
    case 'text':
    default:
      return Type;
  }
}

function VariableField({
  variable,
  value,
  onChange,
  onBlur,
  disabled,
  hasError,
  fileInputRef,
  onFileRemove,
}: {
  variable: TemplateVariable;
  value: string;
  onChange: (value: string) => void;
  onBlur: () => void;
  disabled?: boolean;
  hasError?: boolean;
  fileInputRef?: React.RefObject<HTMLInputElement | null>;
  onFileRemove?: () => void;
}) {
  const Icon = getIconForHint(variable.ui_hint);
  const uiOptions = variable.ui_options || {};

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        onChange(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const renderInput = () => {
    switch (variable.ui_hint) {
      case 'textarea':
        return (
          <textarea
            className={`textarea ${hasError ? 'textarea-error' : ''}`}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            placeholder={(uiOptions.placeholder as string) || `Enter ${variable.name}...`}
            disabled={disabled}
            rows={(uiOptions.rows as number) || 4}
          />
        );

      case 'number':
        return (
          <input
            type="number"
            className={`input ${hasError ? 'input-error' : ''}`}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            placeholder={(uiOptions.placeholder as string) || `Enter ${variable.name}...`}
            disabled={disabled}
            min={uiOptions.min as number | undefined}
            max={uiOptions.max as number | undefined}
            step={uiOptions.step as number | undefined}
          />
        );

      case 'date':
        return (
          <input
            type="date"
            className={`input ${hasError ? 'input-error' : ''}`}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            disabled={disabled}
          />
        );

      case 'select': {
        const options = (uiOptions.options as Array<string | { value: string; label: string }>) || [];
        return (
          <select
            className={`select ${hasError ? 'select-error' : ''}`}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            disabled={disabled}
          >
            <option value="">Select {variable.name}...</option>
            {options.map((option) => {
              const optValue = typeof option === 'string' ? option : option.value;
              const optLabel = typeof option === 'string' ? option : option.label;
              return (
                <option key={optValue} value={optValue}>
                  {optLabel}
                </option>
              );
            })}
          </select>
        );
      }

      case 'file': {
        const accept = uiOptions.accept as string | undefined;
        const hasFile = !!value;

        return (
          <div className={styles.fileInputWrapper}>
            <input
              ref={fileInputRef}
              type="file"
              id={`var-${variable.name}`}
              accept={accept}
              onChange={handleFileChange}
              onBlur={onBlur}
              disabled={disabled}
              className={styles.fileInputHidden}
            />
            {!hasFile ? (
              <label
                htmlFor={`var-${variable.name}`}
                className={`${styles.fileInputLabel} ${hasError ? styles.fileInputError : ''}`}
              >
                <Upload size={18} />
                <span>Choose file</span>
                {accept && <span className={styles.fileAccept}>{accept}</span>}
              </label>
            ) : (
              <div className={styles.fileSelected}>
                <FileText size={18} />
                <span className={styles.fileName}>File selected</span>
                <button
                  type="button"
                  className={styles.fileRemove}
                  onClick={onFileRemove}
                  disabled={disabled}
                >
                  <X size={14} />
                </button>
              </div>
            )}
          </div>
        );
      }

      case 'text':
      default:
        return (
          <input
            type="text"
            className={`input ${hasError ? 'input-error' : ''}`}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            placeholder={(uiOptions.placeholder as string) || `Enter ${variable.name}...`}
            disabled={disabled}
          />
        );
    }
  };

  return (
    <div className={styles.fieldWrapper}>
      <label className={styles.fieldLabel}>
        <Icon size={14} className={styles.fieldIcon} />
        <span className={styles.fieldName}>{variable.name}</span>
        {variable.required && <span className={styles.requiredBadge}>Required</span>}
      </label>
      {renderInput()}
    </div>
  );
}

export function VariableForm({
  constellationId,
  onSubmit,
  onCancel,
}: VariableFormProps) {
  const { variables, isLoading, error } = useConstellationVariables(constellationId);
  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<FieldError[]>([]);
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  // Initialize values with defaults when variables load
  useEffect(() => {
    if (variables.length > 0) {
      const initialValues: Record<string, string> = {};
      variables.forEach((v) => {
        if (v.default !== null && v.default !== undefined) {
          initialValues[v.name] = v.default;
        }
      });
      setValues(initialValues);
    }
  }, [variables]);

  const handleChange = (name: string, value: string) => {
    setValues((prev) => ({ ...prev, [name]: value }));
    // Clear error for this field when user types
    setErrors((prev) => prev.filter((e) => e.name !== name));
  };

  const handleBlur = (name: string) => {
    setTouched((prev) => ({ ...prev, [name]: true }));
  };

  const handleFileRemove = (name: string) => {
    handleChange(name, '');
    if (fileInputRefs.current[name]) {
      fileInputRefs.current[name]!.value = '';
    }
  };

  const validate = (): boolean => {
    const newErrors: FieldError[] = [];

    variables.forEach((variable) => {
      const value = values[variable.name] || '';

      if (variable.required && !value.trim()) {
        newErrors.push({
          name: variable.name,
          message: `${variable.name} is required`,
        });
      }

      // Number validation
      if (variable.ui_hint === 'number' && value) {
        const numValue = parseFloat(value);
        const options = variable.ui_options || {};

        if (isNaN(numValue)) {
          newErrors.push({
            name: variable.name,
            message: 'Must be a valid number',
          });
        } else {
          if (typeof options.min === 'number' && numValue < options.min) {
            newErrors.push({
              name: variable.name,
              message: `Must be at least ${options.min}`,
            });
          }
          if (typeof options.max === 'number' && numValue > options.max) {
            newErrors.push({
              name: variable.name,
              message: `Must be at most ${options.max}`,
            });
          }
        }
      }
    });

    setErrors(newErrors);
    // Mark all fields as touched
    const allTouched: Record<string, boolean> = {};
    variables.forEach((v) => {
      allTouched[v.name] = true;
    });
    setTouched(allTouched);

    return newErrors.length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      onSubmit(values);
    }
  };

  const getFieldError = (name: string): string | undefined => {
    return errors.find((e) => e.name === name)?.message;
  };

  // Loading state
  if (isLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.loadingState}>
          <Loader2 size={24} className={styles.spinner} />
          <span>Loading variables...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.errorState}>
          <AlertCircle size={24} />
          <span>{error}</span>
          <button className="btn btn-primary btn-outline btn-sm" onClick={onCancel}>
            Go Back
          </button>
        </div>
      </div>
    );
  }

  // No variables state
  if (variables.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.emptyState}>
          <Type size={32} />
          <h3 className={styles.emptyTitle}>No Variables Required</h3>
          <p className={styles.emptyHint}>
            This constellation does not require any input variables. You can start the run immediately.
          </p>
          <div className={styles.emptyActions}>
            <button className="btn btn-black-and-white btn-outline" onClick={onCancel}>
              Cancel
            </button>
            <button className="btn btn-primary btn-highlight" onClick={() => onSubmit({})}>
              <Play size={16} />
              Start Run
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Group variables by required/optional
  const requiredVariables = variables.filter((v) => v.required);
  const optionalVariables = variables.filter((v) => !v.required);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>Configure Variables</h3>
        <p className={styles.subtitle}>
          Fill in the required variables to start this constellation run.
        </p>
      </div>

      <form className={styles.form} onSubmit={handleSubmit}>
        {requiredVariables.length > 0 && (
          <div className={styles.section}>
            <h4 className={styles.sectionTitle}>Required Inputs</h4>
            <div className={styles.fields}>
              {requiredVariables.map((variable) => {
                const fieldError = getFieldError(variable.name);
                const showError = touched[variable.name] && fieldError;

                return (
                  <div key={variable.name} className={styles.fieldGroup}>
                    <VariableField
                      variable={variable}
                      value={values[variable.name] || ''}
                      onChange={(value) => handleChange(variable.name, value)}
                      onBlur={() => handleBlur(variable.name)}
                      hasError={!!showError}
                      fileInputRef={{ current: fileInputRefs.current[variable.name] || null }}
                      onFileRemove={() => handleFileRemove(variable.name)}
                    />

                    {variable.description && !showError && (
                      <p className="field-helper">{variable.description}</p>
                    )}

                    {showError && <p className="field-error">{fieldError}</p>}

                    {variable.used_by && variable.used_by.length > 0 && (
                      <span className={styles.usedBy}>Used by: {variable.used_by.join(', ')}</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {optionalVariables.length > 0 && (
          <div className={styles.section}>
            <h4 className={styles.sectionTitle}>Optional Inputs</h4>
            <div className={styles.fields}>
              {optionalVariables.map((variable) => {
                const fieldError = getFieldError(variable.name);
                const showError = touched[variable.name] && fieldError;

                return (
                  <div key={variable.name} className={styles.fieldGroup}>
                    <VariableField
                      variable={variable}
                      value={values[variable.name] || ''}
                      onChange={(value) => handleChange(variable.name, value)}
                      onBlur={() => handleBlur(variable.name)}
                      hasError={!!showError}
                      fileInputRef={{ current: fileInputRefs.current[variable.name] || null }}
                      onFileRemove={() => handleFileRemove(variable.name)}
                    />

                    {variable.description && !showError && (
                      <p className="field-helper">{variable.description}</p>
                    )}

                    {showError && <p className="field-error">{fieldError}</p>}

                    {variable.used_by && variable.used_by.length > 0 && (
                      <span className={styles.usedBy}>Used by: {variable.used_by.join(', ')}</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className={styles.actions}>
          <button type="button" className="btn btn-black-and-white btn-outline" onClick={onCancel}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary btn-highlight">
            <Play size={16} />
            Start Run
          </button>
        </div>
      </form>
    </div>
  );
}
