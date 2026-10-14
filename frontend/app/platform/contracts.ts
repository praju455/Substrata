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
  documents: { id: string; provenance: Provenance }[];
  audit: { valid: boolean; count: number; head: string } | null;
};
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
  as_of: string;
  truncated: boolean;
};
