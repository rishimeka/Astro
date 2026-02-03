'use client';

import { useState, use, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Edit2,
  Trash2,
  Save,
  X,
  Settings,
  FileText,
  Cpu,
  Sparkles,
  Tag,
} from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { MetadataPanel } from '@/components/MetadataPanel';
import { DeleteConfirmModal } from '@/components/DeleteConfirmModal';
import { Spinner, PageLoader } from '@/components/Loading';
import { useStar } from '@/hooks/useStars';
import { useDirective } from '@/hooks/useDirectives';
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

export default function StarDetailPage({ params }: StarDetailProps) {
  const { id } = use(params);
  const router = useRouter();
  const { star, isLoading, error } = useStar(id);
  const { directive } = useDirective(star?.directive_id || null);

  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Edit form state
  const [editName, setEditName] = useState('');
  const [editConfig, setEditConfig] = useState('{}');

  // Initialize edit form when star loads
  useEffect(() => {
    if (star) {
      setEditName(star.name);
      setEditConfig(star.config ? JSON.stringify(star.config, null, 2) : '{}');
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
    setEditConfig(JSON.stringify(star.config, null, 2));
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
  };

  const handleSave = async () => {
    // Validate JSON config
    let parsedConfig;
    try {
      parsedConfig = JSON.parse(editConfig);
    } catch {
      alert('Invalid JSON in config field');
      return;
    }

    setIsSaving(true);
    try {
      await api.put(ENDPOINTS.STAR(id), {
        name: editName,
        config: parsedConfig,
      });
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

  // Get probe IDs if star has them
  const probeIds = 'probe_ids' in star ? (star.probe_ids as string[]) : [];

  return (
    <div className={styles.page}>
      <PageHeader
        title={isEditing ? 'Edit Star' : star.name}
        subtitle={isEditing ? undefined : `${starTypeLabels[star.type]} Star`}
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
                className="btn btn-black-and-white btn-outline"
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
              <Link href="/stars" className="btn btn-black-and-white btn-outline">
                <ArrowLeft size={16} />
                Back
              </Link>
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
              <textarea
                className={`textarea ${styles.configTextarea}`}
                value={editConfig}
                onChange={(e) => setEditConfig(e.target.value)}
                rows={10}
                placeholder="{}"
              />
              <p className={styles.hint}>
                Configuration must be valid JSON.
              </p>
            </section>
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

            {probeIds.length > 0 && (
              <section className={styles.section}>
                <h3 className={styles.sectionTitle}>
                  <Tag size={18} />
                  Probes
                </h3>
                <div className={styles.probeList}>
                  {probeIds.map((probeId) => (
                    <Link
                      key={probeId}
                      href={`/probes/${encodeURIComponent(probeId)}`}
                      className={styles.probeLink}
                    >
                      {probeId}
                    </Link>
                  ))}
                </div>
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
