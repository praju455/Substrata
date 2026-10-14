"use client";

import cytoscape, { type Core, type StylesheetJson } from "cytoscape";
import { useEffect, useRef, useState } from "react";
import type { GraphData } from "./types";
import { dependencyDepths } from "./graph-layout";

export default function Network({
  graph,
  sharedIds,
  onSelect,
}: {
  graph: GraphData;
  sharedIds: string[];
  onSelect: (kind: "node" | "edge", id: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<Core | null>(null);
  const [all, setAll] = useState(false);
  const signature = JSON.stringify(graph);
  const shared = JSON.stringify(sharedIds);

  useEffect(() => {
    if (!container.current) return;
    const data: GraphData = JSON.parse(signature);
    const highlighted: string[] = JSON.parse(shared);
    const nodes = data.nodes.filter(
      (n) =>
        all ||
        !["Region", "AlternativeSupplier", "Event"].includes(n.node_type),
    );
    const visible = new Set(nodes.map((n) => n.id));
    const buckets: Record<number, typeof nodes> = {};
    const depths = dependencyDepths(data);
    const maximum = Math.max(1, ...depths.values());
    for (const node of nodes) {
      const depth = depths.get(node.id);
      const column = depth === undefined ? maximum + 1 : maximum - depth;
      (buckets[column] ??= []).push(node);
    }
    const positions = new Map<string, { x: number; y: number }>();
    for (const [column, items] of Object.entries(buckets)) {
      items.forEach((node, index) =>
        positions.set(node.id, {
          x: 80 + Number(column) * 200,
          y: 60 + index * 86,
        }),
      );
    }
    const style: StylesheetJson = [
      {
        selector: "node",
        style: {
          label: "data(name)",
          width: 30,
          height: 30,
          "background-color": "#6f42c1",
          "font-size": 11,
          color: "#3e384e",
          "text-wrap": "wrap",
          "text-max-width": "130px",
          "text-valign": "bottom",
          "text-margin-y": 8,
          "border-width": 2,
          "border-color": "#ffffff",
        },
      },
      {
        selector: 'node[node_type="Component"]',
        style: { shape: "round-rectangle", "background-color": "#7c879a" },
      },
      {
        selector: 'node[node_type="Plant"]',
        style: { shape: "hexagon", "background-color": "#168b83" },
      },
      {
        selector: 'node[node_type="Product"]',
        style: { shape: "diamond", "background-color": "#a583d6" },
      },
      {
        selector: 'node[node_type="Region"]',
        style: { shape: "rectangle", "background-color": "#a2a8b4" },
      },
      {
        selector: 'node[node_type="AlternativeSupplier"]',
        style: { shape: "pentagon", "background-color": "#c99432" },
      },
      {
        selector: 'node[node_type="Event"]',
        style: { shape: "triangle", "background-color": "#c0393e" },
      },
      {
        selector: "node.shared",
        style: {
          "background-color": "#c0393e",
          "border-color": "#ffe0e0",
          "border-width": 7,
          width: 39,
          height: 39,
        },
      },
      {
        selector: "edge",
        style: {
          width: 1.2,
          "line-color": "#b4a9c7",
          "target-arrow-color": "#b4a9c7",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          "arrow-scale": 0.7,
          "line-opacity": 0.65,
        },
      },
      {
        selector: 'edge[status="inferred"]',
        style: {
          "line-style": "dashed",
          "line-color": "#8051bc",
          "target-arrow-color": "#8051bc",
          width: 2.2,
        },
      },
      {
        selector: 'edge[status="confirmed"]',
        style: {
          width: 3,
          "line-color": "#168b83",
          "target-arrow-color": "#168b83",
        },
      },
      {
        selector: 'edge[status="rejected"], edge[status="expired"]',
        style: { opacity: 0.2, "line-style": "dotted" },
      },
      {
        selector: ":selected",
        style: {
          "overlay-color": "#6f42c1",
          "overlay-opacity": 0.15,
          "overlay-padding": 8,
        },
      },
    ];
    const cy = cytoscape({
      container: container.current,
      style,
      elements: [
        ...nodes.map((n) => ({
          data: n,
          position: positions.get(n.id),
          classes: highlighted.includes(n.id) ? "shared" : "",
        })),
        ...data.edges
          .filter((e) => visible.has(e.source) && visible.has(e.target))
          .map((e) => ({ data: e })),
      ],
      layout: { name: "preset", fit: true, padding: 35 },
      minZoom: 0.2,
      maxZoom: 2.5,
    });
    instance.current = cy;
    cy.on("tap", "node", (event) => onSelect("node", event.target.id()));
    cy.on("tap", "edge", (event) => onSelect("edge", event.target.id()));
    const observer = new ResizeObserver(() => {
      cy.resize();
      cy.fit(undefined, 35);
    });
    observer.observe(container.current);
    return () => {
      observer.disconnect();
      instance.current = null;
      cy.destroy();
    };
  }, [signature, shared, all, onSelect]);

  return (
    <>
      <div className="graph-toolbar">
        <span>Supplier sites → materials → products and plants</span>
        <div>
          <label>
            <input
              type="checkbox"
              checked={all}
              onChange={(e) => setAll(e.target.checked)}
            />{" "}
            All entities
          </label>
          <button
            className="quiet"
            onClick={() => instance.current?.fit(undefined, 35)}
          >
            Fit graph
          </button>
        </div>
      </div>
      <div
        ref={container}
        className="graph-canvas network-grid"
        role="img"
        aria-label="Interactive supplier network. Use the relationship list below for keyboard access."
      />
    </>
  );
}
