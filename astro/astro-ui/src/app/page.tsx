'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { Spinner } from '@/components/Loading';
import { useProbes } from '@/hooks/useProbes';
import { useDirectives } from '@/hooks/useDirectives';
import { useStars } from '@/hooks/useStars';
import { useConstellations } from '@/hooks/useConstellations';
import { useRuns } from '@/hooks/useRuns';
import { formatDateTime } from '@/lib/utils/date';
import type { RunStatus } from '@/types/astro';
import styles from './page.module.scss';

export default function Dashboard() {
  const { probes, isLoading: loadingProbes } = useProbes();
  const { directives, isLoading: loadingDirectives } = useDirectives();
  const { stars, isLoading: loadingStars } = useStars();
  const { constellations, isLoading: loadingConstellations } = useConstellations();
  const { runs, isLoading: loadingRuns } = useRuns();

  const isLoading = loadingProbes || loadingDirectives || loadingStars || loadingConstellations || loadingRuns;

  // Get the 5 most recent runs
  const recentRuns = runs
    .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())
    .slice(0, 5);

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Welcome to Astro"
        actions={
          <div className={styles.quickActions}>
            <Link href="/directives/new" className="btn btn-primary btn-outline btn-sm">
              Create Directive
            </Link>
            <Link href="/stars/new" className="btn btn-primary btn-outline btn-sm">
              Create Star
            </Link>
            <Link href="/constellations/new" className="btn btn-primary btn-outline btn-sm">
              Create Constellation
            </Link>
            <Link href="/launchpad" className="btn btn-primary btn-highlight btn-sm">
              Open Launchpad
            </Link>
          </div>
        }
      />
      <div className={styles.dashboard}>
        {/* Stats Grid */}
        <div className={styles.statsGrid}>
          <StatCard
            label="Probes"
            value={loadingProbes ? '-' : probes.length.toString()}
            href="/probes"
            isLoading={loadingProbes}
          />
          <StatCard
            label="Directives"
            value={loadingDirectives ? '-' : directives.length.toString()}
            href="/directives"
            isLoading={loadingDirectives}
          />
          <StatCard
            label="Stars"
            value={loadingStars ? '-' : stars.length.toString()}
            href="/stars"
            isLoading={loadingStars}
          />
          <StatCard
            label="Constellations"
            value={loadingConstellations ? '-' : constellations.length.toString()}
            href="/constellations"
            isLoading={loadingConstellations}
          />
        </div>

        {/* Recent Runs */}
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>Recent Runs</h2>
            {runs.length > 0 && (
              <Link href="/runs" className={styles.viewAllLink}>
                View all
                <ArrowRight size={14} />
              </Link>
            )}
          </div>

          {loadingRuns ? (
            <div className={styles.loadingState}>
              <Spinner size="sm" />
              <span>Loading recent runs...</span>
            </div>
          ) : recentRuns.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No runs yet. Create a constellation and run it to see results here.</p>
              <Link href="/constellations/new" className="btn btn-primary btn-outline btn-sm">
                Create Constellation
              </Link>
            </div>
          ) : (
            <div className={styles.runsTable}>
              <div className={styles.tableHeader}>
                <span className={styles.colStatus}>Status</span>
                <span className={styles.colConstellation}>Constellation</span>
                <span className={styles.colStarted}>Started</span>
                <span className={styles.colActions}></span>
              </div>
              {recentRuns.map((run) => (
                <Link key={run.id} href={`/runs/${run.id}`} className={styles.tableRow}>
                  <span className={styles.colStatus}>
                    <StatusBadge status={run.status as RunStatus} />
                  </span>
                  <span className={styles.colConstellation}>
                    {run.constellation_name}
                  </span>
                  <span className={styles.colStarted}>
                    {formatDateTime(run.started_at)}
                  </span>
                  <span className={styles.colActions}>
                    <ArrowRight size={16} className={styles.rowArrow} />
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  href: string;
  isLoading?: boolean;
}

function StatCard({ label, value, href, isLoading }: StatCardProps) {
  return (
    <Link href={href} className={styles.statCard}>
      <div className={styles.statContent}>
        {isLoading ? (
          <Spinner size="sm" className={styles.statSpinner} />
        ) : (
          <span className={styles.statValue}>{value}</span>
        )}
        <span className={styles.statLabel}>{label}</span>
      </div>
      <ArrowRight size={20} className={styles.statArrow} />
    </Link>
  );
}
