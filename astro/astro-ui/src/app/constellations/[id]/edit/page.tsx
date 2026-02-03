'use client';

import { useState, useEffect, useCallback, useMemo, use, useRef } from 'react';
import { useRouter } from 'next/navigation';
import PageHeader from '@/components/PageHeader';
import {
  Canvas,
  NodePalette,
  PropertiesPanel,
  ValidationPanel,
  Toolbar,
} from '@/components/ConstellationBuilder';
import type {
  ConstellationGraph,
  ValidationError,
  PaletteItem,
  ConstellationNode,
  StarNodeData,
  CanvasRef,
  SelectedNode,
} from '@/components/ConstellationBuilder';
import type { Edge } from 'reactflow';
import { Spinner } from '@/components/Loading';
import { ENDPOINTS } from '@/lib/api/endpoints';
import { api } from '@/lib/api/client';
import { useStars } from '@/hooks/useStars';
import { useDirectives } from '@/hooks/useDirectives';
import type { Constellation, StarSummary, DirectiveSummary } from '@/types/astro';
import { NodeType } from '@/types/astro';
import styles from './page.module.scss';

interface EditConstellationPageProps {
  params: Promise<{ id: string }>;
}

// Convert stars to palette items
function getStarsAsPaletteItems(
  stars: StarSummary[],
  directives: DirectiveSummary[]
): PaletteItem[] {
  return stars.map((star) => {
    const directive = directives.find((d) => d.id === star.directive_id);
    return {
      type: 'star' as const,
      starId: star.id,
      starName: star.name,
      starType: star.type as PaletteItem['starType'],
      directiveId: star.directive_id,
      directiveName: directive?.name || 'Unknown Directive',
    };
  });
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
    deletable: false,
  } as ConstellationNode);

  // Add end node
  nodes.push({
    id: constellation.end.id,
    type: 'end',
    position: constellation.end.position,
    data: { label: 'End' },
    deletable: false,
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

export default function EditConstellationPage({ params }: EditConstellationPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const canvasRef = useRef<CanvasRef>(null);
  const [constellation, setConstellation] = useState<Constellation | null>(null);
  const [isLoadingConstellation, setIsLoadingConstellation] = useState(true);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [graph, setGraph] = useState<ConstellationGraph | null>(null);
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState<SelectedNode | null>(null);

  // Fetch stars and directives
  const { stars, isLoading: isLoadingStars } = useStars();
  const { directives, isLoading: isLoadingDirectives } = useDirectives();

  const isLoading = isLoadingConstellation || isLoadingStars || isLoadingDirectives;

  const paletteItems = useMemo(
    () => getStarsAsPaletteItems(stars, directives),
    [stars, directives]
  );
  const filteredPaletteItems = searchQuery
    ? paletteItems.filter(
        (item) =>
          item.starName.toLowerCase().includes(searchQuery.toLowerCase()) ||
          item.directiveName.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : paletteItems;

  // Load constellation data
  useEffect(() => {
    async function fetchConstellation() {
      try {
        const data = await api.get<Constellation>(ENDPOINTS.CONSTELLATION(id));
        setConstellation(data);
        setName(data.name);
        setDescription(data.description);
      } catch (err) {
        console.error('Failed to load constellation:', err);
      } finally {
        setIsLoadingConstellation(false);
      }
    }

    fetchConstellation();
  }, [id]);

  const handleGraphChange = useCallback((newGraph: ConstellationGraph) => {
    setGraph(newGraph);
  }, []);

  const handleValidationChange = useCallback((newErrors: ValidationError[]) => {
    setErrors(newErrors);
  }, []);

  const handleAutoLayout = useCallback(() => {
    canvasRef.current?.autoLayout();
  }, []);

  const handleNodeSelect = useCallback((node: SelectedNode | null) => {
    setSelectedNode(node);
  }, []);

  const handleUpdateNode = useCallback((nodeId: string, updates: Partial<StarNodeData>) => {
    canvasRef.current?.updateNode(nodeId, updates);
  }, []);


  const handleSave = useCallback(async () => {
    if (!name.trim()) {
      alert('Please enter a constellation name');
      return;
    }

    if (!graph) {
      alert('No graph data to save');
      return;
    }

    const errorCount = errors.filter((e) => e.severity === 'error').length;
    if (errorCount > 0) {
      alert(`Please fix ${errorCount} validation error(s) before saving`);
      return;
    }

    setIsSaving(true);

    try {
      const startNode = graph.nodes.find((n) => n.type === 'start');
      const endNode = graph.nodes.find((n) => n.type === 'end');
      const starNodes = graph.nodes.filter((n) => n.type === 'star');

      const constellationData = {
        id,
        name: name.trim(),
        description: description.trim(),
        start: {
          id: startNode?.id || 'start',
          type: 'start',
          position: startNode?.position || { x: 0, y: 200 },
          original_query: null,
          constellation_purpose: null,
        },
        end: {
          id: endNode?.id || 'end',
          type: 'end',
          position: endNode?.position || { x: 600, y: 200 },
        },
        nodes: starNodes.map((node) => {
          const data = node.data as StarNodeData | undefined;
          return {
            id: node.id,
            type: 'star',
            position: node.position,
            star_id: data?.starId || '',
            display_name: data?.displayName || null,
            variable_bindings: {},
            requires_confirmation: data?.requiresConfirmation || false,
            confirmation_prompt: data?.confirmationPrompt || null,
          };
        }),
        edges: graph.edges.map((edge) => ({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          condition: edge.data?.condition || null,
        })),
        metadata: {},
      };

      await api.put(ENDPOINTS.CONSTELLATION(id), constellationData);
      router.push(`/constellations/${id}`);
    } catch (error) {
      console.error('Failed to save constellation:', error);
      alert('Failed to save constellation. Please try again.');
    } finally {
      setIsSaving(false);
    }
  }, [id, name, description, graph, errors, router]);

  const handleErrorClick = useCallback((error: ValidationError) => {
    console.log('Focus on error:', error);
  }, []);

  if (isLoading) {
    return (
      <div className={styles.loadingContainer}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (!constellation) {
    return (
      <div className={styles.errorContainer}>
        <h2>Error</h2>
        <p>Constellation not found</p>
      </div>
    );
  }

  const { nodes: initialNodes, edges: initialEdges } = convertToReactFlowGraph(
    constellation,
    stars,
    directives
  );

  const hasErrors = errors.filter((e) => e.severity === 'error').length > 0;

  return (
    <div className={styles.page}>
      <PageHeader
        title={`Edit: ${constellation.name}`}
        subtitle="Modify the workflow graph"
        breadcrumbs={[
          { label: 'Constellations', href: '/constellations' },
          { label: constellation.name, href: `/constellations/${id}` },
          { label: 'Edit' },
        ]}
      />

      <div className={styles.metaForm}>
        <div className={styles.field}>
          <label className={styles.label}>Name *</label>
          <input
            type="text"
            className="input"
            placeholder="Enter constellation name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className={styles.field}>
          <label className={styles.label}>Description</label>
          <input
            type="text"
            className="input"
            placeholder="Brief description of this workflow"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      </div>

      <Toolbar
        onAutoLayout={handleAutoLayout}
        onSave={handleSave}
        isSaving={isSaving}
        hasErrors={hasErrors}
      />

      <div className={styles.builder}>
        <NodePalette
          stars={filteredPaletteItems}
          onSearch={setSearchQuery}
        />

        <div className={styles.canvasWrapper}>
          <Canvas
            ref={canvasRef}
            initialNodes={initialNodes}
            initialEdges={initialEdges}
            onChange={handleGraphChange}
            onValidationChange={handleValidationChange}
            onNodeSelect={handleNodeSelect}
          />
        </div>

        <div className={styles.sidebar}>
          <PropertiesPanel
            selectedNode={selectedNode}
            onUpdateNode={handleUpdateNode}
          />
          <ValidationPanel errors={errors} onErrorClick={handleErrorClick} />
        </div>
      </div>
    </div>
  );
}
