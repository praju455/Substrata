"""Run a reproducible synthetic traversal load check against platform graph code."""

import argparse
import json
import math
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from substrata.graph import dependency_paths
from substrata.platform.cascade import projection
from substrata.platform.domain import Entity, GraphData, Link, Provenance


def synthetic_tree(node_count: int, as_of: datetime):
    provenance = Provenance(
        uri="synthetic://platform-graph-load",
        observed_at=as_of,
        kind="synthetic",
        note="Invented balanced tree for local traversal load testing.",
    )
    entities = [
        Entity(
            id=f"node-{index:05d}",
            kind="Site",
            name=f"Synthetic site {index}",
            provenance=provenance,
        )
        for index in range(node_count)
    ]
    links = [
        Link(
            id=f"tree-edge-{index:05d}",
            source=f"node-{index:05d}",
            target=f"node-{(index - 1) // 2:05d}",
            type="DEPENDS_ON",
            confidence=0.95,
            status="confirmed",
            provenance=provenance,
            valid_from=as_of,
        )
        for index in range(1, node_count)
    ]
    return GraphData(entities=entities, links=links)


def run_load(*, node_count: int, query_count: int, workers: int):
    as_of = datetime.now(UTC)
    data = synthetic_tree(node_count, as_of)
    graph = projection(data, as_of)
    depth = min(32, math.ceil(math.log2(node_count)) + 1)
    budget = min(100_000, max(10_000, node_count * 2))
    first_leaf = max(1, node_count // 2)
    leaves = list(range(first_leaf, node_count))

    def query(index):
        target = f"node-{leaves[index % len(leaves)]:05d}"
        started = time.perf_counter()
        result = dependency_paths(
            graph,
            "node-00000",
            target,
            max_depth=depth,
            max_paths=128,
            budget=budget,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        if not result.paths or result.truncated:
            raise RuntimeError(f"Synthetic path query did not complete for {target}.")
        return elapsed_ms

    query(0)  # Warm up the path through the same measured code path.
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        timings = list(pool.map(query, range(query_count)))
    elapsed = time.perf_counter() - started
    ordered = sorted(timings)
    p95_index = min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1)
    return {
        "data_label": "synthetic only",
        "nodes": node_count,
        "edges": len(data.links),
        "queries": query_count,
        "workers": workers,
        "elapsed_seconds": round(elapsed, 6),
        "queries_per_second": round(query_count / elapsed, 2),
        "latency_ms": {
            "p50": round(statistics.median(ordered), 4),
            "p95": round(ordered[p95_index], 4),
            "max": round(max(ordered), 4),
        },
        "limits": {"max_depth": depth, "work_budget_per_query": budget},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=int, default=4095)
    parser.add_argument("--queries", type=int, default=200)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if not 3 <= args.nodes <= 50000:
        parser.error("--nodes must be between 3 and 50000.")
    if not 1 <= args.queries <= 10000:
        parser.error("--queries must be between 1 and 10000.")
    if not 1 <= args.workers <= 64:
        parser.error("--workers must be between 1 and 64.")
    print(
        json.dumps(run_load(node_count=args.nodes, query_count=args.queries, workers=args.workers))
    )


if __name__ == "__main__":
    main()
