/**
 * Astro TypeScript Types
 * Generated from Python Pydantic models in astro/models/
 *
 * These types match the backend API response structures.
 */

// ============================================================================
// Enums
// ============================================================================

export enum StarType {
  PLANNING = "planning",
  EXECUTION = "execution",
  DOCEX = "docex",
  EVAL = "eval",
  WORKER = "worker",
  SYNTHESIS = "synthesis",
}

export enum NodeType {
  START = "start",
  END = "end",
  STAR = "star",
}

// ============================================================================
// Template Variable
// ============================================================================

export type UIHint = "text" | "textarea" | "number" | "date" | "select" | "file";

export interface TemplateVariable {
  name: string;
  description: string;
  required: boolean;
  default: string | null;
  ui_hint: UIHint | null;
  ui_options: Record<string, unknown> | null;
  used_by: string[];
}

// ============================================================================
// Directive
// ============================================================================

export interface Directive {
  id: string;
  name: string;
  description: string;
  content: string;
  probe_ids: string[];
  reference_ids: string[];
  template_variables: TemplateVariable[];
  metadata: Record<string, unknown>;
}

export interface DirectiveSummary {
  id: string;
  name: string;
  description: string;
  tags: string[];
}

export interface DirectiveCreate {
  id: string;
  name: string;
  description: string;
  content: string;
  metadata?: Record<string, unknown>;
}

// ============================================================================
// Output Models
// ============================================================================

export interface ToolCall {
  tool_name: string;
  arguments: Record<string, unknown>;
  result: string | null;
  error: string | null;
}

export interface WorkerOutput {
  result: string;
  tool_calls: ToolCall[];
  iterations: number;
  status: string;
}

export interface Task {
  id: string;
  description: string;
  directive_id: string | null;
  dependencies: string[];
  metadata: Record<string, unknown>;
}

export interface Plan {
  tasks: Task[];
  context: string;
  success_criteria: string;
}

export type EvalDecisionType = "continue" | "loop";

export interface EvalDecision {
  decision: EvalDecisionType;
  reasoning: string;
  loop_target: string | null;
}

export interface SynthesisOutput {
  formatted_result: string;
  format_type: string;
  sources: string[];
  metadata: Record<string, unknown>;
}

export interface ExecutionResult {
  worker_outputs: WorkerOutput[];
  status: string;
  errors: string[];
}

export interface DocumentExtraction {
  doc_id: string;
  extracted_content: string;
  metadata: Record<string, unknown>;
}

export interface DocExResult {
  documents: DocumentExtraction[];
}

// ============================================================================
// Star Models
// ============================================================================

export interface BaseStar {
  id: string;
  name: string;
  type: StarType;
  directive_id: string;
  config: Record<string, unknown>;
  ai_generated: boolean;
  metadata: Record<string, unknown>;
}

export interface AtomicStar extends BaseStar {
  probe_ids: string[];
}

export interface WorkerStar extends AtomicStar {
  type: StarType.WORKER;
  max_iterations: number;
}

export interface PlanningStar extends AtomicStar {
  type: StarType.PLANNING;
}

export interface EvalStar extends AtomicStar {
  type: StarType.EVAL;
}

export interface SynthesisStar extends AtomicStar {
  type: StarType.SYNTHESIS;
}

export interface ExecutionStar extends BaseStar {
  type: StarType.EXECUTION;
  parallel: boolean;
}

export interface DocExStar extends BaseStar {
  type: StarType.DOCEX;
}

export type Star = WorkerStar | PlanningStar | EvalStar | SynthesisStar | ExecutionStar | DocExStar;

export interface StarSummary {
  id: string;
  name: string;
  type: StarType;
  directive_id: string;
}

export interface StarCreate {
  id: string;
  name: string;
  type: StarType;
  directive_id: string;
  probe_ids?: string[];
  config?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

// ============================================================================
// Node Models
// ============================================================================

export interface Position {
  x: number;
  y: number;
}

export interface BaseNode {
  id: string;
  type: NodeType;
  position: Position;
}

export interface StartNode extends BaseNode {
  type: NodeType.START;
  original_query: string | null;
  constellation_purpose: string | null;
}

export interface EndNode extends BaseNode {
  type: NodeType.END;
}

export interface StarNode extends BaseNode {
  type: NodeType.STAR;
  star_id: string;
  display_name: string | null;
  variable_bindings: Record<string, unknown>;
  requires_confirmation: boolean;
  confirmation_prompt: string | null;
}

export type Node = StartNode | EndNode | StarNode;

// ============================================================================
// Edge Model
// ============================================================================

export type EdgeCondition = "continue" | "loop";

export interface Edge {
  id: string;
  source: string;
  target: string;
  condition: EdgeCondition | null;
}

// ============================================================================
// Constellation Model
// ============================================================================

export interface Constellation {
  id: string;
  name: string;
  description: string;
  start: StartNode;
  end: EndNode;
  nodes: StarNode[];
  edges: Edge[];
  max_loop_iterations: number;
  max_retry_attempts: number;
  retry_delay_base: number;
  metadata: Record<string, unknown>;
}

export interface ConstellationSummary {
  id: string;
  name: string;
  description: string;
  node_count: number;
  tags: string[];
}

export interface ConstellationCreate {
  id: string;
  name: string;
  description: string;
  start: StartNode;
  end: EndNode;
  nodes: StarNode[];
  edges: Edge[];
  metadata?: Record<string, unknown>;
}

// ============================================================================
// Run Models
// ============================================================================

export type RunStatus = "running" | "awaiting_confirmation" | "completed" | "failed" | "cancelled";

export interface NodeOutput {
  node_id: string;
  star_id: string;
  status: "pending" | "running" | "completed" | "failed";
  started_at: string | null;
  completed_at: string | null;
  output: string | null;
  error: string | null;
  tool_calls: Record<string, unknown>[];
}

export interface Run {
  id: string;
  constellation_id: string;
  constellation_name: string;
  status: RunStatus;
  variables: Record<string, unknown>;
  started_at: string;
  completed_at: string | null;
  node_outputs: Record<string, NodeOutput>;
  final_output: string | null;
  error: string | null;
  awaiting_node_id: string | null;
  awaiting_prompt: string | null;
}

export interface RunSummary {
  id: string;
  constellation_id: string;
  constellation_name: string;
  status: string;
  started_at: string;
  completed_at: string | null;
}

export interface RunRequest {
  variables: Record<string, unknown>;
}

export interface ConfirmRequest {
  proceed: boolean;
  additional_context?: string;
}

export interface ConfirmResponse {
  run_id: string;
  status: string;
  message: string;
}

// ============================================================================
// SSE Event Types
// ============================================================================

export interface SSERunStarted {
  run_id: string;
  status: "running";
}

export interface SSENodeStarted {
  node_id: string;
  star_id: string;
  status: "running";
}

export interface SSENodeProgress {
  node_id: string;
  message: string;
}

export interface SSENodeCompleted {
  node_id: string;
  status: "completed";
  output: string;
}

export interface SSENodeFailed {
  node_id: string;
  status: "failed";
  error: string;
}

export interface SSEAwaitingConfirmation {
  run_id: string;
  node_id: string;
  prompt: string;
}

export interface SSERunCompleted {
  run_id: string;
  status: "completed";
  final_output: string;
}

export interface SSERunFailed {
  run_id: string;
  status: "failed";
  error: string;
}

export type SSEEvent =
  | { event: "run_started"; data: SSERunStarted }
  | { event: "node_started"; data: SSENodeStarted }
  | { event: "node_progress"; data: SSENodeProgress }
  | { event: "node_completed"; data: SSENodeCompleted }
  | { event: "node_failed"; data: SSENodeFailed }
  | { event: "awaiting_confirmation"; data: SSEAwaitingConfirmation }
  | { event: "run_completed"; data: SSERunCompleted }
  | { event: "run_failed"; data: SSERunFailed };

// ============================================================================
// API Response Wrappers
// ============================================================================

export interface DirectiveResponse {
  directive: Directive;
  warnings: string[];
}

export interface ErrorResponse {
  detail: string;
  error_code?: string;
}

// ============================================================================
// Probe (Read-Only from API)
// ============================================================================

export interface Probe {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}
