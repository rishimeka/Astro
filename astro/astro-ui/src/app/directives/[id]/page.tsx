'use client';

import { useState, use, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Edit2, Trash2, Save, X, FileText, Settings, Tag } from 'lucide-react';
import PageHeader from '@/components/PageHeader/PageHeader';
import { ContentViewer } from '@/components/ContentViewer';
import { DeleteConfirmModal } from '@/components/DeleteConfirmModal';
import { Spinner, PageLoader } from '@/components/Loading';
import { useDirective } from '@/hooks/useDirectives';
import { api } from '@/lib/api/client';
import { ENDPOINTS } from '@/lib/api/endpoints';
import styles from './page.module.scss';

interface DirectiveDetailProps {
  params: Promise<{ id: string }>;
}

export default function DirectiveDetailPage({ params }: DirectiveDetailProps) {
  const { id } = use(params);
  const router = useRouter();
  const { directive, isLoading, error } = useDirective(id);

  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Edit form state
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editContent, setEditContent] = useState('');

  // Initialize edit form when directive loads
  useEffect(() => {
    if (directive) {
      setEditName(directive.name);
      setEditDescription(directive.description);
      setEditContent(directive.content);
    }
  }, [directive]);

  if (isLoading) {
    return <PageLoader message="Loading directive..." />;
  }

  if (error || !directive) {
    return (
      <div className={styles.errorContainer}>
        <h2>Directive Not Found</h2>
        <p>The directive with ID &quot;{id}&quot; does not exist.</p>
        {error && <p className={styles.errorMessage}>{error}</p>}
        <Link href="/directives" className="btn btn-primary btn-outline">
          Back to Directives
        </Link>
      </div>
    );
  }

  const handleEdit = () => {
    setEditName(directive.name);
    setEditDescription(directive.description);
    setEditContent(directive.content);
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await api.put(ENDPOINTS.DIRECTIVE(id), {
        name: editName,
        description: editDescription,
        content: editContent,
      });
      // In a real app, we'd refetch or update state
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to save directive:', error);
      alert('Failed to save directive. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.delete(ENDPOINTS.DIRECTIVE(id));
      router.push('/directives');
    } catch (error) {
      console.error('Failed to delete directive:', error);
      alert('Failed to delete directive. Please try again.');
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  // Probe IDs are the probe names
  const probeNames = directive.probe_ids;

  return (
    <div className={styles.page}>
      <PageHeader
        title={isEditing ? 'Edit Directive' : directive.name}
        subtitle={isEditing ? undefined : directive.description}
        breadcrumbs={[
          { label: 'Directives', href: '/directives' },
          { label: directive.name },
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
              <Link href="/directives" className="btn btn-black-and-white btn-outline">
                <ArrowLeft size={16} />
                Back
              </Link>
            </div>
          )
        }
      />

      {/* Metadata tags row - only in view mode */}
      {!isEditing && Object.keys(directive.metadata).length > 0 && (
        <div className={styles.metadataTags}>
          {'version' in directive.metadata && directive.metadata.version != null && (
            <span className={styles.metadataTag}>
              <span className={styles.metadataLabel}>v</span>
              {String(directive.metadata.version)}
            </span>
          )}
          {'tags' in directive.metadata && Array.isArray(directive.metadata.tags) && (
            (directive.metadata.tags as string[]).map((tag: string) => (
              <span key={tag} className={styles.metadataTag}>{tag}</span>
            ))
          )}
          {'category' in directive.metadata && directive.metadata.category != null && (
            <span className={styles.metadataTag}>{String(directive.metadata.category)}</span>
          )}
        </div>
      )}

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
              <div className={styles.field}>
                <label className={styles.fieldLabel}>Description</label>
                <input
                  type="text"
                  className="input"
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                />
              </div>
            </section>

            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>
                <FileText size={18} />
                Content
              </h3>
              <textarea
                className={`textarea ${styles.contentTextarea}`}
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                rows={15}
              />
              <p className={styles.hint}>
                Use @probe:name, @directive:id, and @variable:name to reference probes, directives, and variables.
              </p>
            </section>
          </>
        ) : (
          // View Mode
          <>
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>
                <FileText size={18} />
                Content
              </h3>
              <ContentViewer content={directive.content} />
            </section>

            {directive.template_variables.length > 0 && (
              <section className={styles.section}>
                <h3 className={styles.sectionTitle}>
                  <Settings size={18} />
                  Template Variables
                </h3>
                <div className={styles.variables}>
                  {directive.template_variables.map((variable) => (
                    <div key={variable.name} className={styles.variable}>
                      <div className={styles.variableHeader}>
                        <code className={styles.variableName}>{variable.name}</code>
                        {variable.required && (
                          <span className={styles.requiredBadge}>required</span>
                        )}
                        {variable.ui_hint && (
                          <span className={styles.hintBadge}>{variable.ui_hint}</span>
                        )}
                      </div>
                      <p className={styles.variableDesc}>{variable.description}</p>
                      {variable.default && (
                        <p className={styles.variableDefault}>
                          Default: <code>{variable.default}</code>
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {probeNames.length > 0 && (
              <section className={styles.section}>
                <h3 className={styles.sectionTitle}>
                  <Tag size={18} />
                  Probes Used
                </h3>
                <div className={styles.probeList}>
                  {probeNames.map((name) => (
                    <Link
                      key={name}
                      href={`/probes/${encodeURIComponent(name)}`}
                      className={styles.probeLink}
                    >
                      {name}
                    </Link>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>

      <DeleteConfirmModal
        isOpen={showDeleteModal}
        title="Delete Directive"
        message={`Are you sure you want to delete "${directive.name}"? This action cannot be undone. Stars using this directive will be affected.`}
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteModal(false)}
        isDeleting={isDeleting}
      />
    </div>
  );
}
