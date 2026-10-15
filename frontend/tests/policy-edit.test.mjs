import assert from "node:assert/strict";
import test from "node:test";
import { editedPolicy, policyDraft } from "../app/platform/policy-edit.ts";

const source = {
  uri: "synthetic://approved-policy",
  kind: "synthetic",
  observed_at: "2026-10-15T00:00:00Z",
  note: "Invented policy for regression checks",
};
const changed = {
  uri: "user://workspace/policy",
  kind: "assumption",
  observed_at: "2026-10-15T01:00:00Z",
  note: "Reviewed revised spending limit",
};
const measure = (value, unit) => ({ value, unit, provenance: source });
const policy = {
  currency: "EUR",
  spend_limit: measure(5000, "EUR"),
  auto_approve_limit: measure(5, "EUR"),
  approval_sla: measure(72, "hour"),
  llm_daily_budget: measure(2.5, "USD"),
  approver_roles: ["approver"],
  require_separate_approver: true,
  allowed_kinds: ["buffer_buy"],
};

test("spending edits retain custom policy controls and unchanged provenance", () => {
  const original = structuredClone(policy);
  const updated = editedPolicy(
    policy,
    { ...policyDraft(policy), spend: "6000" },
    changed,
  );
  assert.equal(updated.spend_limit.value, 6000);
  assert.deepEqual(updated.spend_limit.provenance, changed);
  for (const key of [
    "auto_approve_limit",
    "approval_sla",
    "llm_daily_budget",
    "approver_roles",
    "require_separate_approver",
    "allowed_kinds",
  ])
    assert.deepEqual(updated[key], policy[key]);
  assert.deepEqual(policy, original);
  assert.deepEqual(editedPolicy(policy, policyDraft(policy), changed), policy);
});

test("SLA and budget edits distinguish zero, missing and currency changes", () => {
  const draft = {
    ...policyDraft(policy),
    currency: "GBP",
    sla: "12.5",
    dailyBudget: "0",
  };
  const updated = editedPolicy(policy, draft, changed);
  assert.equal(updated.spend_limit.unit, "GBP");
  assert.equal(updated.auto_approve_limit.unit, "GBP");
  assert.equal(updated.approval_sla.value, 12.5);
  assert.equal(updated.approval_sla.unit, "hour");
  assert.equal(updated.llm_daily_budget.value, 0);
  assert.equal(updated.llm_daily_budget.unit, "USD");
  assert.equal(policyDraft(updated).dailyBudget, "0");
  assert.equal(
    editedPolicy(policy, { ...draft, dailyBudget: "" }, changed)
      .llm_daily_budget,
    null,
  );
  assert.equal(policyDraft({}).dailyBudget, "");
});

test("incomplete or invalid policy values cannot be submitted as zero", () => {
  for (const patch of [
    { spend: "" },
    { spend: "Infinity" },
    { automatic: "-1" },
    { automatic: "5001" },
    { sla: "0" },
    { sla: "169" },
    { dailyBudget: "NaN" },
    { currency: "US" },
  ])
    assert.throws(() =>
      editedPolicy(policy, { ...policyDraft(policy), ...patch }, changed),
    );
  assert.throws(
    () => editedPolicy(policy, policyDraft(policy), { ...changed, note: " " }),
    /reason/,
  );
});
