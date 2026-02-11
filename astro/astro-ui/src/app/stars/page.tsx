'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import PageHeader from '@/components/PageHeader';
import { DataTable, Column } from '@/components/DataTable';
import { SearchInput } from '@/components/SearchInput';
import { TypeFilter } from '@/components/TypeFilter';
import { Pagination } from '@/components/Pagination';
import { EmptyState } from '@/components/EmptyState';
import { Spinner } from '@/components/Loading';
import { ErrorMessage } from '@/components/Error';
import { useStars } from '@/hooks';
import { useDirectives } from '@/hooks';
import { StarType } from '@/types/astro';
import type { StarSummary } from '@/types/astro';
import styles from './page.module.scss';

const PAGE_SIZE = 10;

const typeLabels: Record<StarType, string> = {
  [StarType.PLANNING]: 'Planning',
  [StarType.EXECUTION]: 'Execution',
  [StarType.DOCEX]: 'DocEx',
  [StarType.EVAL]: 'Eval',
  [StarType.WORKER]: 'Worker',
  [StarType.SYNTHESIS]: 'Synthesis',
};

const typeColors: Record<StarType, string> = {
  [StarType.PLANNING]: '#3B82F6',
  [StarType.EXECUTION]: '#10B981',
  [StarType.DOCEX]: '#8B5CF6',
  [StarType.EVAL]: '#F59E0B',
  [StarType.WORKER]: '#4A9DEA',
  [StarType.SYNTHESIS]: '#EC4899',
};

export default function StarList() {
  const router = useRouter();
  const { stars, isLoading: starsLoading, error: starsError, refetch } = useStars();
  const { directives, isLoading: directivesLoading } = useDirectives();
  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState<StarType | null>(null);
  const [sortColumn, setSortColumn] = useState<string>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);

  const isLoading = starsLoading || directivesLoading;
  const error = starsError;

  const directiveMap = useMemo(() => {
    const map: Record<string, string> = {};
    directives.forEach((d) => {
      map[d.id] = d.name;
    });
    return map;
  }, [directives]);

  const columns: Column<StarSummary>[] = [
    {
      key: 'name',
      header: 'Name',
      sortable: true,
      width: '30%',
      render: (value, row) => (
        <Link href={`/stars/${row.id}`} className={styles.nameLink}>
          {String(value)}
        </Link>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      sortable: true,
      width: '20%',
      render: (value) => {
        const type = value as StarType;
        return (
          <span
            className={styles.typeBadge}
            style={{ backgroundColor: `${typeColors[type]}20`, color: typeColors[type] }}
          >
            {typeLabels[type]}
          </span>
        );
      },
    },
    {
      key: 'directive_id',
      header: 'Directive',
      sortable: true,
      width: '30%',
      render: (value, row) => {
        const directiveId = value as string;
        const directiveName = directiveMap[directiveId] || directiveId;
        return (
          <Link href={`/directives/${row.directive_id}`} className={styles.directiveLink}>
            {directiveName}
          </Link>
        );
      },
    },
  ];

  const filteredData = useMemo(() => {
    let data = [...stars];

    // Filter by search
    if (search) {
      const searchLower = search.toLowerCase();
      data = data.filter((s) => s.name.toLowerCase().includes(searchLower));
    }

    // Filter by type
    if (selectedType) {
      data = data.filter((s) => s.type === selectedType);
    }

    // Sort
    data.sort((a, b) => {
      let aVal = String(a[sortColumn as keyof StarSummary] || '');
      let bVal = String(b[sortColumn as keyof StarSummary] || '');

      // Special handling for directive_id - sort by name
      if (sortColumn === 'directive_id') {
        aVal = directiveMap[a.directive_id] || a.directive_id;
        bVal = directiveMap[b.directive_id] || b.directive_id;
      }

      const cmp = aVal.localeCompare(bVal);
      return sortDirection === 'asc' ? cmp : -cmp;
    });

    return data;
  }, [stars, search, selectedType, sortColumn, sortDirection, directiveMap]);

  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredData.slice(start, start + PAGE_SIZE);
  }, [filteredData, currentPage]);

  const totalPages = Math.ceil(filteredData.length / PAGE_SIZE);

  const handleSort = (column: string, direction: 'asc' | 'desc') => {
    setSortColumn(column);
    setSortDirection(direction);
  };

  const handleRowClick = (row: StarSummary) => {
    router.push(`/stars/${row.id}`);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const hasFilters = search || selectedType;

  if (isLoading) {
    return (
      <div>
        <PageHeader
          title="Stars"
          subtitle="Configured directive instances with parameters"
          actions={
            <Link href="/stars/new" className="btn btn-primary btn-highlight">
              New Star
            </Link>
          }
        />
        <div className={styles.loadingContainer}>
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  if (error && stars.length === 0) {
    return (
      <div>
        <PageHeader
          title="Stars"
          subtitle="Configured directive instances with parameters"
          actions={
            <Link href="/stars/new" className="btn btn-primary btn-highlight">
              New Star
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
        title="Stars"
        subtitle="Configured directive instances with parameters"
        actions={
          <Link href="/stars/new" className="btn btn-primary btn-highlight">
            New Star
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
          placeholder="Search stars..."
        />
        <TypeFilter
          value={selectedType}
          onChange={(type) => {
            setSelectedType(type);
            setCurrentPage(1);
          }}
        />
      </div>

      {filteredData.length === 0 ? (
        <EmptyState
          icon={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
          }
          title={hasFilters ? 'No stars found' : 'No stars yet'}
          description={
            hasFilters
              ? 'Try adjusting your search or filters'
              : 'Create your first star to get started'
          }
          action={
            hasFilters
              ? {
                  label: 'Clear filters',
                  onClick: () => {
                    setSearch('');
                    setSelectedType(null);
                  },
                }
              : {
                  label: 'Create Star',
                  onClick: () => router.push('/stars/new'),
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
            keyExtractor={(s) => s.id}
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
