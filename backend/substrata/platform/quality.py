"""Graph-aware data completeness summaries for the tenant workspace."""

from datetime import UTC, datetime

import networkx as nx

from substrata.platform.cascade import projection
from substrata.platform.domain import Snapshot


def inventory_completeness(snapshot: Snapshot, *, as_of: datetime | None = None) -> dict:
    as_of = as_of or datetime.now(UTC)
    graph = projection(snapshot.data, as_of)
    kinds = {entity.id: entity.kind for entity in snapshot.data.entities}
    materials = sorted(id for id, kind in kinds.items() if kind == "Material")
    expected = set()
    for material_id in materials:
        if material_id not in graph:
            continue
        for reachable in nx.descendants(graph, material_id):
            if kinds.get(reachable) == "Plant":
                expected.add((material_id, reachable))
    rows = {(row.material_id, row.plant_id): row for row in snapshot.data.inventory}
    # Inventory outside the current active where-used graph is still reported;
    # it may be stale, but silently excluding it would overstate completeness.
    expected |= set(rows)
    missing_rows = sorted(expected - set(rows))
    incomplete = []
    for key in sorted(expected & set(rows)):
        row = rows[key]
        missing = [
            name
            for name, value in (
                ("on_hand", row.on_hand),
                ("daily_consumption", row.daily_consumption),
            )
            if value is None
        ]
        if missing:
            incomplete.append(
                {"material_id": key[0], "plant_id": key[1], "missing_fields": missing}
            )
    complete = len(expected) - len(missing_rows) - len(incomplete)
    return {
        "expected_rows": len(expected),
        "present_rows": len(rows),
        "complete_rows": max(0, complete),
        "missing_row_count": len(missing_rows),
        "missing_value_row_count": len(incomplete),
        "missing_rows": [
            {"material_id": material_id, "plant_id": plant_id}
            for material_id, plant_id in missing_rows[:100]
        ],
        "incomplete_rows": incomplete[:100],
        "truncated_details": len(missing_rows) > 100 or len(incomplete) > 100,
    }
