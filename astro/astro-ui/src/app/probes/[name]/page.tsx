'use client';

import { use } from 'react';
import Link from 'next/link';
import { Settings, FileText } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
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

  // Build metadata for display - parameters is a JSON Schema object
  const parametersSchema = probe.parameters as {
    type?: string;
    properties?: Record<string, { type?: string; default?: unknown; items?: { type?: string } }>;
    required?: string[];
  } | undefined;

  const requiredParams = new Set(parametersSchema?.required || []);
  const properties = parametersSchema?.properties || {};

  const parameterEntries = Object.entries(properties).map(([key, value]) => {
    let typeStr = value.type || 'unknown';
    if (value.type === 'array' && value.items?.type) {
      typeStr = `array<${value.items.type}>`;
    }
    return [key, {
      type: typeStr,
      required: requiredParams.has(key),
      default: value.default,
    }];
  });

  return (
    <div className={styles.page}>
      <PageHeader
        title={probe.name}
        subtitle="Probe (Read-only from API)"
        backHref="/probes"
        breadcrumbs={[
          { label: 'Probes', href: '/probes' },
          { label: probe.name },
        ]}
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
