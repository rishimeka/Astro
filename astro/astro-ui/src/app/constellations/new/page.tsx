'use client';

import { useState, useCallback, useMemo, useRef } from 'react';
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
  StarNodeData,
  CanvasRef,
  SelectedNode,
} from '@/components/ConstellationBuilder';
import { Spinner } from '@/components/Loading';
import { useStars } from '@/hooks/useStars';
import { useDirectives } from '@/hooks/useDirectives';
import { ENDPOINTS } from '@/lib/api/endpoints';
import { api } from '@/lib/api/client';
import styles from './page.module.scss';

export default function NewConstellationPage() {
  const router = useRouter();
  const canvasRef = useRef<CanvasRef>(null);
  const { stars, isLoading: loadingStars } = useStars();
  const { directives, isLoading: loadingDirectives } = useDirectives();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [graph, setGraph] = useState<ConstellationGraph | null>(null);
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState<SelectedNode | null>(null);

  // Convert stars to palette items
  const paletteItems = useMemo((): PaletteItem[] => {
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
  }, [stars, directives]);

  const filteredPaletteItems = searchQuery
    ? paletteItems.filter(
        (item) =>
          item.starName.toLowerCase().includes(searchQuery.toLowerCase()) ||
          item.directiveName.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : paletteItems;

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
      // Transform graph to API format
      const startNode = graph.nodes.find((n) => n.type === 'start');
      const endNode = graph.nodes.find((n) => n.type === 'end');
      const starNodes = graph.nodes.filter((n) => n.type === 'star');

      const constellationData = {
        id: `const-${Date.now()}`,
        name: name.trim(),
        description: description.trim(),
        start: {
          id: startNode?.id || 'start',
          type: 'start',
          position: startNode?.position || { x: 250, y: 0 },
          original_query: null,
          constellation_purpose: null,
        },
        end: {
          id: endNode?.id || 'end',
          type: 'end',
          position: endNode?.position || { x: 250, y: 400 },
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

      await api.post(ENDPOINTS.CONSTELLATIONS, constellationData);
      router.push('/constellations');
    } catch (error) {
      console.error('Failed to save constellation:', error);
      alert('Failed to save constellation. Please try again.');
    } finally {
      setIsSaving(false);
    }
  }, [name, description, graph, errors, router]);

  const handleErrorClick = useCallback((error: ValidationError) => {
    // Could focus the node in the canvas via ref
    console.log('Focus on error:', error);
  }, []);

  const hasErrors = errors.filter((e) => e.severity === 'error').length > 0;
  const isLoading = loadingStars || loadingDirectives;

  if (isLoading) {
    return (
      <div className={styles.page}>
        <PageHeader
          title="Create Constellation"
          subtitle="Build a workflow graph with stars"
          breadcrumbs={[
            { label: 'Constellations', href: '/constellations' },
            { label: 'New' },
          ]}
        />
        <div className={styles.loadingContainer}>
          <Spinner size="lg" />
          <p>Loading stars and directives...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <PageHeader
        title="Create Constellation"
        subtitle="Build a workflow graph with stars"
        breadcrumbs={[
          { label: 'Constellations', href: '/constellations' },
          { label: 'New' },
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
