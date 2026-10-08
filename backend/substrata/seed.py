"""Deterministic, explicitly synthetic fixtures; truth is never mapper input."""

import hashlib
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from substrata.erp_models import (
    BomItem,
    Dataset,
    LeadTime,
    PlantStock,
    PurchasingDocument,
    VendorMaster,
)
from substrata.models import EvidenceRecord, GraphEdge, GraphNode, SourceSnapshot

AS_OF = datetime(2025, 10, 22, 9, tzinfo=UTC)
DATASET = "synthetic-v1"
INVENTORY = "inventory-v1"
SEED = 42


def canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def generate_fixture() -> tuple[dict, dict, list[dict], list[dict]]:
    """Freeze the documented minimum: 1 product, 8 parts, 12 sites, 2 plants."""
    rng = random.Random(SEED)
    nodes, edges = [], []

    def add_node(node_id, kind, name, **attributes):
        nodes.append(
            {
                "id": node_id,
                "node_type": kind,
                "name": name,
                "attributes": {"node_type": kind, **attributes},
            }
        )

    def add_edge(source, target, kind, hidden=False, **fields):
        types = {item["id"]: item["node_type"] for item in nodes}
        edges.append(
            {
                "id": f"{kind.lower()}_{source}_{target}",
                "from_node_id": source,
                "to_node_id": target,
                "from_node_type": types[source],
                "to_node_type": types[target],
                "edge_type": kind,
                "hidden": hidden,
                "confidence": 1.0,
                **fields,
            }
        )

    for region, name in enumerate(["India", "Malaysia", "Netherlands", "Mexico"]):
        add_node(f"region_{region}", "Region", name, region_type="country")
    site_names = [
        "Aster Mobility",
        "Birch Controls",
        "Cedar Electronics",
        "Delta Systems",
        "Elm Devices",
        "Fern Components",
        "Cobalt Assemblies",
        "Indigo Fabrication",
        "Violet Circuits",
        "Silver Materials",
        "Meridian Semiconductors",
        "Orion Devices",
    ]
    site_ids = (
        [f"site_t1_{i}" for i in range(6)]
        + [f"site_t2_{i}" for i in range(4)]
        + ["site_shared_source", "site_other_source"]
    )
    countries = ["IN", "MY", "NL", "MX"]
    for index, (site_id, name) in enumerate(zip(site_ids, site_names, strict=True)):
        add_node(
            site_id,
            "SupplierSite",
            name,
            legal_entity_name=name,
            site_name=f"{name} synthetic facility",
            country_code=countries[index % 4],
            identifiers={"synthetic_id": site_id},
        )
        add_edge(site_id, f"region_{index % 4}", "LOCATED_IN")
    add_node(
        "product_controller",
        "Product",
        "Atlas vehicle controller",
        product_family="automotive electronics",
        manufacturer_id="synthetic_oem",
    )
    for index, name in enumerate(["Pune assembly", "Monterrey assembly"]):
        add_node(
            f"plant_{index}",
            "Plant",
            name,
            country_code=["IN", "MX"][index],
            capacity_unit="controller/day",
        )
        add_edge(f"plant_{index}", f"region_{[0, 3][index]}", "LOCATED_IN")
    for index in range(8):
        component = f"component_{index}"
        add_node(
            component,
            "Component",
            ["Power module", "Brake controller", "Sensor module"][index]
            if index < 3
            else f"Controller input {index + 1}",
            part_number=f"SYN-{index + 1:03}",
            description="Invented automotive component",
            unit="piece",
            requalification_days=90 if index < 3 else 30,
        )
        add_edge(f"site_t1_{index % 6}", component, "SUPPLIES", share=1, lead_time_days=10)
        add_edge(component, "product_controller", "USED_IN", bom_quantity=1, unit="piece")
        for plant in range(2):
            add_edge(component, f"plant_{plant}", "USED_IN", bom_quantity=1, unit="piece")
    for index in range(6):
        add_edge(f"site_t1_{index}", f"site_t2_{index if index < 3 else 3}", "OWNED_BY")
    for index in range(4):
        add_edge(
            f"site_t2_{index}",
            "site_shared_source" if index < 3 else "site_other_source",
            "OWNED_BY",
            hidden=True,
        )
    for index in range(5):
        add_node(
            f"alternative_{index}",
            "AlternativeSupplier",
            f"Candidate source {index + 1}",
            supplier_site_id=f"site_t1_{(index + 3) % 6}",
            component_id=f"component_{index % 3}",
            qualification_status="pending" if index < 3 else "qualified",
        )
    manifest = {
        "seed": SEED,
        "generator_version": "1.0",
        "dataset_version": DATASET,
        "inventory_snapshot_id": INVENTORY,
        "graph_version": 1,
        "as_of": AS_OF.isoformat(),
        "synthetic": True,
        "scope": "Invented ownership/control dependency, not a real supplier map",
    }
    truth = {"manifest": manifest, "nodes": nodes, "edges": edges}
    declared = {
        "manifest": manifest,
        "nodes": nodes,
        "edges": [
            {k: v for k, v in edge.items() if k != "hidden"} for edge in edges if not edge["hidden"]
        ],
        "stock": [
            {
                "component_id": f"component_{i}",
                "plant_id": f"plant_{p}",
                "on_hand": 1200 if i < 3 else rng.randint(1800, 3000),
                "in_transit": 600 if i < 3 else 200,
                "daily_consumption": 100,
                "unit": "piece",
                "requalification_days": 90 if i < 3 else 30,
            }
            for i in range(8)
            for p in range(2)
        ],
    }
    corpus = []
    claims = [
        (site_names[6 + i], site_names[10 if i < 3 else 11], reliability)
        for i, reliability in enumerate([0.90, 0.86, 0.55, 0.50])
    ]
    claims.append((site_names[9], site_names[10], 0.30))
    for index, (source, target, reliability) in enumerate(claims):
        quote = f"{source} is owned by {target}."
        corpus.append(
            {
                "id": f"evidence_{index}",
                "text": f"SYNTHETIC {'filing' if index < 4 else 'unverified rumour'}. {quote} "
                "This text is invented for the demo.",
                "reliability": reliability,
            }
        )
    corpus.extend(
        [
            {
                "id": "distractor_region",
                "text": "SYNTHETIC news. Aster Mobility and Meridian "
                "Semiconductors attend the same industry fair. Geography is not proof of supply.",
                "reliability": 0.7,
            },
            {
                "id": "distractor_name",
                "text": "SYNTHETIC profile. Meridian Logistics ships furniture "
                "and is unrelated to Meridian Semiconductors.",
                "reliability": 0.8,
            },
        ]
    )
    events = [
        {
            "id": f"event_{i}",
            "title": title,
            "entity": entity,
            "severity": severity,
            "observed_at": (AS_OF + timedelta(days=i)).isoformat(),
            "synthetic": True,
            "event_type": "supply_disruption",
            "source_id": "synthetic-event-replay-v1",
            "description": "Invented replay inspired by semiconductor disruption context; "
            "no claim about a real company's inventory or supplier relationships.",
        }
        for i, (title, entity, severity) in enumerate(
            [
                ("Semiconductor output disruption", "Meridian Semiconductors", 0.9),
                ("Alternative capacity review", "Orion Devices", 0.4),
                ("Regional shipping notice", "Malaysia", 0.3),
                ("Ambiguous facility notice", "Meridian", 0.5),
                ("Assembly monitoring update", "Pune assembly", 0.2),
                ("Supplier recovery update", "Silver Materials", 0.25),
            ]
        )
    ]
    return declared, truth, corpus, events


def write_fixtures(directory: Path) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    fixture, truth, corpus, events = generate_fixture()
    for name, value in [
        ("scenario.json", fixture),
        ("true_graph.json", truth),
        ("corpus.json", corpus),
        ("events.json", events),
    ]:
        (directory / name).write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return hashlib.sha256(canonical(fixture).encode()).hexdigest()


def seed_database(engine: Engine, directory: Path) -> str:
    """Reset only this synthetic database, atomically, through checked-in migrations."""
    fixture = json.loads((directory / "scenario.json").read_text(encoding="utf-8"))
    corpus = json.loads((directory / "corpus.json").read_text(encoding="utf-8"))
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0001_database_baseline")
        command.upgrade(config, "head")
        with Session(connection) as session:
            for item in fixture["nodes"]:
                session.add(
                    GraphNode(**item, graph_version=1, normalized_name=item["name"].casefold())
                )
            session.add(
                Dataset(id=DATASET, graph_version=1, inventory_snapshot_id=INVENTORY, as_of=AS_OF)
            )
            session.flush()
            for item in corpus:
                session.add(
                    SourceSnapshot(
                        id=f"source_{item['id']}",
                        source_kind="synthetic",
                        source_uri=f"synthetic://corpus/{item['id']}",
                        observed_at=AS_OF,
                        content_sha256=hashlib.sha256(item["text"].encode()).hexdigest(),
                        permitted_excerpt=item["text"],
                        license_note="Invented demo fixture.",
                    )
                )
            for i in range(6):
                session.add(
                    VendorMaster(
                        id=f"vendor_{i}",
                        dataset_version=DATASET,
                        supplier_site_id=f"site_t1_{i}",
                        graph_version=1,
                        vendor_name=f"Synthetic vendor {i}",
                    )
                )
            session.flush()
            for item in corpus:
                session.add(
                    EvidenceRecord(
                        id=item["id"],
                        source_snapshot_id=f"source_{item['id']}",
                        claim=item["text"],
                        reliability=item["reliability"],
                        recency_days=0,
                    )
                )
            for item in fixture["edges"]:
                session.add(GraphEdge(**item, graph_version=1, status="declared", valid_from=AS_OF))
            for i in range(8):
                session.add(
                    BomItem(
                        id=f"bom_{i}",
                        dataset_version=DATASET,
                        graph_version=1,
                        component_id=f"component_{i}",
                        product_id="product_controller",
                        quantity=1,
                        unit="piece",
                    )
                )
                session.add(
                    LeadTime(
                        dataset_version=DATASET,
                        component_id=f"component_{i}",
                        graph_version=1,
                        requalification_days=90 if i < 3 else 30,
                        provenance="Synthetic fixture assumption",
                    )
                )
            for index, item in enumerate(fixture["stock"]):
                session.add(
                    PlantStock(
                        dataset_version=DATASET,
                        graph_version=1,
                        component_id=item["component_id"],
                        plant_id=item["plant_id"],
                        inventory_snapshot_id=INVENTORY,
                        as_of=AS_OF,
                        on_hand=item["on_hand"],
                        daily_consumption=item["daily_consumption"],
                        unit=item["unit"],
                    )
                )
                session.add(
                    PurchasingDocument(
                        id=f"po_{index}",
                        dataset_version=DATASET,
                        graph_version=1,
                        vendor_id=f"vendor_{int(item['component_id'].split('_')[-1]) % 6}",
                        component_id=item["component_id"],
                        plant_id=item["plant_id"],
                        quantity=item["in_transit"],
                        unit=item["unit"],
                        status="in_transit",
                        expected_at=AS_OF + timedelta(days=3),
                    )
                )
            session.flush()
    return hashlib.sha256(canonical(fixture).encode()).hexdigest()
