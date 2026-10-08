export type Citation = {
  id: string;
  quote: string;
  stance: string;
  source_uri: string;
  source_kind: string;
  sha256: string;
};
export type GraphNode = {
  id: string;
  name: string;
  node_type: string;
  attributes: Record<string, unknown>;
  synthetic: boolean;
};
export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  edge_type: string;
  status: string;
  confidence: number;
  evidence: Citation[];
};
export type GraphData = {
  version: number;
  as_of: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
};
export type Impact = {
  component_id: string;
  component_name: string;
  plant_id: string;
  plant_name: string;
  status: string;
  reason: string | null;
  unit: string;
  on_hand: number | null;
  in_transit: number | null;
  daily_consumption: number | null;
  cover_days: number | null;
  requalification_days: number | null;
  exposure_window: number | null;
  priority: number | null;
  path_confidence: number;
  evidence_ids: string[];
  paths: string[][];
  truncated: boolean;
};
export type Scenario = {
  id: string;
  event_id: string;
  status: string;
  versions: Record<string, unknown>;
  report: {
    source_id: string;
    formula_version: string;
    impacts: Impact[];
    truncated: boolean;
  };
};
export type Action = {
  id: string;
  scenario_id: string;
  kind: string;
  title: string;
  cost: number;
  duration_days: number;
  risk: number;
  rank_score: number;
  policy: string;
  status: string;
  rationale: string;
  payload: Record<string, unknown>;
};
export type AuditEvent = {
  sequence: number;
  previous_hash: string;
  payload_hash: string;
  event_type: string;
  actor: string;
  timestamp: string;
  payload: Record<string, unknown>;
};
export type StreamEvent = {
  id: number;
  event_type: string;
  timestamp: string;
  payload: Record<string, unknown>;
};
export type Workspace = {
  generation: string;
  synthetic: true;
  llm: {
    mode: "gemini" | "mock";
    primary: LLMProvider;
    backup: LLMProvider | null;
    last_attempts: {
      provider: string;
      model: string;
      status: "completed" | "failed";
      error_code: string | null;
      latency_ms: number;
    }[];
  };
  replay: { active: boolean; processed: number; total: number };
  graph: GraphData;
  tier1_ids: string[];
  shared_dependencies: {
    node_id: string;
    name: string;
    supplier_ids: string[];
  }[];
  scenarios: Scenario[];
  actions: Action[];
  audit_events: AuditEvent[];
  audit: {
    valid: boolean;
    count: number;
    head: string;
    error_sequence: number | null;
  };
  confirmations: {
    id: string;
    status: string;
    confidence: number;
    quote: string;
    edge_id: string;
  }[];
  events: {
    id: string;
    status: string;
    payload: { title: string; entity: string };
    candidates: { node_id: string; score: number }[];
  }[];
  evaluation: { id: string; metrics: Record<string, number> }[];
};

export type LLMProvider = {
  provider: string;
  model: string;
  credential_configured: boolean;
};
