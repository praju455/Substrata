import assert from "node:assert/strict";
import test from "node:test";
import { reportSnapshot } from "../app/platform/report-snapshot.ts";

test("saved assessment exports keep the original graph after supplier replies or history selection", () => {
  const original = {
    version: 2,
    sha256: "original-graph",
    data: { links: [{ status: "inferred" }] },
  };
  const later = {
    version: 3,
    sha256: "confirmed-graph",
    data: { links: [{ status: "confirmed" }] },
  };
  const assessment = {
    payload: { report: { graph_version: 2 }, input_snapshot: original },
  };
  assert.equal(reportSnapshot(later, assessment), original);
  assert.equal(reportSnapshot({ version: 1 }, assessment), original);
  assert.equal(reportSnapshot(later, null), later);
  assert.equal(reportSnapshot(null, null), null);
  assert.throws(
    () => reportSnapshot(later, { payload: { report: { graph_version: 2 } } }),
    /original graph snapshot/,
  );
  assert.throws(
    () =>
      reportSnapshot(later, {
        payload: { report: { graph_version: 3 }, input_snapshot: original },
      }),
    /original graph snapshot/,
  );
});
