'use client';

import { useState, useEffect, useMemo, use } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Play, Edit2, Trash2 } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { Canvas } from '@/components/ConstellationBuilder';
import type { ConstellationNode } from '@/components/ConstellationBuilder';
import type { Edge } from 'reactflow';
import { Spinner } from '@/components/Loading';
import { ENDPOINTS } from '@/lib/api/endpoints';
import { api } from '@/lib/api/client';
import { useStars } from '@/hooks/useStars';
import { useDirectives } from '@/hooks/useDirectives';
import type { Constellation, StarSummary, DirectiveSummary } from '@/types/astro';
import { NodeType } from '@/types/astro';
import styles from './page.module.scss';

interface ConstellationDetailProps {
  params: Promise<{ id: string }>;
}

// Convert API constellation to React Flow format
function convertToReactFlowGraph(
  constellation: Constellation,
  stars: StarSummary[],
  directives: DirectiveSummary[]
): { nodes: ConstellationNode[]; edges: Edge[] } {
  const nodes: ConstellationNode[] = [];

  // Add start node
  nodes.push({
    id: constellation.start.id,
    type: 'start',
    position: constellation.start.position,
    data: { label: 'Start' },
  } as ConstellationNode);

  // Add end node
  nodes.push({
    id: constellation.end.id,
    type: 'end',
    position: constellation.end.position,
    data: { label: 'End' },
  } as ConstellationNode);

  // Add star nodes
  constellation.nodes.forEach((node) => {
    const star = stars.find((s) => s.id === node.star_id);
    const directive = directives.find((d) => d.id === star?.directive_id);

    nodes.push({
      id: node.id,
      type: 'star',
      position: node.position,
      data: {
        starId: node.star_id,
        starName: star?.name || 'Unknown Star',
        starType: star?.type || 'worker',
        directiveId: star?.directive_id || '',
        directiveName: directive?.name || 'Unknown Directive',
        displayName: node.display_name || undefined,
        requiresConfirmation: node.requires_confirmation,
        confirmationPrompt: node.confirmation_prompt || undefined,
        hasProbes: false,
        probeCount: 0,
        hasVariables: false,
        variableCount: 0,
      },
    } as ConstellationNode);
  });

  // Convert edges
  const edges: Edge[] = constellation.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: 'constellation',
    data: edge.condition ? { condition: edge.condition } : undefined,
  }));

  return { nodes, edges };
}

export default function ConstellationDetailPage({ params }: ConstellationDetailProps) {
  const { id } = use(params);
  const router = useRouter();
  const [constellation, setConstellation] = useState<Constellation | null>(null);
  const [isLoadingConstellation, setIsLoadingConstellation] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch stars and directives
  const { stars, isLoading: isLoadingStars } = useStars();
  const { directives, isLoading: isLoadingDirectives } = useDirectives();

  const isLoading = isLoadingConstellation || isLoadingStars || isLoadingDirectives;

  useEffect(() => {
    async function fetchConstellation() {
      try {
        // Try to fetch from API
        const data = await api.get<Constellation>(ENDPOINTS.CONSTELLATION(id));
        setConstellation(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Constellation not found');
      } finally {
        setIsLoadingConstellation(false);
      }
    }

    fetchConstellation();
  }, [id]);

  // useMemo must be called before early returns to follow Rules of Hooks
  const { nodes, edges } = useMemo(() => {
    if (!constellation) {
      return { nodes: [], edges: [] };
    }
    return convertToReactFlowGraph(constellation, stars, directives);
  }, [constellation, stars, directives]);

  const handleRun = () => {
    router.push(`/runs/new?constellation=${id}`);
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this constellation?')) {
      return;
    }

    try {
      await api.delete(ENDPOINTS.CONSTELLATION(id));
      router.push('/constellations');
    } catch (err) {
      console.error('Failed to delete constellation:', err);
      alert('Failed to delete constellation');
    }
  };

  if (isLoading) {
    return (
      <div className={styles.loadingContainer}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !constellation) {
    return (
      <div className={styles.errorContainer}>
        <h2>Error</h2>
        <p>{error || 'Failed to load constellation'}</p>
        <Link href="/constellations" className="btn btn-primary btn-outline">
          Back to Constellations
        </Link>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <PageHeader
        title={constellation.name}
        subtitle={constellation.description}
        backHref="/constellations"
        breadcrumbs={[
          { label: 'Constellations', href: '/constellations' },
          { label: constellation.name },
        ]}
        actions={
          <div className={styles.actions}>
            <button
              className="btn btn-error btn-outline"
              onClick={handleDelete}
              title="Delete"
            >
              <Trash2 size={16} />
            </button>
            <Link
              href={`/constellations/${id}/edit`}
              className="btn btn-primary btn-outline"
            >
              <Edit2 size={16} />
              Edit
            </Link>
            <button
              className="btn btn-primary btn-highlight"
              onClick={handleRun}
            >
              <Play size={16} />
              Run
            </button>
          </div>
        }
      />

      <div className={styles.info}>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Nodes</span>
          <span className={styles.statValue}>{constellation.nodes.length + 2}</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Edges</span>
          <span className={styles.statValue}>{constellation.edges.length}</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Max Loops</span>
          <span className={styles.statValue}>{constellation.max_loop_iterations}</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Max Retries</span>
          <span className={styles.statValue}>{constellation.max_retry_attempts}</span>
        </div>
      </div>

      <div className={styles.canvasContainer}>
        <Canvas
          initialNodes={nodes}
          initialEdges={edges}
          readOnly
        />
      </div>
    </div>
  );
}
