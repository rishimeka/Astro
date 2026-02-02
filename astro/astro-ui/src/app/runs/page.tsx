'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import PageHeader from '@/components/PageHeader/PageHeader';
import { DataTable, Column } from '@/components/DataTable';
import { StatusFilter, FilterableStatus } from '@/components/StatusFilter';
import { StatusBadge } from '@/components/StatusBadge';
import { DateRangeFilter, DateRangePreset, DateRange } from '@/components/DateRangeFilter';
import { Pagination } from '@/components/Pagination';
import { EmptyState } from '@/components/EmptyState';
import Spinner from '@/components/Loading/Spinner';
import ErrorMessage from '@/components/Error/ErrorMessage';
import { useRuns } from '@/hooks';
import { formatDateTime, getRelativeTime } from '@/lib/utils/date';
import type { RunSummary, RunStatus } from '@/types/astro';
import styles from './page.module.scss';

const PAGE_SIZE = 10;

export default function RunList() {
  const router = useRouter();
  const { runs, isLoading, error, refetch } = useRuns();
  const [statusFilter, setStatusFilter] = useState<FilterableStatus>('all');
  const [datePreset, setDatePreset] = useState<DateRangePreset>('all');
  const [customDateRange, setCustomDateRange] = useState<DateRange | undefined>();
  const [sortColumn, setSortColumn] = useState<string>('started_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);

  const columns: Column<RunSummary>[] = [
    {
      key: 'constellation_name',
      header: 'Constellation',
      sortable: true,
      width: '35%',
      render: (value, row) => (
        <Link href={`/constellations/${row.constellation_id}`} className={styles.constellationLink}>
          {String(value)}
        </Link>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      width: '20%',
      render: (value) => <StatusBadge status={value as RunStatus} size="sm" />,
    },
    {
      key: 'started_at',
      header: 'Started',
      sortable: true,
      width: '22%',
      render: (value) => (
        <span className={styles.datetime} title={formatDateTime(value as string)}>
          {getRelativeTime(value as string)}
        </span>
      ),
    },
    {
      key: 'completed_at',
      header: 'Completed',
      sortable: true,
      width: '23%',
      render: (value) => (
        <span className={styles.datetime}>
          {value ? formatDateTime(value as string) : '—'}
        </span>
      ),
    },
  ];

  const filteredData = useMemo(() => {
    let data = [...runs];

    // Filter by status
    if (statusFilter !== 'all') {
      data = data.filter((r) => r.status === statusFilter);
    }

    // Filter by date range
    if (datePreset !== 'all') {
      const now = new Date();
      let startDate: Date | null = null;

      switch (datePreset) {
        case 'today':
          startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
          break;
        case 'week':
          startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          break;
        case 'month':
          startDate = new Date(now.getFullYear(), now.getMonth(), 1);
          break;
        case 'custom':
          if (customDateRange?.start) {
            startDate = customDateRange.start;
          }
          break;
      }

      if (startDate) {
        data = data.filter((r) => new Date(r.started_at) >= startDate!);
      }

      if (datePreset === 'custom' && customDateRange?.end) {
        const endDate = new Date(customDateRange.end);
        endDate.setHours(23, 59, 59, 999);
        data = data.filter((r) => new Date(r.started_at) <= endDate);
      }
    }

    // Sort
    data.sort((a, b) => {
      const aVal = a[sortColumn as keyof RunSummary];
      const bVal = b[sortColumn as keyof RunSummary];

      // Handle null values for completed_at
      if (aVal === null && bVal === null) return 0;
      if (aVal === null) return sortDirection === 'asc' ? 1 : -1;
      if (bVal === null) return sortDirection === 'asc' ? -1 : 1;

      // Date comparison for date fields
      if (sortColumn === 'started_at' || sortColumn === 'completed_at') {
        const aDate = new Date(aVal as string).getTime();
        const bDate = new Date(bVal as string).getTime();
        return sortDirection === 'asc' ? aDate - bDate : bDate - aDate;
      }

      // String comparison
      const cmp = String(aVal).localeCompare(String(bVal));
      return sortDirection === 'asc' ? cmp : -cmp;
    });

    return data;
  }, [runs, statusFilter, datePreset, customDateRange, sortColumn, sortDirection]);

  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredData.slice(start, start + PAGE_SIZE);
  }, [filteredData, currentPage]);

  const totalPages = Math.ceil(filteredData.length / PAGE_SIZE);

  const handleSort = (column: string, direction: 'asc' | 'desc') => {
    setSortColumn(column);
    setSortDirection(direction);
  };

  const handleRowClick = (row: RunSummary) => {
    router.push(`/runs/${row.id}`);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleDateRangeChange = (preset: DateRangePreset, range?: DateRange) => {
    setDatePreset(preset);
    setCustomDateRange(range);
    setCurrentPage(1);
  };

  const hasFilters = statusFilter !== 'all' || datePreset !== 'all';

  if (isLoading) {
    return (
      <div>
        <PageHeader
          title="Run History"
          subtitle="View execution history and results"
        />
        <div className={styles.loadingContainer}>
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  if (error && runs.length === 0) {
    return (
      <div>
        <PageHeader
          title="Run History"
          subtitle="View execution history and results"
        />
        <ErrorMessage message={error} onRetry={refetch} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Run History"
        subtitle="View execution history and results"
      />

      {error && (
        <ErrorMessage message={`Using cached data: ${error}`} />
      )}

      <div className={styles.filters}>
        <StatusFilter
          value={statusFilter}
          onChange={(status) => {
            setStatusFilter(status);
            setCurrentPage(1);
          }}
        />
        <DateRangeFilter
          preset={datePreset}
          customRange={customDateRange}
          onChange={handleDateRangeChange}
        />
      </div>

      {filteredData.length === 0 ? (
        <EmptyState
          icon={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
          }
          title={hasFilters ? 'No runs found' : 'No runs yet'}
          description={
            hasFilters
              ? 'Try adjusting your filters'
              : 'Run a constellation to see execution history here'
          }
          action={
            hasFilters
              ? {
                  label: 'Clear filters',
                  onClick: () => {
                    setStatusFilter('all');
                    setDatePreset('all');
                    setCustomDateRange(undefined);
                  },
                }
              : {
                  label: 'View Constellations',
                  onClick: () => router.push('/constellations'),
                }
          }
        />
      ) : (
        <>
          <DataTable
            data={paginatedData}
            columns={columns}
            sortColumn={sortColumn}
            sortDirection={sortDirection}
            onSort={handleSort}
            onRowClick={handleRowClick}
            keyExtractor={(r) => r.id}
          />
          {totalPages > 1 && (
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              pageSize={PAGE_SIZE}
              totalItems={filteredData.length}
              onPageChange={handlePageChange}
            />
          )}
        </>
      )}
    </div>
  );
}
