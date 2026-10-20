import assert from "node:assert/strict";
import test from "node:test";
import { defaultUnits, importFields } from "../app/platform/import-fields.ts";

test("import mapping exposes identifiers, revenue, validity and per-field units", () => {
  const paths = (target) => importFields[target].map((field) => field.path);
  assert(paths("entities").includes("identifiers.duns"));
  assert(paths("entities").includes("measures.daily_revenue"));
  assert(paths("links").includes("valid_to"));
  assert(paths("links").includes("measures.share"));
  assert.equal(defaultUnits("entities")["measures.daily_revenue"], "USD/day");
  assert.equal(defaultUnits("inventory").daily_consumption, "piece/day");
  assert.equal(defaultUnits("links")["measures.share"], "fraction");
});
