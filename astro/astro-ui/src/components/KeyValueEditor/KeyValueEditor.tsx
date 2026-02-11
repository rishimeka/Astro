'use client';

import { useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import styles from './KeyValueEditor.module.scss';

interface KeyValuePair {
  key: string;
  value: string;
  type: 'string' | 'number' | 'boolean';
}

export interface KeyValueEditorProps {
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
  className?: string;
}

function detectType(value: unknown): 'string' | 'number' | 'boolean' {
  if (typeof value === 'boolean') return 'boolean';
  if (typeof value === 'number') return 'number';
  return 'string';
}

function parseValue(value: string, type: 'string' | 'number' | 'boolean'): unknown {
  if (type === 'boolean') return value === 'true';
  if (type === 'number') {
    const num = parseFloat(value);
    return isNaN(num) ? 0 : num;
  }
  return value;
}

function stringifyValue(value: unknown): string {
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return String(value);
}

export default function KeyValueEditor({ value, onChange, className = '' }: KeyValueEditorProps) {
  // Convert object to array of key-value pairs
  const pairs: KeyValuePair[] = Object.entries(value).map(([key, val]) => ({
    key,
    value: stringifyValue(val),
    type: detectType(val),
  }));

  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [newType, setNewType] = useState<'string' | 'number' | 'boolean'>('string');

  const updatePairs = (newPairs: KeyValuePair[]) => {
    const result: Record<string, unknown> = {};
    newPairs.forEach((pair) => {
      if (pair.key.trim()) {
        result[pair.key] = parseValue(pair.value, pair.type);
      }
    });
    onChange(result);
  };

  const handleKeyChange = (index: number, newKey: string) => {
    const newPairs = [...pairs];
    newPairs[index] = { ...newPairs[index], key: newKey };
    updatePairs(newPairs);
  };

  const handleValueChange = (index: number, newValue: string) => {
    const newPairs = [...pairs];
    newPairs[index] = { ...newPairs[index], value: newValue };
    updatePairs(newPairs);
  };

  const handleTypeChange = (index: number, newType: 'string' | 'number' | 'boolean') => {
    const newPairs = [...pairs];
    // Convert value to new type
    let convertedValue = newPairs[index].value;
    if (newType === 'boolean') {
      convertedValue = newPairs[index].value === 'true' || newPairs[index].value === '1' ? 'true' : 'false';
    } else if (newType === 'number') {
      const num = parseFloat(newPairs[index].value);
      convertedValue = isNaN(num) ? '0' : String(num);
    }
    newPairs[index] = { ...newPairs[index], type: newType, value: convertedValue };
    updatePairs(newPairs);
  };

  const handleRemove = (index: number) => {
    const newPairs = pairs.filter((_, i) => i !== index);
    updatePairs(newPairs);
  };

  const handleAdd = () => {
    if (!newKey.trim()) return;

    const newPairs = [...pairs, { key: newKey, value: newValue, type: newType }];
    updatePairs(newPairs);
    setNewKey('');
    setNewValue('');
    setNewType('string');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd();
    }
  };

  return (
    <div className={`${styles.editor} ${className}`}>
      {pairs.length > 0 && (
        <div className={styles.pairsList}>
          {pairs.map((pair, index) => (
            <div key={index} className={styles.pair}>
              <input
                type="text"
                className={`input ${styles.keyInput}`}
                value={pair.key}
                onChange={(e) => handleKeyChange(index, e.target.value)}
                placeholder="Key"
              />

              {pair.type === 'boolean' ? (
                <select
                  className={`select ${styles.valueInput}`}
                  value={pair.value}
                  onChange={(e) => handleValueChange(index, e.target.value)}
                >
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
              ) : (
                <input
                  type={pair.type === 'number' ? 'number' : 'text'}
                  step={pair.type === 'number' ? 'any' : undefined}
                  className={`input ${styles.valueInput}`}
                  value={pair.value}
                  onChange={(e) => handleValueChange(index, e.target.value)}
                  placeholder="Value"
                />
              )}

              <select
                className={`select ${styles.typeSelect}`}
                value={pair.type}
                onChange={(e) => handleTypeChange(index, e.target.value as 'string' | 'number' | 'boolean')}
                title="Value type"
              >
                <option value="string">Text</option>
                <option value="number">Number</option>
                <option value="boolean">Boolean</option>
              </select>

              <button
                type="button"
                className={styles.removeButton}
                onClick={() => handleRemove(index)}
                title="Remove"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className={styles.addRow}>
        <input
          type="text"
          className={`input ${styles.keyInput}`}
          value={newKey}
          onChange={(e) => setNewKey(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="New key..."
        />

        {newType === 'boolean' ? (
          <select
            className={`select ${styles.valueInput}`}
            value={newValue || 'false'}
            onChange={(e) => setNewValue(e.target.value)}
          >
            <option value="true">true</option>
            <option value="false">false</option>
          </select>
        ) : (
          <input
            type={newType === 'number' ? 'number' : 'text'}
            step={newType === 'number' ? 'any' : undefined}
            className={`input ${styles.valueInput}`}
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Value..."
          />
        )}

        <select
          className={`select ${styles.typeSelect}`}
          value={newType}
          onChange={(e) => setNewType(e.target.value as 'string' | 'number' | 'boolean')}
          title="Value type"
        >
          <option value="string">Text</option>
          <option value="number">Number</option>
          <option value="boolean">Boolean</option>
        </select>

        <button
          type="button"
          className={styles.addButton}
          onClick={handleAdd}
          disabled={!newKey.trim()}
          title="Add"
        >
          <Plus size={16} />
        </button>
      </div>

      {pairs.length === 0 && (
        <p className={styles.emptyHint}>No configuration options. Add one above.</p>
      )}
    </div>
  );
}
