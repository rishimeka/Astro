'use client';

import { useState, use, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Edit2,
  Trash2,
  Save,
  X,
  Settings,
  FileText,
  Cpu,
  Sparkles,
  Tag,
  Search,
} from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { KeyValueEditor } from '@/components/KeyValueEditor';
import { MetadataPanel } from '@/components/MetadataPanel';
import { DeleteConfirmModal } from '@/components/DeleteConfirmModal';
import { Spinner, PageLoader } from '@/components/Loading';
import { useStar } from '@/hooks/useStars';
import { useDirective } from '@/hooks/useDirectives';
import { useProbes } from '@/hooks/useProbes';
import { api } from '@/lib/api/client';
import { ENDPOINTS } from '@/lib/api/endpoints';
import { StarType } from '@/types/astro';
import styles from './page.module.scss';

interface StarDetailProps {
  params: Promise<{ id: string }>;
}

const starTypeLabels: Record<StarType, string> = {
  [StarType.WORKER]: 'Worker',
  [StarType.PLANNING]: 'Planning',
  [StarType.EXECUTION]: 'Execution',
  [StarType.DOCEX]: 'DocEx',
  [StarType.EVAL]: 'Eval',
  [StarType.SYNTHESIS]: 'Synthesis',
};

const starTypeColors: Record<StarType, string> = {
  [StarType.WORKER]: 'var(--accent-primary)',
  [StarType.PLANNING]: 'var(--accent-secondary)',
  [StarType.EXECUTION]: 'var(--accent-success)',
  [StarType.DOCEX]: 'var(--accent-warning)',
  [StarType.EVAL]: 'var(--accent-tertiary)',
  [StarType.SYNTHESIS]: 'var(--accent-quaternary)',
};

// Atomic star types that support probe_ids
const ATOMIC_STAR_TYPES: StarType[] = [
  StarType.WORKER,
  StarType.PLANNING,
  StarType.EVAL,
  StarType.SYNTHESIS,
];

function isAtomicStarType(type: StarType): boolean {
  return ATOMIC_STAR_TYPES.includes(type);
}

// Extract tag from probe name (e.g., "fetch_google_news_headlines" → "google_news")
function extractProbeTag(name: string): string {
  const withoutPrefix = name.replace(/^(fetch_|get_|search_|find_|list_|read_|write_|create_|update_|delete_)/, '');
  const parts = withoutPrefix.split('_');
  if (parts.length >= 2) {
    return parts.slice(0, 2).join('_');
  }
  return parts[0] || 'other';
}

export default function StarDetailPage({ params }: StarDetailProps) {
  const { id } = use(params);
  const router = useRouter();
  const { star, isLoading, error } = useStar(id);
  const { directive } = useDirective(star?.directive_id || null);
  const { probes, isLoading: probesLoading } = useProbes();

  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Edit form state
  const [editName, setEditName] = useState('');
  const [editConfig, setEditConfig] = useState<Record<string, unknown>>({});
  const [editProbeIds, setEditProbeIds] = useState<string[]>([]);

  // Probe filtering state
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
      const searchLower = probeSearch.toLowerCase();
      const matchesSearch =
        !probeSearch ||
        probe.name.toLowerCase().includes(searchLower) ||
        probe.description.toLowerCase().includes(searchLower);

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

  // Initialize edit form when star loads
  useEffect(() => {
    if (star) {
      setEditName(star.name);
      setEditConfig(star.config || {});
      // Initialize probe IDs for atomic star types
      const probeIds = 'probe_ids' in star ? (star.probe_ids as string[]) : [];
      setEditProbeIds(probeIds);
    }
  }, [star]);

  if (isLoading) {
    return <PageLoader message="Loading star..." />;
  }

  if (error || !star) {
    return (
      <div className={styles.errorContainer}>
        <h2>Star Not Found</h2>
        <p>The star with ID &quot;{id}&quot; does not exist.</p>
        {error && <p className={styles.errorMessage}>{error}</p>}
        <Link href="/stars" className="btn btn-primary btn-outline">
          Back to Stars
        </Link>
      </div>
    );
  }

  const handleEdit = () => {
    setEditName(star.name);
    setEditConfig(star.config || {});
    const probeIds = 'probe_ids' in star ? (star.probe_ids as string[]) : [];
    setEditProbeIds(probeIds);
    setIsEditing(true);
  };

  const toggleProbe = (probeName: string) => {
    setEditProbeIds((prev) =>
      prev.includes(probeName)
        ? prev.filter((id) => id !== probeName)
        : [...prev, probeName]
    );
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const updatePayload: {
        name: string;
        config: Record<string, unknown>;
        probe_ids?: string[];
      } = {
        name: editName,
        config: editConfig,
      };

      // Include probe_ids for atomic star types
      if (star && isAtomicStarType(star.type)) {
        updatePayload.probe_ids = editProbeIds;
      }

      await api.put(ENDPOINTS.STAR(id), updatePayload);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to save star:', error);
      alert('Failed to save star. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.delete(ENDPOINTS.STAR(id));
      router.push('/stars');
    } catch (error) {
      console.error('Failed to delete star:', error);
      alert('Failed to delete star. Please try again.');
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  // Get probe IDs - combine directive probes with star probes
  const starProbeIds = 'probe_ids' in star ? (star.probe_ids as string[]) : [];
  const directiveProbeIds = directive?.probe_ids ?? [];

  // Combined set is the union of both (what will actually be available during execution)
  const combinedProbeIds = [...new Set([...directiveProbeIds, ...starProbeIds])];

  // Check if there are any probes to show
  const hasAnyProbes = combinedProbeIds.length > 0;

  return (
    <div className={styles.page}>
      <PageHeader
        title={isEditing ? 'Edit Star' : star.name}
        subtitle={isEditing ? undefined : `${starTypeLabels[star.type]} Star`}
        backHref="/stars"
        breadcrumbs={[
          { label: 'Stars', href: '/stars' },
          { label: star.name },
        ]}
        actions={
          isEditing ? (
            <div className={styles.actions}>
              <button
                className="btn btn-black-and-white btn-outline"
                onClick={handleCancelEdit}
                disabled={isSaving}
              >
                <X size={16} />
                Cancel
              </button>
              <button
                className="btn btn-primary btn-highlight"
                onClick={handleSave}
                disabled={isSaving}
              >
                {isSaving ? <Spinner size="sm" /> : <Save size={16} />}
                Save
              </button>
            </div>
          ) : (
            <div className={styles.actions}>
              <button
                className="btn btn-error btn-outline"
                onClick={() => setShowDeleteModal(true)}
                title="Delete"
              >
                <Trash2 size={16} />
              </button>
              <button
                className="btn btn-primary btn-outline"
                onClick={handleEdit}
              >
                <Edit2 size={16} />
                Edit
              </button>
            </div>
          )
        }
      />

      <div className={styles.content}>
        {isEditing ? (
          // Edit Mode
          <>
            <section className={styles.section}>
              <div className={styles.field}>
                <label className={styles.fieldLabel}>Name</label>
                <input
                  type="text"
                  className="input"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                />
              </div>
            </section>

            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>
                <Settings size={18} />
                Configuration
              </h3>
              <KeyValueEditor
                value={editConfig}
                onChange={setEditConfig}
              />
              <p className={styles.hint}>
                Add configuration options like temperature, max_tokens, etc.
              </p>
            </section>

            {/* Probe Selection - only for atomic star types */}
            {star && isAtomicStarType(star.type) && (
              <section className={styles.section}>
                <h3 className={styles.sectionTitle}>
                  <Tag size={18} />
                  Probes
                </h3>
                <p className={styles.hint} style={{ marginTop: '-12px', marginBottom: '16px' }}>
                  Select probes that this star can use as tools.
                </p>

                {probesLoading ? (
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
                    {/* Probe Filter Bar */}
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
                                selectedTags.includes(tag) ? styles.probeTagChipSelected : ''
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
                      <div className={styles.editProbeList}>
                        {filteredProbes.map((probe) => {
                          const isInherited = directiveProbeIds.includes(probe.name);
                          const isSelected = editProbeIds.includes(probe.name);
                          const isChecked = isInherited || isSelected;

                          return (
                            <label
                              key={probe.name}
                              className={`${styles.probeItem} ${isChecked ? styles.probeItemSelected : ''} ${isInherited ? styles.probeItemInherited : ''}`}
                            >
                              <input
                                type="checkbox"
                                className={`checkbox ${styles.probeCheckbox}`}
                                checked={isChecked}
                                disabled={isInherited}
                                onChange={() => toggleProbe(probe.name)}
                              />
                              <div className={styles.probeInfo}>
                                <div className={styles.probeName}>
                                  {probe.name}
                                  {isInherited && (
                                    <span className={styles.inheritedBadge}>Inherited</span>
                                  )}
                                </div>
                                <div className={styles.probeDescription}>{probe.description}</div>
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    )}

                    <div className={styles.probeSelectedCount}>
                      {directiveProbeIds.length > 0 && (
                        <span>{directiveProbeIds.length} inherited from directive</span>
                      )}
                      {editProbeIds.length > 0 && (
                        <span>{directiveProbeIds.length > 0 ? ' + ' : ''}{editProbeIds.length} additional</span>
                      )}
                      {directiveProbeIds.length === 0 && editProbeIds.length === 0 && (
                        <span>No probes selected</span>
                      )}
                    </div>
                  </>
                )}
              </section>
            )}
          </>
        ) : (
          // View Mode
          <>
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>
                <Cpu size={18} />
                Star Details
              </h3>
              <div className={styles.details}>
                <div className={styles.detailRow}>
                  <span className={styles.detailLabel}>Type</span>
                  <span
                    className={styles.typeBadge}
                    style={{ '--badge-color': starTypeColors[star.type] } as React.CSSProperties}
                  >
                    {starTypeLabels[star.type]}
                  </span>
                </div>
                <div className={styles.detailRow}>
                  <span className={styles.detailLabel}>ID</span>
                  <code className={styles.detailCode}>{star.id}</code>
                </div>
                <div className={styles.detailRow}>
                  <span className={styles.detailLabel}>AI Generated</span>
                  <span className={styles.detailValue}>
                    {star.ai_generated ? (
                      <span className={styles.aiGeneratedBadge}>
                        <Sparkles size={14} />
                        Yes
                      </span>
                    ) : (
                      'No'
                    )}
                  </span>
                </div>
                {'max_iterations' in star && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Max Iterations</span>
                    <span className={styles.detailValue}>{(star as { max_iterations: number }).max_iterations}</span>
                  </div>
                )}
                {'parallel' in star && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Parallel Execution</span>
                    <span className={styles.detailValue}>{(star as { parallel: boolean }).parallel ? 'Yes' : 'No'}</span>
                  </div>
                )}
              </div>
            </section>

            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>
                <FileText size={18} />
                Directive
              </h3>
              {directive ? (
                <Link href={`/directives/${directive.id}`} className={styles.directiveCard}>
                  <div className={styles.directiveName}>{directive.name}</div>
                  <div className={styles.directiveDesc}>{directive.description}</div>
                </Link>
              ) : (
                <p className={styles.emptyText}>
                  Directive not found: {star.directive_id}
                </p>
              )}
            </section>

            {hasAnyProbes && (
              <section className={styles.section}>
                <h3 className={styles.sectionTitle}>
                  <Tag size={18} />
                  Probes
                </h3>

                {/* Combined (Resolved) - what will actually be available during execution */}
                <div className={styles.probeSubsection}>
                  <h4 className={styles.probeSubsectionTitle}>
                    Combined (Resolved)
                    <span className={styles.probeCount}>{combinedProbeIds.length}</span>
                  </h4>
                  <p className={styles.probeSubsectionHint}>
                    These probes will be available during execution
                  </p>
                  <div className={styles.probeList}>
                    {combinedProbeIds.map((probeId) => {
                      const isInherited = directiveProbeIds.includes(probeId);
                      const isAdditional = starProbeIds.includes(probeId);
                      return (
                        <Link
                          key={probeId}
                          href={`/probes/${encodeURIComponent(probeId)}`}
                          className={`${styles.probeLink} ${isInherited && isAdditional ? styles.probeBoth : isInherited ? styles.probeInherited : styles.probeAdditional}`}
                          title={isInherited && isAdditional ? 'From both Directive and Star' : isInherited ? 'Inherited from Directive' : 'Added on Star'}
                        >
                          {probeId}
                        </Link>
                      );
                    })}
                  </div>
                </div>

                {/* Inherited from Directive */}
                {directiveProbeIds.length > 0 && (
                  <div className={styles.probeSubsection}>
                    <h4 className={styles.probeSubsectionTitle}>
                      <span className={styles.probeInheritedIndicator} />
                      Inherited from Directive
                      <span className={styles.probeCount}>{directiveProbeIds.length}</span>
                    </h4>
                    <div className={styles.probeList}>
                      {directiveProbeIds.map((probeId) => (
                        <Link
                          key={probeId}
                          href={`/probes/${encodeURIComponent(probeId)}`}
                          className={`${styles.probeLink} ${styles.probeInherited}`}
                        >
                          {probeId}
                        </Link>
                      ))}
                    </div>
                  </div>
                )}

                {/* Additional on Star */}
                {starProbeIds.length > 0 && (
                  <div className={styles.probeSubsection}>
                    <h4 className={styles.probeSubsectionTitle}>
                      <span className={styles.probeAdditionalIndicator} />
                      Additional on Star
                      <span className={styles.probeCount}>{starProbeIds.length}</span>
                    </h4>
                    <div className={styles.probeList}>
                      {starProbeIds.map((probeId) => (
                        <Link
                          key={probeId}
                          href={`/probes/${encodeURIComponent(probeId)}`}
                          className={`${styles.probeLink} ${styles.probeAdditional}`}
                        >
                          {probeId}
                        </Link>
                      ))}
                    </div>
                  </div>
                )}

                {/* Show loading state if directive hasn't loaded yet */}
                {!directive && star.directive_id && (
                  <p className={styles.probeLoadingHint}>
                    Loading directive probes...
                  </p>
                )}
              </section>
            )}

            {Object.keys(star.config).length > 0 && (
              <section className={styles.section}>
                <h3 className={styles.sectionTitle}>
                  <Settings size={18} />
                  Configuration
                </h3>
                <pre className={styles.configView}>
                  {JSON.stringify(star.config, null, 2)}
                </pre>
              </section>
            )}

            {Object.keys(star.metadata).length > 0 && (
              <section className={styles.section}>
                <h3 className={styles.sectionTitle}>Metadata</h3>
                <MetadataPanel metadata={star.metadata} />
              </section>
            )}
          </>
        )}
      </div>

      <DeleteConfirmModal
        isOpen={showDeleteModal}
        title="Delete Star"
        message={`Are you sure you want to delete "${star.name}"? This action cannot be undone. Constellations using this star will be affected.`}
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteModal(false)}
        isDeleting={isDeleting}
      />
    </div>
  );
}
