import assert from "node:assert/strict";
import test from "node:test";
import { eventForAlert, recordTitle } from "../app/platform/record-title.ts";

test("reference-only alerts resolve their sourced event instead of showing undefined", () => {
  const alert = {
    kind: "alert",
    payload: { event_id: "event-1", severity: { value: 0.8 } },
  };
  const event = {
    id: "event-1",
    kind: "event",
    payload: {
      title: "Synthetic site closure",
      provenance: { kind: "synthetic" },
    },
  };
  const unrelated = {
    id: "event-1",
    kind: "notification",
    payload: { title: "Wrong title" },
  };
  assert.equal(
    recordTitle(alert, [unrelated, event]),
    "Synthetic site closure",
  );
  assert.equal(eventForAlert(alert, [event]), event);
  assert.equal(recordTitle(alert, []), "Event alert");
  assert.equal(
    recordTitle(
      { kind: "notification", payload: { title: "Approval required" } },
      [],
    ),
    "Approval required",
  );
  assert.equal(
    recordTitle(
      { kind: "notification", payload: { type: "supplier_confirmation" } },
      [],
    ),
    "supplier_confirmation",
  );
});
