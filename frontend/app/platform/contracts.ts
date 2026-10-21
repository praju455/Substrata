export type Provenance = {
  uri: string;
  observed_at: string;
  kind: string;
  note: string;
};
export type Measure = { value: number; unit: string; provenance: Provenance };
export type Entity = {
  id: string;
  kind: string;
  name: string;
  identifiers: Record<string, string>;
  attributes: Record<string, string>;
  measures: Record<string, Measure>;
  provenance: Provenance;
};
export type Link = {
  id: string;
  source: string;
  target: string;
  type: string;
  confidence: number;
  status: string;
  evidence: { document_id: string; passage: string; stance: string }[];
  valid_from: string;
  valid_to: string | null;
  provenance: Provenance;
  confidence_provenance: {
    method: "rule" | "calibrated_scorer";
    scorer_version: string;
    calibrated: boolean;
    feature_version: string;
    prompt_version: string | null;
    evaluation_scope: string | null;
    evaluation_metrics: Record<string, number>;
    synthetic_evaluation: boolean | null;
  } | null;
};
export type Graph = {
  entities: Entity[];
  links: Link[];
  inventory: {
    material_id: string;
    plant_id: string;
    on_hand: Measure | null;
    daily_consumption: Measure | null;
  }[];
  purchase_orders: unknown[];
  boms: unknown[];
};
export type Frozen = {
  version: number;
  recorded_at: string;
  sha256: string;
  data: Graph;
};
export type RecordItem = {
  id: string;
  kind: string;
  status: string;
  created_at: string;
  payload: Record<string, unknown>;
};
export type Workspace = {
  identity: { subject: string; tenant_id: string; roles: string[] };
  organisation: {
    name: string;
    version: number;
    policy: Record<string, unknown>;
  } | null;
  snapshot: Frozen | null;
  records: RecordItem[];
  jobs?: RecordItem[];
  models?: RecordItem[];
  documents: { id: string; provenance: Provenance }[];
  audit: { valid: boolean; count: number; head: string } | null;
  quality: {
    inventory: {
      expected_rows: number;
      present_rows: number;
      complete_rows: number;
      missing_row_count: number;
      missing_value_row_count: number;
      truncated_details: boolean;
    } | null;
  };
};
export type RecordPage = { items: RecordItem[]; next_cursor: string | null };
export type Impact = {
  material_name: string;
  plant_name: string;
  status: string;
  reason: string | null;
  cover_days: number | null;
  requalification_days: number | null;
  exposure_days_range: number[] | null;
  confidence_bounds: number[];
  revenue: { value_range: number[]; unit: string }[];
};
export type Report = {
  impacts: Impact[];
  shared_dependencies: { id: string; name: string; supplier_ids: string[] }[];
  range_assumption: string;
  graph_version: number;
  graph_sha256: string;
  evidence_sha256: string;
  formula_version: string;
  source_id: string;
  severity: number;
  as_of: string;
  truncated: boolean;
};
export type AssistantSource = {
  id: string;
  title: string;
  uri: string;
  excerpt: string;
  source_type: string;
  status: "known" | "inferred" | "unknown";
  observed_at: string | null;
  retrieved_at: string;
  sha256: string;
  relevance: number;
};
export type AssistantClaim = {
  statement: string;
  status: "known" | "inferred" | "unknown";
  source_ids: string[];
};
export type AssistantResponse = {
  verdict:
    | "likely_dependency"
    | "unlikely_dependency"
    | "conflicting_evidence"
    | "insufficient_evidence";
  answer: string;
  claims: AssistantClaim[];
  uncertainties: string[];
  next_step: string;
  sources: AssistantSource[];
  graph_version: number | null;
  model: { provider: string; model: string };
  retrieval: {
    internal_source_count: number;
    web_source_count: number;
    web_attempted: boolean;
    web_query: string | null;
    vector_database_used: boolean;
  };
  prompt_version: string;
  read_only: true;
};
