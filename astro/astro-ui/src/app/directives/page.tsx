'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import PageHeader from '@/components/PageHeader/PageHeader';
import { DataTable, Column } from '@/components/DataTable';
import { SearchInput } from '@/components/SearchInput';
import { TagFilter } from '@/components/TagFilter';
import { Pagination } from '@/components/Pagination';
import { EmptyState } from '@/components/EmptyState';
import Spinner from '@/components/Loading/Spinner';
import ErrorMessage from '@/components/Error/ErrorMessage';
import { useDirectives, getDirectiveTags } from '@/hooks';
import type { DirectiveSummary } from '@/types/astro';
import styles from './page.module.scss';

const PAGE_SIZE = 10;

export default function DirectiveList() {
  const router = useRouter();
  const { directives, isLoading, error, refetch } = useDirectives();
  const [search, setSearch] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [sortColumn, setSortColumn] = useState<string>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);

  const allTags = useMemo(() => getDirectiveTags(directives), [directives]);

  const columns: Column<DirectiveSummary>[] = [
    {
      key: 'name',
      header: 'Name',
      sortable: true,
      width: '25%',
      render: (value, row) => (
        <Link href={`/directives/${row.id}`} className={styles.nameLink}>
          {String(value)}
        </Link>
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
      key: 'tags',
      header: 'Tags',
      width: '30%',
      render: (value) => {
        const tags = value as string[];
        if (!tags || tags.length === 0) {
          return <span className={styles.noTags}>—</span>;
        }
        return (
          <div className={styles.tags}>
            {tags.slice(0, 3).map((tag) => (
              <span key={tag} className={styles.tag}>
                {tag}
              </span>
            ))}
            {tags.length > 3 && (
              <span className={styles.moreTags}>+{tags.length - 3}</span>
            )}
          </div>
        );
      },
    },
  ];

  const filteredData = useMemo(() => {
    let data = [...directives];

    // Filter by search
    if (search) {
      const searchLower = search.toLowerCase();
      data = data.filter(
        (d) =>
          d.name.toLowerCase().includes(searchLower) ||
          d.description.toLowerCase().includes(searchLower)
      );
    }

    // Filter by tags
    if (selectedTags.length > 0) {
      data = data.filter((d) =>
        selectedTags.some((tag) => d.tags.includes(tag))
      );
    }

    // Sort
    data.sort((a, b) => {
      const aVal = String(a[sortColumn as keyof DirectiveSummary] || '');
      const bVal = String(b[sortColumn as keyof DirectiveSummary] || '');
      const cmp = aVal.localeCompare(bVal);
      return sortDirection === 'asc' ? cmp : -cmp;
    });

    return data;
  }, [directives, search, selectedTags, sortColumn, sortDirection]);

  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredData.slice(start, start + PAGE_SIZE);
  }, [filteredData, currentPage]);

  const totalPages = Math.ceil(filteredData.length / PAGE_SIZE);

  const handleSort = (column: string, direction: 'asc' | 'desc') => {
    setSortColumn(column);
    setSortDirection(direction);
  };

  const handleRowClick = (row: DirectiveSummary) => {
    router.push(`/directives/${row.id}`);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const hasFilters = search || selectedTags.length > 0;

  if (isLoading) {
    return (
      <div>
        <PageHeader
          title="Directives"
          subtitle="Prompt modules that define analysis tasks"
          actions={
            <Link href="/directives/new" className="btn btn-primary btn-highlight">
              New Directive
            </Link>
          }
        />
        <div className={styles.loadingContainer}>
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  if (error && directives.length === 0) {
    return (
      <div>
        <PageHeader
          title="Directives"
          subtitle="Prompt modules that define analysis tasks"
          actions={
            <Link href="/directives/new" className="btn btn-primary btn-highlight">
              New Directive
            </Link>
          }
        />
        <ErrorMessage message={error} onRetry={refetch} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Directives"
        subtitle="Prompt modules that define analysis tasks"
        actions={
          <Link href="/directives/new" className="btn btn-primary btn-highlight">
            New Directive
          </Link>
        }
      />

      {error && (
        <ErrorMessage message={`Using cached data: ${error}`} />
      )}

      <div className={styles.filters}>
        <SearchInput
          value={search}
          onChange={(v) => {
            setSearch(v);
            setCurrentPage(1);
          }}
          placeholder="Search directives..."
        />
        <TagFilter
          tags={allTags}
          selected={selectedTags}
          onChange={(tags) => {
            setSelectedTags(tags);
            setCurrentPage(1);
          }}
        />
      </div>

      {filteredData.length === 0 ? (
        <EmptyState
          icon={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          }
          title={hasFilters ? 'No directives found' : 'No directives yet'}
          description={
            hasFilters
              ? 'Try adjusting your search or filters'
              : 'Create your first directive to get started'
          }
          action={
            hasFilters
              ? {
                  label: 'Clear filters',
                  onClick: () => {
                    setSearch('');
                    setSelectedTags([]);
                  },
                }
              : {
                  label: 'Create Directive',
                  onClick: () => router.push('/directives/new'),
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
            keyExtractor={(d) => d.id}
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
