'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import PageHeader from '@/components/PageHeader';
import { DataTable, Column } from '@/components/DataTable';
import { SearchInput } from '@/components/SearchInput';
import { EmptyState } from '@/components/EmptyState';
import { Spinner } from '@/components/Loading';
import { ErrorMessage } from '@/components/Error';
import { useProbes } from '@/hooks';
import type { Probe } from '@/types/astro';
import styles from './page.module.scss';

const columns: Column<Probe>[] = [
  {
    key: 'name',
    header: 'Name',
    sortable: true,
    width: '25%',
    render: (value) => (
      <code className={styles.probeName}>{String(value)}</code>
    ),
  },
  {
    key: 'description',
    header: 'Description',
    width: '45%',
    render: (value) => (
      <span className={styles.description}>{String(value)}</span>
    ),
  },
  {
    key: 'parameters',
    header: 'Parameters',
    width: '30%',
    render: (value) => {
      const params = value as Record<string, unknown> | undefined;
      if (!params || Object.keys(params).length === 0) {
        return <span className={styles.noParams}>None</span>;
      }
      const paramNames = Object.keys(params);
      return (
        <div className={styles.params}>
          {paramNames.slice(0, 3).map((name) => (
            <span key={name} className={styles.paramBadge}>
              {name}
            </span>
          ))}
          {paramNames.length > 3 && (
            <span className={styles.moreParams}>+{paramNames.length - 3}</span>
          )}
        </div>
      );
    },
  },
];

export default function ProbeList() {
  const router = useRouter();
  const { probes, isLoading, error, refetch } = useProbes();
  const [search, setSearch] = useState('');
  const [sortColumn, setSortColumn] = useState<string>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const handleRowClick = (probe: Probe) => {
    router.push(`/probes/${encodeURIComponent(probe.name)}`);
  };

  const filteredData = useMemo(() => {
    let data = [...probes];

    // Filter by search
    if (search) {
      const searchLower = search.toLowerCase();
      data = data.filter(
        (probe) =>
          probe.name.toLowerCase().includes(searchLower) ||
          probe.description.toLowerCase().includes(searchLower)
      );
    }

    // Sort
    data.sort((a, b) => {
      const aVal = String(a[sortColumn as keyof Probe] || '');
      const bVal = String(b[sortColumn as keyof Probe] || '');
      const cmp = aVal.localeCompare(bVal);
      return sortDirection === 'asc' ? cmp : -cmp;
    });

    return data;
  }, [probes, search, sortColumn, sortDirection]);

  const handleSort = (column: string, direction: 'asc' | 'desc') => {
    setSortColumn(column);
    setSortDirection(direction);
  };

  const subtitle = (
    <>
      Reusable data extraction functions defined in code
      <span className={styles.subtitleNote}>Probes are defined in code and cannot be edited from the UI.</span>
    </>
  );

  if (isLoading) {
    return (
      <div>
        <PageHeader
          title="Probes"
          subtitle={subtitle}
        />
        <div className={styles.loadingContainer}>
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  if (error && probes.length === 0) {
    return (
      <div>
        <PageHeader
          title="Probes"
          subtitle={subtitle}
        />
        <ErrorMessage message={error} onRetry={refetch} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Probes"
        subtitle={subtitle}
      />

      {error && (
        <ErrorMessage message={`Using cached data: ${error}`} />
      )}

      <div className={styles.filters}>
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search probes..."
        />
      </div>

      {filteredData.length === 0 && search ? (
        <EmptyState
          icon={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
            </svg>
          }
          title="No probes found"
          description={`No probes match "${search}"`}
          action={{
            label: 'Clear search',
            onClick: () => setSearch(''),
          }}
        />
      ) : filteredData.length === 0 ? (
        <EmptyState
          icon={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
            </svg>
          }
          title="No probes available"
          description="Probes are defined in code. Check with your administrator."
        />
      ) : (
        <DataTable
          data={filteredData}
          columns={columns}
          sortColumn={sortColumn}
          sortDirection={sortDirection}
          onSort={handleSort}
          onRowClick={handleRowClick}
          emptyMessage="No probes available"
          keyExtractor={(probe) => probe.name}
        />
      )}
    </div>
  );
}
