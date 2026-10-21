import assert from "node:assert/strict";
import test from "node:test";

import {
  humanizeAssistantLabel,
  safeSourceHref,
} from "../app/platform/assistant-utils.ts";

test("assistant source links allow only browser-safe HTTP URLs", () => {
  assert.equal(
    safeSourceHref("https://example.test/evidence"),
    "https://example.test/evidence",
  );
  assert.equal(safeSourceHref("record://assessment/abc"), null);
  assert.equal(safeSourceHref("javascript:alert(1)"), null);
  assert.equal(safeSourceHref("not a URL"), null);
});

test("assistant machine labels are readable", () => {
  assert.equal(humanizeAssistantLabel("likely_dependency"), "Likely dependency");
});
