export type ImportField = {
  path: string;
  label: string;
  defaultUnit?: string;
};

export const importFields: Record<string, ImportField[]> = {
  entities: [
    { path: "id", label: "Internal ID" },
    { path: "kind", label: "Entity type" },
    { path: "name", label: "Legal or site name" },
    { path: "identifiers.supplier_code", label: "Supplier code" },
    { path: "identifiers.tax_id", label: "Tax identifier" },
    { path: "identifiers.duns", label: "D-U-N-S identifier" },
    { path: "identifiers.lei", label: "Legal Entity Identifier" },
    { path: "attributes.unit", label: "Material base unit" },
    { path: "attributes.country_code", label: "Country code" },
    { path: "measures.requalification_days", label: "Requalification time", defaultUnit: "day" },
    { path: "measures.daily_revenue", label: "Daily product revenue", defaultUnit: "USD/day" },
  ],
  inventory: [
    { path: "material_id", label: "Material ID" },
    { path: "plant_id", label: "Plant ID" },
    { path: "as_of", label: "Inventory observed at" },
    { path: "on_hand", label: "On-hand quantity", defaultUnit: "piece" },
    { path: "daily_consumption", label: "Daily consumption", defaultUnit: "piece/day" },
  ],
  links: [
    { path: "id", label: "Relationship ID" },
    { path: "source", label: "Source entity ID" },
    { path: "target", label: "Target entity ID" },
    { path: "type", label: "Relationship type" },
    { path: "status", label: "Relationship status" },
    { path: "confidence", label: "Evidence support score" },
    { path: "valid_from", label: "Valid from" },
    { path: "valid_to", label: "Valid until" },
    { path: "measures.share", label: "Supply share", defaultUnit: "fraction" },
  ],
  purchase_orders: [
    { path: "id", label: "Purchase-order ID" },
    { path: "supplier_id", label: "Supplier or site ID" },
    { path: "material_id", label: "Material ID" },
    { path: "plant_id", label: "Plant ID" },
    { path: "quantity", label: "Order quantity", defaultUnit: "piece" },
    { path: "expected_at", label: "Expected arrival" },
    { path: "status", label: "Order status" },
  ],
  boms: [
    { path: "material_id", label: "Material ID" },
    { path: "product_id", label: "Product ID" },
    { path: "quantity", label: "BOM quantity", defaultUnit: "piece" },
  ],
};

export function defaultUnits(target: string): Record<string, string> {
  return Object.fromEntries(
    (importFields[target] || [])
      .filter((field) => field.defaultUnit)
      .map((field) => [field.path, field.defaultUnit as string]),
  );
}
