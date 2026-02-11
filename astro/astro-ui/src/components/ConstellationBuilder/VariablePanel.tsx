'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { VariablePanelProps } from './types';
import styles from './VariablePanel.module.scss';

export function VariablePanel({ variables }: VariablePanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (variables.length === 0) {
    return null;
  }

  return (
    <div className={styles.panel}>
      <button
        className={styles.header}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? (
          <ChevronDown size={16} className={styles.chevron} />
        ) : (
          <ChevronRight size={16} className={styles.chevron} />
        )}
        <span className={styles.title}>Variables ({variables.length})</span>
      </button>

      {isExpanded && (
        <div className={styles.content}>
          {variables.map((variable) => (
            <div key={variable.name} className={styles.variable}>
              <div className={styles.variableHeader}>
                <span className={styles.variableName}>{variable.name}</span>
                <span
                  className={`${styles.badge} ${
                    variable.required ? styles.required : styles.optional
                  }`}
                >
                  {variable.required ? 'required' : 'optional'}
                </span>
              </div>

              {variable.description && (
                <p className={styles.description}>{variable.description}</p>
              )}

              {variable.default && (
                <div className={styles.defaultValue}>
                  Default: <code>{variable.default}</code>
                </div>
              )}

              <div className={styles.usedBy}>
                {variable.usedBy.map((usage) => (
                  <div key={usage.nodeId} className={styles.usage}>
                    <span className={styles.usagePrefix}>Used by:</span>
                    <span className={styles.usageName}>{usage.nodeName}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
