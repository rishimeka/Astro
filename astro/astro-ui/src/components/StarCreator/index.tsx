'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Star as StarIcon,
  Brain,
  PlayCircle,
  FileSearch,
  CheckCircle,
  Hammer,
  Layers,
  Settings,
  Check,
} from 'lucide-react';
import { useDirectives } from '@/hooks/useDirectives';
import { useProbes } from '@/hooks/useProbes';
import { useStarMutations } from '@/hooks/useStars';
import { Spinner } from '@/components/Loading';
import { StarType } from '@/types/astro';
import styles from './StarCreator.module.scss';

interface FormState {
  name: string;
  type: StarType | '';
  directive_id: string;
  probe_ids: string[];
  config: string;
}

interface FormErrors {
  name?: string;
  type?: string;
  directive_id?: string;
  config?: string;
}

const STAR_TYPES: {
  value: StarType;
  label: string;
  description: string;
  icon: React.ComponentType<{ size?: number }>;
}[] = [
  { value: StarType.WORKER, label: 'Worker', description: 'Executes tasks with tools', icon: Hammer },
  { value: StarType.PLANNING, label: 'Planning', description: 'Creates execution plans', icon: Brain },
  { value: StarType.EVAL, label: 'Eval', description: 'Evaluates conditions', icon: CheckCircle },
  { value: StarType.SYNTHESIS, label: 'Synthesis', description: 'Combines results', icon: Layers },
  { value: StarType.EXECUTION, label: 'Execution', description: 'Runs parallel tasks', icon: PlayCircle },
  { value: StarType.DOCEX, label: 'DocEx', description: 'Extracts documents', icon: FileSearch },
];

function generateId(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    || `star-${Date.now()}`;
}

function needsProbes(type: StarType | ''): boolean {
  if (!type) return false;
  return [StarType.WORKER, StarType.PLANNING, StarType.EVAL, StarType.SYNTHESIS].includes(type as StarType);
}

export default function StarCreator() {
  const router = useRouter();
  const { directives, isLoading: directivesLoading } = useDirectives();
  const { probes, isLoading: probesLoading } = useProbes();
  const { createStar, isSubmitting } = useStarMutations();

  const [formState, setFormState] = useState<FormState>({
    name: '',
    type: '',
    directive_id: '',
    probe_ids: [],
    config: '{}',
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);

  const updateField = <K extends keyof FormState>(field: K, value: FormState[K]) => {
    setFormState((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const toggleProbe = (probeName: string) => {
    setFormState((prev) => ({
      ...prev,
      probe_ids: prev.probe_ids.includes(probeName)
        ? prev.probe_ids.filter((id) => id !== probeName)
        : [...prev.probe_ids, probeName],
    }));
  };

  const validate = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formState.name.trim()) {
      newErrors.name = 'Name is required';
    }
    if (!formState.type) {
      newErrors.type = 'Please select a star type';
    }
    if (!formState.directive_id) {
      newErrors.directive_id = 'Please select a directive';
    }

    // Validate JSON config
    if (formState.config) {
      try {
        JSON.parse(formState.config);
      } catch {
        newErrors.config = 'Invalid JSON format';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    setSubmitError(null);

    if (!validate()) return;

    try {
      const id = generateId(formState.name);
      const config = formState.config ? JSON.parse(formState.config) : {};

      await createStar({
        id,
        name: formState.name.trim(),
        type: formState.type as StarType,
        directive_id: formState.directive_id,
        probe_ids: needsProbes(formState.type) ? formState.probe_ids : undefined,
        config,
      });

      router.push(`/stars/${id}`);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to create star');
    }
  };

  const isLoading = directivesLoading || probesLoading;

  return (
    <div className={styles.creator}>
      {/* Error Banner */}
      {submitError && <div className={styles.errorBanner}>{submitError}</div>}

      {/* Basic Info */}
      <div className={styles.formCard}>
        <h3 className={styles.sectionTitle}>
          <StarIcon size={18} />
          Star Configuration
        </h3>

        <div className={styles.field}>
          <label className={styles.fieldLabel}>
            Name
            <span className={styles.fieldRequired}>*</span>
          </label>
          <input
            type="text"
            className={`input ${errors.name ? 'input-error' : ''}`}
            value={formState.name}
            onChange={(e) => updateField('name', e.target.value)}
            placeholder="e.g., Code Review Worker"
          />
          {errors.name && <p className={styles.fieldError}>{errors.name}</p>}
        </div>

        <div className={styles.field}>
          <label className={styles.fieldLabel}>
            Type
            <span className={styles.fieldRequired}>*</span>
          </label>
          <div className={styles.typeGrid}>
            {STAR_TYPES.map((starType) => {
              const Icon = starType.icon;
              return (
                <button
                  key={starType.value}
                  type="button"
                  className={`${styles.typeOption} ${
                    formState.type === starType.value ? styles.selected : ''
                  }`}
                  onClick={() => updateField('type', starType.value)}
                >
                  <div className={styles.typeIcon}>
                    <Icon size={20} />
                  </div>
                  <span className={styles.typeName}>{starType.label}</span>
                  <span className={styles.typeDescription}>{starType.description}</span>
                </button>
              );
            })}
          </div>
          {errors.type && <p className={styles.fieldError}>{errors.type}</p>}
        </div>

        <div className={styles.field}>
          <label className={styles.fieldLabel}>
            Directive
            <span className={styles.fieldRequired}>*</span>
          </label>
          {isLoading ? (
            <div className={styles.loadingState}>
              <Spinner size="sm" />
              Loading directives...
            </div>
          ) : (
            <select
              className={`select ${errors.directive_id ? 'select-error' : ''}`}
              value={formState.directive_id}
              onChange={(e) => updateField('directive_id', e.target.value)}
            >
              <option value="">Select a directive...</option>
              {directives.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          )}
          {errors.directive_id && <p className={styles.fieldError}>{errors.directive_id}</p>}
          <p className={styles.fieldHint}>
            The directive defines the prompt template for this star.
          </p>
        </div>
      </div>

      {/* Probes (only for atomic stars) */}
      {needsProbes(formState.type) && (
        <div className={styles.formCard}>
          <h3 className={styles.sectionTitle}>
            <Settings size={18} />
            Probes
          </h3>
          <p className={styles.fieldHint} style={{ marginTop: '-12px', marginBottom: '16px' }}>
            Select probes that this star can use as tools.
          </p>

          {isLoading ? (
            <div className={styles.loadingState}>
              <Spinner size="sm" />
              Loading probes...
            </div>
          ) : probes.length === 0 ? (
            <div className={styles.noProbes}>
              No probes available. Create probes first or continue without them.
            </div>
          ) : (
            <div className={styles.probeList}>
              {probes.map((probe) => (
                <label
                  key={probe.name}
                  className={`${styles.probeItem} ${
                    formState.probe_ids.includes(probe.name) ? styles.selected : ''
                  }`}
                >
                  <input
                    type="checkbox"
                    className={`checkbox ${styles.probeCheckbox}`}
                    checked={formState.probe_ids.includes(probe.name)}
                    onChange={() => toggleProbe(probe.name)}
                  />
                  <div className={styles.probeInfo}>
                    <div className={styles.probeName}>{probe.name}</div>
                    <div className={styles.probeDescription}>{probe.description}</div>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Config */}
      <div className={styles.formCard}>
        <h3 className={styles.sectionTitle}>
          <Settings size={18} />
          Configuration (Optional)
        </h3>

        <div className={styles.field}>
          <label className={styles.fieldLabel}>Config JSON</label>
          <textarea
            className={`textarea ${styles.configEditor} ${errors.config ? 'textarea-error' : ''}`}
            value={formState.config}
            onChange={(e) => updateField('config', e.target.value)}
            placeholder="{}"
          />
          {errors.config && <p className={styles.fieldError}>{errors.config}</p>}
          <p className={styles.fieldHint}>
            Additional configuration options in JSON format.
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className={styles.actions}>
        <button
          type="button"
          className="btn btn-black-and-white btn-outline"
          onClick={() => router.push('/stars')}
          disabled={isSubmitting}
        >
          Cancel
        </button>
        <button
          type="button"
          className="btn btn-primary btn-highlight"
          onClick={handleSubmit}
          disabled={isSubmitting || isLoading}
        >
          {isSubmitting ? (
            <>
              <Spinner size="sm" />
              Creating...
            </>
          ) : (
            <>
              <Check size={16} />
              Create Star
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export { StarCreator };
