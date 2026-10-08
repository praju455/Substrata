"""Validated, synthetic entity attributes persisted inside graph nodes."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter

Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]
Country = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
Days = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class Attributes(BaseModel):
    """Replace the entire immutable payload when editing a node."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ProductAttributes(Attributes):
    node_type: Literal["Product"] = "Product"
    product_family: Label
    manufacturer_id: Label


class ComponentAttributes(Attributes):
    node_type: Literal["Component"] = "Component"
    part_number: Label
    description: Label
    unit: Label
    requalification_days: Days | None = None


class SupplierSiteAttributes(Attributes):
    node_type: Literal["SupplierSite"] = "SupplierSite"
    legal_entity_name: Label
    site_name: Label
    country_code: Country
    identifiers: dict[Label, Label] = Field(default_factory=dict)


class PlantAttributes(Attributes):
    node_type: Literal["Plant"] = "Plant"
    country_code: Country
    capacity_unit: Label


class RegionAttributes(Attributes):
    node_type: Literal["Region"] = "Region"
    region_type: Label
    geometry_ref: Label | None = None


class EventAttributes(Attributes):
    node_type: Literal["Event"] = "Event"
    event_type: Label
    observed_at: AwareDatetime
    source_id: Label
    severity: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class AlternativeSupplierAttributes(Attributes):
    node_type: Literal["AlternativeSupplier"] = "AlternativeSupplier"
    supplier_site_id: Label
    component_id: Label
    qualification_status: Literal["unqualified", "pending", "qualified", "rejected"]


NodeAttributes = Annotated[
    ProductAttributes
    | ComponentAttributes
    | SupplierSiteAttributes
    | PlantAttributes
    | RegionAttributes
    | EventAttributes
    | AlternativeSupplierAttributes,
    Field(discriminator="node_type"),
]
NODE_ATTRIBUTES = TypeAdapter(NodeAttributes)
