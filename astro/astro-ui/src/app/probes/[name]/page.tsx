'use client';

import { use } from 'react';
import Link from 'next/link';
import { ArrowLeft, Settings, FileText } from 'lucide-react';
import PageHeader from '@/components/PageHeader/PageHeader';
import { PageLoader } from '@/components/Loading';
import { useProbe } from '@/hooks/useProbes';
import styles from './page.module.scss';

interface ProbeDetailProps {
  params: Promise<{ name: string }>;
}

export default function ProbeDetailPage({ params }: ProbeDetailProps) {
  const { name } = use(params);
  const decodedName = decodeURIComponent(name);
  const { probe, isLoading, error } = useProbe(decodedName);

  if (isLoading) {
    return <PageLoader message="Loading probe..." />;
  }

  if (error || !probe) {
    return (
      <div className={styles.errorContainer}>
        <h2>Probe Not Found</h2>
        <p>The probe &quot;{decodedName}&quot; does not exist.</p>
        {error && <p className={styles.errorMessage}>{error}</p>}
        <Link href="/probes" className="btn btn-primary btn-outline">
          Back to Probes
        </Link>
      </div>
    );
  }

  // Build metadata for display
  const parameterEntries = Object.entries(probe.parameters || {}).map(([key, value]) => {
    const param = value as { type?: string; required?: boolean; default?: unknown; items?: string };
    let typeStr = param.type || 'unknown';
    if (param.type === 'array' && param.items) {
      typeStr = `array<${param.items}>`;
    }
    return [key, {
      type: typeStr,
      required: param.required ?? false,
      default: param.default,
    }];
  });

  return (
    <div className={styles.page}>
      <PageHeader
        title={probe.name}
        subtitle="Probe (Read-only from API)"
        breadcrumbs={[
          { label: 'Probes', href: '/probes' },
          { label: probe.name },
        ]}
        actions={
          <Link href="/probes" className="btn btn-black-and-white btn-outline">
            <ArrowLeft size={16} />
            Back
          </Link>
        }
      />

      <div className={styles.content}>
        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>
            <FileText size={18} />
            Description
          </h3>
          <p className={styles.description}>{probe.description}</p>
        </section>

        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>
            <Settings size={18} />
            Parameters
          </h3>
          {parameterEntries.length === 0 ? (
            <p className={styles.emptyText}>No parameters defined</p>
          ) : (
            <div className={styles.parameters}>
              {parameterEntries.map(([key, value]) => {
                const param = value as { type: string; required: boolean; default?: unknown };
                return (
                  <div key={key as string} className={styles.parameter}>
                    <div className={styles.paramHeader}>
                      <code className={styles.paramName}>{key as string}</code>
                      {param.required && (
                        <span className={styles.requiredBadge}>required</span>
                      )}
                    </div>
                    <div className={styles.paramDetails}>
                      <span className={styles.paramType}>{param.type}</span>
                      {param.default !== undefined && (
                        <span className={styles.paramDefault}>
                          default: <code>{JSON.stringify(param.default)}</code>
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>Raw Definition</h3>
          <pre className={styles.jsonView}>
            {JSON.stringify(probe, null, 2)}
          </pre>
        </section>
      </div>
    </div>
  );
}
