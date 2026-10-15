"""Multiple clearly synthetic industries with identical platform contracts."""

from datetime import UTC, datetime, timedelta
from random import Random

from substrata.platform.domain import (
    BomItem,
    Entity,
    GraphData,
    Inventory,
    Link,
    Measure,
    Provenance,
    PurchaseOrder,
)

INDUSTRIES = {
    "automotive": ("Controller module", "Road vehicle", "piece", 90),
    "pharma": ("Active ingredient", "Medicine batch", "kg", 120),
    "food": ("Cocoa ingredient", "Confectionery batch", "kg", 21),
}


def generate(industry: str, *, seed: int = 42, as_of: datetime | None = None):
    if industry not in INDUSTRIES:
        raise ValueError("Industry must be automotive, pharma or food.")
    as_of = as_of or datetime.now(UTC)
    part, product, unit, qualification = INDUSTRIES[industry]
    provenance = Provenance(
        uri=f"synthetic://{industry}/{seed}",
        observed_at=as_of,
        kind="synthetic",
        note="Invented multi-industry fixture; not customer data.",
    )
    rng = Random(seed)

    def measure(value, unit):
        return Measure(value=value, unit=unit, provenance=provenance)

    entities = [
        Entity(
            id="upstream",
            kind="Site",
            name=f"Shared {industry} processing site",
            provenance=provenance,
        ),
        Entity(
            id="plant",
            kind="Plant",
            name=f"{industry.title()} production plant",
            provenance=provenance,
        ),
        Entity(
            id="product",
            kind="Product",
            name=product,
            provenance=provenance,
            measures={"daily_revenue": measure(50000, "USD/day")},
        ),
        Entity(
            id="material",
            kind="Material",
            name=part,
            provenance=provenance,
            attributes={"unit": unit},
            measures={"requalification_days": measure(qualification, "day")},
        ),
    ]
    links = []
    for index in range(3):
        supplier = f"supplier-{index}"
        entities.append(
            Entity(
                id=supplier,
                kind="Supplier",
                name=f"Synthetic {industry} supplier {index + 1}",
                provenance=provenance,
            )
        )
        links.extend(
            [
                Link(
                    id=f"dependency-{index}",
                    source=supplier,
                    target="upstream",
                    type="DEPENDS_ON",
                    confidence=1,
                    status="declared",
                    provenance=provenance,
                    valid_from=as_of,
                ),
                Link(
                    id=f"supply-{index}",
                    source=supplier,
                    target="material",
                    type="SUPPLIES",
                    confidence=1,
                    status="declared",
                    provenance=provenance,
                    valid_from=as_of,
                    measures={
                        "share": measure(1 / 3, "fraction"),
                        "lead_time_days": measure(7, "day"),
                    },
                ),
            ]
        )
    for target in ("product", "plant"):
        links.append(
            Link(
                id=f"used-{target}",
                source="material",
                target=target,
                type="USED_IN",
                confidence=1,
                status="declared",
                provenance=provenance,
                valid_from=as_of,
            )
        )
    on_hand = 1200 if industry == "automotive" else rng.randint(500, 1500)
    return GraphData(
        entities=entities,
        links=links,
        inventory=[
            Inventory(
                material_id="material",
                plant_id="plant",
                as_of=as_of,
                on_hand=measure(on_hand, unit),
                daily_consumption=measure(100, f"{unit}/day"),
            )
        ],
        purchase_orders=[
            PurchaseOrder(
                id="po-1",
                supplier_id="supplier-0",
                material_id="material",
                plant_id="plant",
                expected_at=as_of + timedelta(days=3),
                quantity=measure(600, unit),
                status="in_transit",
            )
        ],
        boms=[BomItem(material_id="material", product_id="product", quantity=measure(1, unit))],
    )
