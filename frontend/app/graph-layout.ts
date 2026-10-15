import type { GraphData } from "./types";

/** Dependency depth relative to products/plants, derived from relationships. */
export function dependencyDepths(graph: GraphData): Map<string, number> {
  const depths = new Map<string, number>();
  const queue = graph.nodes
    .filter((n) => ["Plant", "Product"].includes(n.node_type))
    .map((n) => n.id);
  for (const id of queue) depths.set(id, 0);
  const upstream = new Map<string, string[]>();
  for (const edge of graph.edges) {
    if (
      ["rejected", "expired"].includes(edge.status) ||
      edge.edge_type === "LOCATED_IN"
    )
      continue;
    const reverse = ["SUPPLIES", "USED_IN"].includes(edge.edge_type);
    const from = reverse ? edge.target : edge.source;
    const to = reverse ? edge.source : edge.target;
    upstream.set(from, [...(upstream.get(from) || []), to]);
  }
  for (let index = 0; index < queue.length; index++) {
    const id = queue[index];
    const depth = depths.get(id)!;
    for (const next of upstream.get(id) || []) {
      if (!depths.has(next)) {
        depths.set(next, depth + 1);
        queue.push(next);
      }
    }
  }
  return depths;
}
