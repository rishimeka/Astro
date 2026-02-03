'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import PageHeader from '@/components/PageHeader';
import { SearchInput } from '@/components/SearchInput';
import { TagFilter } from '@/components/TagFilter';
import { ConstellationCard } from '@/components/ConstellationCard';
import { EmptyState } from '@/components/EmptyState';
import { Spinner } from '@/components/Loading';
import { ErrorMessage } from '@/components/Error';
import { useConstellations, getConstellationTags } from '@/hooks';
import styles from './page.module.scss';

export default function ConstellationList() {
  const router = useRouter();
  const { constellations, isLoading, error, refetch } = useConstellations();
  const [search, setSearch] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  const allTags = useMemo(() => getConstellationTags(constellations), [constellations]);

  const filteredData = useMemo(() => {
    let data = [...constellations];

    // Filter by search
    if (search) {
      const searchLower = search.toLowerCase();
      data = data.filter(
        (c) =>
          c.name.toLowerCase().includes(searchLower) ||
          c.description.toLowerCase().includes(searchLower)
      );
    }

    // Filter by tags
    if (selectedTags.length > 0) {
      data = data.filter((c) =>
        selectedTags.some((tag) => c.tags.includes(tag))
      );
    }

    return data;
  }, [constellations, search, selectedTags]);

  const handleCardClick = (id: string) => {
    router.push(`/constellations/${id}`);
  };

  const hasFilters = search || selectedTags.length > 0;

  if (isLoading) {
    return (
      <div>
        <PageHeader
          title="Constellations"
          subtitle="Workflow graphs connecting stars"
          actions={
            <Link href="/constellations/new" className="btn btn-primary btn-highlight">
              New Constellation
            </Link>
          }
        />
        <div className={styles.loadingContainer}>
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  if (error && constellations.length === 0) {
    return (
      <div>
        <PageHeader
          title="Constellations"
          subtitle="Workflow graphs connecting stars"
          actions={
            <Link href="/constellations/new" className="btn btn-primary btn-highlight">
              New Constellation
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
        title="Constellations"
        subtitle="Workflow graphs connecting stars"
        actions={
          <Link href="/constellations/new" className="btn btn-primary btn-highlight">
            New Constellation
          </Link>
        }
      />

      {error && (
        <ErrorMessage message={`Using cached data: ${error}`} />
      )}

      <div className={styles.filters}>
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search constellations..."
        />
        <TagFilter
          tags={allTags}
          selected={selectedTags}
          onChange={setSelectedTags}
        />
      </div>

      {filteredData.length === 0 ? (
        <EmptyState
          icon={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="3" />
              <circle cx="19" cy="5" r="2" />
              <circle cx="5" cy="19" r="2" />
              <line x1="14.5" y1="9.5" x2="17.5" y2="6.5" />
              <line x1="9.5" y1="14.5" x2="6.5" y2="17.5" />
            </svg>
          }
          title={hasFilters ? 'No constellations found' : 'No constellations yet'}
          description={
            hasFilters
              ? 'Try adjusting your search or filters'
              : 'Create your first constellation to orchestrate star workflows'
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
                  label: 'Create Constellation',
                  onClick: () => router.push('/constellations/new'),
                }
          }
        />
      ) : (
        <div className={styles.grid}>
          {filteredData.map((constellation) => (
            <ConstellationCard
              key={constellation.id}
              id={constellation.id}
              name={constellation.name}
              description={constellation.description}
              nodeCount={constellation.node_count}
              tags={constellation.tags}
              onClick={() => handleCardClick(constellation.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
