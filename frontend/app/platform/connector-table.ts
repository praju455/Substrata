// Convert bounded connector JSON into the existing UTF-8 CSV mapping workflow.

function flatten(
  value: unknown,
  prefix: string,
  result: Record<string, string>,
  depth = 0,
) {
  if (depth > 8)
    throw new Error("Connector rows exceed the supported nesting depth.");
  if (value !== null && typeof value === "object" && !Array.isArray(value)) {
    for (const [key, item] of Object.entries(value)) {
      if (!key.trim())
        throw new Error("Connector field names must be nonblank.");
      flatten(item, prefix ? prefix + "." + key : key, result, depth + 1);
    }
  } else if (prefix) {
    if (Object.hasOwn(result, prefix))
      throw new Error("Connector fields collide after flattening.");
    result[prefix] =
      value == null
        ? ""
        : typeof value === "object"
          ? JSON.stringify(value)
          : String(value);
  }
}

export function connectorTable(rows: unknown[]) {
  if (!rows.length || rows.length > 10000)
    throw new Error("Connector preview requires 1 to 10000 rows.");
  const flattened = rows.map((row) => {
    if (!row || typeof row !== "object" || Array.isArray(row))
      throw new Error("Connector rows must be objects.");
    const result: Record<string, string> = Object.create(null);
    flatten(row, "", result);
    return result;
  });
  const columns = [...new Set(flattened.flatMap((row) => Object.keys(row)))];
  if (!columns.length || columns.length > 100)
    throw new Error("Connector preview requires 1 to 100 columns.");
  const cell = (value: string) => '"' + value.replaceAll('"', '""') + '"';
  const csv = [
    columns.map(cell).join(","),
    ...flattened.map((row) =>
      columns.map((key) => cell(row[key] ?? "")).join(","),
    ),
  ].join("\r\n");
  const bytes = new TextEncoder().encode(csv);
  if (bytes.length > 3000000)
    throw new Error("Connector preview exceeds the 3 MB import limit.");
  let binary = "";
  for (let index = 0; index < bytes.length; index += 8192)
    binary += String.fromCharCode(...bytes.subarray(index, index + 8192));
  return {
    columns,
    content_base64: btoa(binary),
    row_count: rows.length,
    sample: flattened.slice(0, 5),
  };
}
