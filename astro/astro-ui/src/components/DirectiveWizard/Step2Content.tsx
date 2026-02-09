'use client';

import { ContentViewer } from '@/components/ContentViewer';
import { ContentEditor } from '@/components/ContentEditor';
import styles from './DirectiveWizard.module.scss';

export interface Step2Data {
  content: string;
}

interface Step2ContentProps {
  data: Step2Data;
  onChange: (data: Step2Data) => void;
  errors: Partial<Record<keyof Step2Data, string>>;
}

export default function Step2Content({ data, onChange, errors }: Step2ContentProps) {
  return (
    <div className={styles.stepContent}>
      <h2 className={styles.stepTitle}>Directive Content</h2>
      <p className={styles.stepDescription}>
        Write your prompt template. Use @variable:name syntax for dynamic values, @probe:name for probe references,
        and @directive:id for directive references. Type @ to see autocomplete suggestions.
      </p>

      <div className={styles.field}>
        <label className={styles.fieldLabel}>
          Content
          <span className={styles.fieldRequired}>*</span>
        </label>
        <ContentEditor
          value={data.content}
          onChange={(content) => onChange({ ...data, content })}
          error={!!errors.content}
          className={styles.contentTextarea}
          placeholder="You are a helpful assistant that will @variable:task_type the provided code.

Requirements:
- @variable:requirements

Use @probe:code_analyzer to understand the codebase.
Follow guidelines from @directive:coding-standards."
        />
        {errors.content && <p className={styles.fieldError}>{errors.content}</p>}
        <p className={styles.fieldHint}>
          Variables will be extracted automatically and configurable in the next step. Type @ for autocomplete.
        </p>
      </div>

      {data.content && (
        <div className={styles.contentPreview}>
          <p className={styles.previewLabel}>Preview</p>
          <ContentViewer content={data.content} />
        </div>
      )}
    </div>
  );
}
