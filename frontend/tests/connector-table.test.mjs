import assert from "node:assert/strict";
import test from "node:test";
import { connectorTable } from "../app/platform/connector-table.ts";

test("connector staging preserves Unicode, quoted fields, nested measures and missing cells", () => {
  const table = connectorTable([
    {
      id: "a",
      name: 'आपूर्तिकर्ता, "A"\nLine two',
      on_hand: { value: 5, unit: "kg" },
    },
    { id: "b", name: "Other" },
  ]);
  assert.deepEqual(table.columns, [
    "id",
    "name",
    "on_hand.value",
    "on_hand.unit",
  ]);
  assert.equal(table.row_count, 2);
  assert.equal(
    Buffer.from(table.content_base64, "base64").toString("utf8"),
    '"id","name","on_hand.value","on_hand.unit"\r\n"a","आपूर्तिकर्ता, ""A""\nLine two","5","kg"\r\n"b","Other","",""',
  );
});

test("connector preview enforces import bounds and rejects ambiguous columns", () => {
  assert.throws(() => connectorTable([]), /1 to 10000/);
  assert.throws(() => connectorTable([null]), /must be objects/);
  assert.throws(() => connectorTable([{ "a.b": 1, a: { b: 2 } }]), /collide/);
  assert.throws(() => connectorTable([{ value: "x".repeat(3000001) }]), /3 MB/);
  assert.throws(
    () =>
      connectorTable([
        Object.fromEntries(
          Array.from({ length: 101 }, (_, i) => ["field" + i, i]),
        ),
      ]),
    /100 columns/,
  );
});
