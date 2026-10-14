"""Industry-neutral contracts. Measurements always carry source and units."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")]
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Provenance(Contract):
    uri: str = Field(min_length=1, max_length=2048)
    observed_at: AwareDatetime
    kind: Literal["synthetic", "uploaded", "connector", "public", "supplier", "assumption"]
    note: str = Field(min_length=1, max_length=2000)


class Measure(Contract):
    value: float = Field(ge=0, allow_inf_nan=False)
    unit: Label
    provenance: Provenance


class Entity(Contract):
    id: Identifier
    kind: Literal["Supplier", "Site", "Material", "Product", "Plant", "Region"]
    name: Label
    identifiers: dict[str, str] = Field(default_factory=dict)
    attributes: dict[str, str] = Field(default_factory=dict)
    measures: dict[str, Measure] = Field(default_factory=dict)
    provenance: Provenance


class Citation(Contract):
    document_id: Identifier
    passage: str = Field(min_length=1, max_length=10000)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    stance: Literal["supports", "contradicts"] = "supports"

    @model_validator(mode="after")
    def span(self):
        if self.end <= self.start or self.end - self.start != len(self.passage):
            raise ValueError("Citation offsets must match the exact passage length.")
        return self


class Link(Contract):
    id: Identifier
    source: Identifier
    target: Identifier
    type: Literal["SUPPLIES", "DEPENDS_ON", "USED_IN", "OWNED_BY", "LOCATED_IN"]
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    status: Literal["declared", "inferred", "confirmed", "rejected", "expired"]
    evidence: list[Citation] = Field(default_factory=list)
    provenance: Provenance
    valid_from: AwareDatetime
    valid_to: AwareDatetime | None = None
    measures: dict[str, Measure] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_link(self):
        if self.source == self.target:
            raise ValueError("A link must have distinct endpoints.")
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("Link expiry must follow its start.")
        if self.status == "inferred" and not any(e.stance == "supports" for e in self.evidence):
            raise ValueError("Inferred links require supporting passage citations.")
        return self


class Inventory(Contract):
    material_id: Identifier
    plant_id: Identifier
    as_of: AwareDatetime
    on_hand: Measure | None = None
    daily_consumption: Measure | None = None


class PurchaseOrder(Contract):
    id: Identifier
    supplier_id: Identifier
    material_id: Identifier
    plant_id: Identifier
    expected_at: AwareDatetime
    quantity: Measure
    status: Literal["open", "in_transit", "received", "cancelled"]


class BomItem(Contract):
    material_id: Identifier
    product_id: Identifier
    quantity: Measure


class GraphData(Contract):
    entities: list[Entity] = Field(default_factory=list, max_length=50000)
    links: list[Link] = Field(default_factory=list, max_length=100000)
    inventory: list[Inventory] = Field(default_factory=list)
    purchase_orders: list[PurchaseOrder] = Field(default_factory=list)
    boms: list[BomItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def references(self):
        kinds = {e.id: e.kind for e in self.entities}
        if len(kinds) != len(self.entities) or len({e.id for e in self.links}) != len(self.links):
            raise ValueError("Entity and link IDs must be unique within a tenant snapshot.")
        for link in self.links:
            if link.source not in kinds or link.target not in kinds:
                raise ValueError("Every link endpoint must exist in the same snapshot.")
        for row in [*self.inventory, *self.purchase_orders]:
            if kinds.get(row.material_id) != "Material" or kinds.get(row.plant_id) != "Plant":
                raise ValueError("Inventory and orders require a material and a plant.")
        for order in self.purchase_orders:
            if kinds.get(order.supplier_id) not in {"Supplier", "Site"}:
                raise ValueError("Orders require a supplier or supplier site.")
        for bom in self.boms:
            if kinds.get(bom.material_id) != "Material" or kinds.get(bom.product_id) != "Product":
                raise ValueError("BOMs require a material and a product.")
        keys = [(i.material_id, i.plant_id) for i in self.inventory]
        if len(set(keys)) != len(keys):
            raise ValueError("Inventory must be unique per material and plant.")
        if len({p.id for p in self.purchase_orders}) != len(self.purchase_orders):
            raise ValueError("Purchase order IDs must be unique.")
        return self


class Snapshot(Contract):
    tenant_id: Identifier
    version: int = Field(ge=1)
    recorded_at: datetime
    sha256: str
    data: GraphData
