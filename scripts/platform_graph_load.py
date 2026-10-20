"""Run a reproducible synthetic traversal load check against platform graph code."""

import argparse
import json
import math
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from substrata.graph import dependency_paths
from substrata.platform.cascade import projection
from substrata.platform.database import build_engine
from substrata.platform.domain import Entity, GraphData, Link, Provenance
from substrata.platform.store import PlatformStore


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
            status="declared",
            provenance=provenance,
            valid_from=as_of,
        )
        for index in range(1, node_count)
    ]
    return GraphData(entities=entities, links=links)


def run_load(*, node_count: int, query_count: int, workers: int, database_url: str | None = None):
    as_of = datetime.now(UTC)
    data = synthetic_tree(node_count, as_of)
    graph = projection(data, as_of) if database_url is None else None
    depth = min(32, math.ceil(math.log2(node_count)) + 1)
    budget = min(100_000, max(10_000, node_count * 2))
    first_leaf = max(1, node_count // 2)
    leaves = list(range(first_leaf, node_count))

    store = None
    tenant_id = f"graph-load-{time.time_ns()}"
    if database_url is not None:
        store = PlatformStore(build_engine(database_url))
        store.provision(tenant_id, "Synthetic graph load", "load-harness")
        store.save(tenant_id, data, "load-harness", expected_version=0)

    def query(index):
        target = f"node-{leaves[index % len(leaves)]:05d}"
        started = time.perf_counter()
        result = (
            store.paths(
                tenant_id,
                "node-00000",
                target,
                version=1,
                traversal_as_of=as_of,
                max_depth=depth,
                max_paths=128,
                budget=budget,
            )
            if store is not None
            else dependency_paths(
                graph,
                "node-00000",
                target,
                max_depth=depth,
                max_paths=128,
                budget=budget,
            )
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        if not result.paths or result.truncated:
            raise RuntimeError(f"Synthetic path query did not complete for {target}.")
        return elapsed_ms

    try:
        query(0)  # Warm up the path through the same measured code path.
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            timings = list(pool.map(query, range(query_count)))
        elapsed = time.perf_counter() - started
    finally:
        if store is not None:
            store.engine.dispose()
    ordered = sorted(timings)
    p95_index = min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1)
    return {
        "data_label": "synthetic only",
        "backend": "postgresql-recursive-cte" if database_url else "in-memory-networkx",
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
    parser.add_argument(
        "--database-url",
        default=os.environ.get("SUBSTRATA_GRAPH_LOAD_DATABASE_URL"),
        help=(
            "Tenant-runtime PostgreSQL/psycopg URL. The schema must already be migrated; "
            "omit it to measure the offline NetworkX baseline."
        ),
    )
    args = parser.parse_args()
    if not 3 <= args.nodes <= 50000:
        parser.error("--nodes must be between 3 and 50000.")
    if not 1 <= args.queries <= 10000:
        parser.error("--queries must be between 1 and 10000.")
    if not 1 <= args.workers <= 64:
        parser.error("--workers must be between 1 and 64.")
    print(
        json.dumps(
            run_load(
                node_count=args.nodes,
                query_count=args.queries,
                workers=args.workers,
                database_url=args.database_url,
            )
        )
    )


if __name__ == "__main__":
    main()
