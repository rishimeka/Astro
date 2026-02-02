import { Node, Edge } from 'reactflow';

// Star types supported in the constellation
export type StarType = 'worker' | 'planning' | 'eval' | 'synthesis' | 'execution' | 'docex';

// Node data payloads
export interface StartNodeData {
  label: 'Start';
}

export interface EndNodeData {
  label: 'End';
}

export interface StarNodeData {
  starId: string;
  starName: string;
  starType: StarType;
  directiveId: string;
  directiveName: string;
  displayName?: string;
  requiresConfirmation: boolean;
  confirmationPrompt?: string;
  hasProbes: boolean;
  probeCount: number;
  hasVariables: boolean;
  variableCount: number;
}

// Custom node types
export type ConstellationNode =
  | Node<StartNodeData, 'start'>
  | Node<EndNodeData, 'end'>
  | Node<StarNodeData, 'star'>;

// Edge with optional condition (for EvalStar routing)
export interface ConstellationEdgeData {
  condition?: 'continue' | 'loop';
}

export type ConstellationEdge = Edge<ConstellationEdgeData>;

// Validation
export interface ValidationError {
  nodeId?: string;
  edgeId?: string;
  message: string;
  severity: 'error' | 'warning';
}

// Palette item for drag-and-drop
export interface PaletteItem {
  type: 'star';
  starId: string;
  starName: string;
  starType: StarType;
  directiveId: string;
  directiveName: string;
}

// Full constellation state for save
export interface ConstellationGraph {
  nodes: ConstellationNode[];
  edges: ConstellationEdge[];
}

// Aggregated variable for the VariablePanel
export interface AggregatedVariable {
  name: string;
  description: string;
  required: boolean;
  default?: string;
  usedBy: { nodeId: string; nodeName: string }[];
}

// Canvas ref handle for imperative methods
export interface CanvasRef {
  autoLayout: () => void;
  updateNode: (nodeId: string, updates: Partial<StarNodeData>) => void;
}

// Selected node info for properties panel
export interface SelectedNode {
  id: string;
  type: 'start' | 'end' | 'star';
  data: StartNodeData | EndNodeData | StarNodeData;
}

// Canvas props
export interface CanvasProps {
  initialNodes?: ConstellationNode[];
  initialEdges?: ConstellationEdge[];
  onChange?: (graph: ConstellationGraph) => void;
  onValidationChange?: (errors: ValidationError[]) => void;
  onNodeSelect?: (node: SelectedNode | null) => void;
  readOnly?: boolean;
}

// PropertiesPanel props
export interface PropertiesPanelProps {
  selectedNode: SelectedNode | null;
  onUpdateNode?: (nodeId: string, updates: Partial<StarNodeData>) => void;
}

// NodePalette props
export interface NodePaletteProps {
  stars: PaletteItem[];
  onSearch?: (query: string) => void;
}

// VariablePanel props
export interface VariablePanelProps {
  variables: AggregatedVariable[];
}

// ValidationPanel props
export interface ValidationPanelProps {
  errors: ValidationError[];
  onErrorClick?: (error: ValidationError) => void;
}

// Toolbar props
export interface ToolbarProps {
  onAutoLayout: () => void;
  onSave: () => void;
  onRun?: () => void;
  isSaving?: boolean;
  hasErrors?: boolean;
  canRun?: boolean;
}
