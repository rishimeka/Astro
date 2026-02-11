'use client';

import { useState, useMemo } from 'react';
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
  Search,
  Tag,
} from 'lucide-react';
import { useDirectives } from '@/hooks/useDirectives';
import { useProbes } from '@/hooks/useProbes';
import { useStarMutations } from '@/hooks/useStars';
import { Spinner } from '@/components/Loading';
import { KeyValueEditor } from '@/components/KeyValueEditor';
import { StarType, Probe } from '@/types/astro';
import styles from './StarCreator.module.scss';

// Extract tag from probe name (e.g., "fetch_google_news_headlines" → "google_news")
function extractProbeTag(name: string): string {
  // Remove common prefixes like "fetch_", "get_", "search_", etc.
  const withoutPrefix = name.replace(/^(fetch_|get_|search_|find_|list_|read_|write_|create_|update_|delete_)/, '');

  // Get the first two parts as the tag (e.g., "google_news_headlines" → "google_news")
  const parts = withoutPrefix.split('_');
  if (parts.length >= 2) {
    return parts.slice(0, 2).join('_');
  }
  return parts[0] || 'other';
}

interface FormState {
  name: string;
  type: StarType | '';
  directive_id: string;
  probe_ids: string[];
  config: Record<string, unknown>;
}

interface FormErrors {
  name?: string;
  type?: string;
  directive_id?: string;
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
    config: {},
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Probe filtering
  const [probeSearch, setProbeSearch] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  // Extract unique tags from all probes
  const probeTags = useMemo(() => {
    const tags = new Set<string>();
    probes.forEach((probe) => {
      tags.add(extractProbeTag(probe.name));
    });
    return Array.from(tags).sort();
  }, [probes]);

  // Filter probes based on search and selected tags
  const filteredProbes = useMemo(() => {
    return probes.filter((probe) => {
      // Search filter
      const searchLower = probeSearch.toLowerCase();
      const matchesSearch =
        !probeSearch ||
        probe.name.toLowerCase().includes(searchLower) ||
        probe.description.toLowerCase().includes(searchLower);

      // Tag filter
      const probeTag = extractProbeTag(probe.name);
      const matchesTags = selectedTags.length === 0 || selectedTags.includes(probeTag);

      return matchesSearch && matchesTags;
    });
  }, [probes, probeSearch, selectedTags]);

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

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

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    setSubmitError(null);

    if (!validate()) return;

    try {
      const id = generateId(formState.name);

      await createStar({
        id,
        name: formState.name.trim(),
        type: formState.type as StarType,
        directive_id: formState.directive_id,
        probe_ids: needsProbes(formState.type) ? formState.probe_ids : undefined,
        config: formState.config,
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
            <>
              {/* Filter Bar */}
              <div className={styles.probeFilters}>
                <div className={styles.probeSearchWrapper}>
                  <Search size={16} className={styles.probeSearchIcon} />
                  <input
                    type="text"
                    className={`input ${styles.probeSearchInput}`}
                    value={probeSearch}
                    onChange={(e) => setProbeSearch(e.target.value)}
                    placeholder="Search probes..."
                  />
                </div>

                {probeTags.length > 0 && (
                  <div className={styles.probeTags}>
                    <Tag size={14} className={styles.probeTagIcon} />
                    {probeTags.map((tag) => (
                      <button
                        key={tag}
                        type="button"
                        className={`${styles.probeTagChip} ${
                          selectedTags.includes(tag) ? styles.selected : ''
                        }`}
                        onClick={() => toggleTag(tag)}
                      >
                        {tag.replace(/_/g, ' ')}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Probe List */}
              {filteredProbes.length === 0 ? (
                <div className={styles.noProbes}>
                  No probes match your filters.
                </div>
              ) : (
                <div className={styles.probeList}>
                  {filteredProbes.map((probe) => (
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

              {formState.probe_ids.length > 0 && (
                <div className={styles.probeSelectedCount}>
                  {formState.probe_ids.length} probe{formState.probe_ids.length !== 1 ? 's' : ''} selected
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Config */}
      <div className={styles.formCard}>
        <h3 className={styles.sectionTitle}>
          <Settings size={18} />
          Configuration (Optional)
        </h3>

        <KeyValueEditor
          value={formState.config}
          onChange={(value) => updateField('config', value)}
        />
        <p className={styles.fieldHint}>
          Add configuration options like temperature, max_tokens, etc.
        </p>
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
