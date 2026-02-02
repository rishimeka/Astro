'use client';

import { Settings, Star, Play, Square } from 'lucide-react';
import { PropertiesPanelProps, StarNodeData } from './types';
import styles from './PropertiesPanel.module.scss';

export function PropertiesPanel({ selectedNode, onUpdateNode }: PropertiesPanelProps) {
  // No node selected
  if (!selectedNode) {
    return (
      <div className={styles.panel}>
        <div className={styles.header}>
          <Settings size={16} />
          <span>Node Properties</span>
        </div>
        <div className={styles.emptyState}>
          <p>Select a node to edit its properties</p>
        </div>
      </div>
    );
  }

  // Start or End node selected (read-only info)
  if (selectedNode.type === 'start' || selectedNode.type === 'end') {
    const Icon = selectedNode.type === 'start' ? Play : Square;
    const label = selectedNode.type === 'start' ? 'Start Node' : 'End Node';

    return (
      <div className={styles.panel}>
        <div className={styles.header}>
          <Icon size={16} />
          <span>{label}</span>
        </div>
        <div className={styles.content}>
          <p className={styles.info}>
            {selectedNode.type === 'start'
              ? 'The entry point of the workflow. All executions begin here.'
              : 'The exit point of the workflow. Execution completes when this node is reached.'}
          </p>
        </div>
      </div>
    );
  }

  // Star node selected - show editable properties
  const data = selectedNode.data as StarNodeData;

  const handleDisplayNameChange = (value: string) => {
    if (onUpdateNode) {
      onUpdateNode(selectedNode.id, { displayName: value || undefined });
    }
  };

  const handleConfirmationToggle = (checked: boolean) => {
    if (onUpdateNode) {
      onUpdateNode(selectedNode.id, {
        requiresConfirmation: checked,
        confirmationPrompt: checked ? data.confirmationPrompt : undefined,
      });
    }
  };

  const handleConfirmationPromptChange = (value: string) => {
    if (onUpdateNode) {
      onUpdateNode(selectedNode.id, { confirmationPrompt: value || undefined });
    }
  };

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <Star size={16} />
        <span>Node Properties</span>
      </div>

      <div className={styles.content}>
        {/* Node Info (read-only) */}
        <div className={styles.section}>
          <h4 className={styles.sectionTitle}>Star</h4>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Name</span>
            <span className={styles.infoValue}>{data.starName}</span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Type</span>
            <span className={styles.infoValue}>{data.starType}</span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Directive</span>
            <span className={styles.infoValue}>{data.directiveName}</span>
          </div>
        </div>

        {/* Editable Properties */}
        <div className={styles.section}>
          <h4 className={styles.sectionTitle}>Display</h4>
          <div className={styles.field}>
            <label className={styles.fieldLabel}>Display Name</label>
            <input
              type="text"
              className="input"
              placeholder={data.starName}
              defaultValue={data.displayName || ''}
              onBlur={(e) => handleDisplayNameChange(e.target.value)}
              key={`displayName-${selectedNode.id}`}
            />
            <span className={styles.fieldHint}>
              Optional custom name shown in the graph
            </span>
          </div>
        </div>

        <div className={styles.section}>
          <h4 className={styles.sectionTitle}>Execution</h4>
          <div className={styles.field}>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={data.requiresConfirmation || false}
                onChange={(e) => handleConfirmationToggle(e.target.checked)}
              />
              <span>Require confirmation before execution</span>
            </label>
            <span className={styles.fieldHint}>
              Pause execution and wait for user approval
            </span>
          </div>

          {data.requiresConfirmation && (
            <div className={styles.field}>
              <label className={styles.fieldLabel}>Confirmation Prompt</label>
              <textarea
                className="textarea"
                placeholder="Enter confirmation message..."
                defaultValue={data.confirmationPrompt || ''}
                onBlur={(e) => handleConfirmationPromptChange(e.target.value)}
                rows={3}
                key={`confirmationPrompt-${selectedNode.id}`}
              />
              <span className={styles.fieldHint}>
                Message shown when asking for confirmation
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
