'use client';

import type { UIHint } from '@/types/astro';
import styles from './DirectiveWizard.module.scss';

export interface ExtractedVariable {
  name: string;
  description: string;
  required: boolean;
  default: string;
  ui_hint: UIHint;
  ui_options: Record<string, unknown>;
}

export interface Step3Data {
  variables: ExtractedVariable[];
}

interface Step3VariablesProps {
  content: string;
  data: Step3Data;
  onChange: (data: Step3Data) => void;
}

const UI_HINT_OPTIONS: { value: UIHint; label: string }[] = [
  { value: 'text', label: 'Text Input' },
  { value: 'textarea', label: 'Text Area' },
  { value: 'number', label: 'Number' },
  { value: 'date', label: 'Date Picker' },
  { value: 'select', label: 'Dropdown Select' },
  { value: 'file', label: 'File Upload' },
];

export function extractVariables(content: string): string[] {
  const regex = /@variable:([a-zA-Z0-9_-]+)/g;
  const variables = new Set<string>();
  let match;
  while ((match = regex.exec(content)) !== null) {
    variables.add(match[1]);
  }
  return Array.from(variables);
}

export default function Step3Variables({ content, data, onChange }: Step3VariablesProps) {
  const extractedNames = extractVariables(content);

  // Sync extracted variables with data.variables
  const syncedVariables = extractedNames.map((name) => {
    const existing = data.variables.find((v) => v.name === name);
    return existing || {
      name,
      description: '',
      required: true,
      default: '',
      ui_hint: 'text' as UIHint,
      ui_options: {},
    };
  });

  // Only update if the variables have changed
  const currentNames = data.variables.map((v) => v.name).sort().join(',');
  const newNames = extractedNames.sort().join(',');
  if (currentNames !== newNames) {
    onChange({ variables: syncedVariables });
  }

  const updateVariable = (index: number, updates: Partial<ExtractedVariable>) => {
    const newVariables = [...syncedVariables];
    newVariables[index] = { ...newVariables[index], ...updates };
    onChange({ variables: newVariables });
  };

  if (extractedNames.length === 0) {
    return (
      <div className={styles.stepContent}>
        <h2 className={styles.stepTitle}>Configure Variables</h2>
        <p className={styles.stepDescription}>
          Variables allow users to customize directive behavior at runtime.
        </p>
        <div className={styles.noVariables}>
          No variables found in your content. Add variables using @variable:name syntax in the previous step.
        </div>
      </div>
    );
  }

  return (
    <div className={styles.stepContent}>
      <h2 className={styles.stepTitle}>Configure Variables</h2>
      <p className={styles.stepDescription}>
        Configure how each variable should be displayed and handled. Found {extractedNames.length} variable{extractedNames.length !== 1 ? 's' : ''}.
      </p>

      <div className={styles.variablesList}>
        {syncedVariables.map((variable, index) => (
          <div key={variable.name} className={styles.variableItem}>
            <div className={styles.variableHeader}>
              <span className={styles.variableName}>@{variable.name}</span>
            </div>

            <div className={styles.variableFields}>
              <div className={styles.field}>
                <label className={styles.fieldLabel}>Description</label>
                <input
                  type="text"
                  className="input"
                  value={variable.description}
                  onChange={(e) => updateVariable(index, { description: e.target.value })}
                  placeholder="Describe what this variable is for..."
                />
              </div>

              <div className={styles.field}>
                <label className={styles.fieldLabel}>Input Type</label>
                <select
                  className="select"
                  value={variable.ui_hint}
                  onChange={(e) => updateVariable(index, { ui_hint: e.target.value as UIHint })}
                >
                  {UI_HINT_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.field}>
                <label className={styles.fieldLabel}>Default Value</label>
                <input
                  type="text"
                  className="input"
                  value={variable.default}
                  onChange={(e) => updateVariable(index, { default: e.target.value })}
                  placeholder="Optional default value..."
                />
              </div>

              <div className={styles.field}>
                <label className={styles.fieldLabel}>
                  <input
                    type="checkbox"
                    className="checkbox"
                    checked={variable.required}
                    onChange={(e) => updateVariable(index, { required: e.target.checked })}
                  />
                  {' '}Required field
                </label>
              </div>

              {variable.ui_hint === 'select' && (
                <div className={styles.field} style={{ gridColumn: '1 / -1' }}>
                  <label className={styles.fieldLabel}>Options (comma-separated)</label>
                  <input
                    type="text"
                    className="input"
                    value={(variable.ui_options.options as string[])?.join(', ') || ''}
                    onChange={(e) => updateVariable(index, {
                      ui_options: {
                        ...variable.ui_options,
                        options: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                      },
                    })}
                    placeholder="Option 1, Option 2, Option 3"
                  />
                </div>
              )}

              {variable.ui_hint === 'number' && (
                <>
                  <div className={styles.field}>
                    <label className={styles.fieldLabel}>Min</label>
                    <input
                      type="number"
                      className="input"
                      value={variable.ui_options.min as number || ''}
                      onChange={(e) => updateVariable(index, {
                        ui_options: {
                          ...variable.ui_options,
                          min: e.target.value ? Number(e.target.value) : undefined,
                        },
                      })}
                    />
                  </div>
                  <div className={styles.field}>
                    <label className={styles.fieldLabel}>Max</label>
                    <input
                      type="number"
                      className="input"
                      value={variable.ui_options.max as number || ''}
                      onChange={(e) => updateVariable(index, {
                        ui_options: {
                          ...variable.ui_options,
                          max: e.target.value ? Number(e.target.value) : undefined,
                        },
                      })}
                    />
                  </div>
                </>
              )}

              {variable.ui_hint === 'file' && (
                <div className={styles.field} style={{ gridColumn: '1 / -1' }}>
                  <label className={styles.fieldLabel}>Accepted file types</label>
                  <input
                    type="text"
                    className="input"
                    value={(variable.ui_options.accept as string) || ''}
                    onChange={(e) => updateVariable(index, {
                      ui_options: {
                        ...variable.ui_options,
                        accept: e.target.value,
                      },
                    })}
                    placeholder=".pdf,.doc,.docx"
                  />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
