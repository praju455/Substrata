import test from "node:test";
import assert from "node:assert/strict";
import { dependencyDepths } from "../app/graph-layout.ts";

test("tiers come from paths rather than supplier ID spelling", () => {
  const graph = {
    nodes: [
      { id: "factory", node_type: "Plant" },
      { id: "api", node_type: "Component" },
      { id: "arbitrary-supplier", node_type: "SupplierSite" },
      { id: "shared", node_type: "SupplierSite" },
    ],
    edges: [
      {
        source: "api",
        target: "factory",
        edge_type: "USED_IN",
        status: "declared",
      },
      {
        source: "arbitrary-supplier",
        target: "api",
        edge_type: "SUPPLIES",
        status: "declared",
      },
      {
        source: "arbitrary-supplier",
        target: "shared",
        edge_type: "DEPENDS_ON",
        status: "inferred",
      },
      {
        source: "shared",
        target: "arbitrary-supplier",
        edge_type: "DEPENDS_ON",
        status: "inferred",
      },
    ],
  };
  assert.deepEqual(Object.fromEntries(dependencyDepths(graph)), {
    factory: 0,
    api: 1,
    "arbitrary-supplier": 2,
    shared: 3,
  });
  graph.edges[2].status = "rejected";
  assert.equal(dependencyDepths(graph).has("shared"), false);
});
