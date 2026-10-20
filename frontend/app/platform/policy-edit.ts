import type { Measure, Provenance } from "./contracts";

export type PolicyDraft = {
  currency: string;
  spend: string;
  automatic: string;
  sla: string;
  dailyBudget: string;
  jobHourlyLimit: string;
  jobTimeoutSeconds: string;
};

export function policyDraft(policy: Record<string, unknown>): PolicyDraft {
  const value = (field: string, fallback: number) =>
    String((policy[field] as Measure | undefined)?.value ?? fallback);
  return {
    currency: String(policy.currency ?? "USD"),
    spend: value("spend_limit", 50000),
    automatic: value("auto_approve_limit", 0),
    sla: value("approval_sla", 24),
    dailyBudget: policy.llm_daily_budget ? value("llm_daily_budget", 0) : "",
    jobHourlyLimit: String(policy.job_hourly_limit ?? 100),
    jobTimeoutSeconds: String(policy.job_timeout_seconds ?? 120),
  };
}

export function editedPolicy(
  policy: Record<string, unknown>,
  draft: PolicyDraft,
  provenance: Provenance,
): Record<string, unknown> {
  const numeric = (text: string) => {
    const value = Number(text);
    if (!text.trim() || !Number.isFinite(value) || value < 0)
      throw new Error("Policy values must be finite and nonnegative.");
    return value;
  };
  const spend = numeric(draft.spend);
  const automatic = numeric(draft.automatic);
  const sla = numeric(draft.sla);
  const jobHourlyLimit = numeric(draft.jobHourlyLimit);
  const jobTimeoutSeconds = numeric(draft.jobTimeoutSeconds);
  if (!/^[A-Z]{3}$/.test(draft.currency))
    throw new Error("Policy currency must contain three uppercase letters.");
  if (automatic > spend)
    throw new Error(
      "Automatic approval limit cannot exceed the spending limit.",
    );
  if (sla <= 0 || sla > 168)
    throw new Error("Approval SLA must be between zero and 168 hours.");
  if (!Number.isInteger(jobHourlyLimit) || jobHourlyLimit < 1 || jobHourlyLimit > 10000)
    throw new Error("Hourly job limit must be a whole number from 1 to 10000.");
  if (!Number.isInteger(jobTimeoutSeconds) || jobTimeoutSeconds < 5 || jobTimeoutSeconds > 3600)
    throw new Error("Job deadline must be a whole number from 5 to 3600 seconds.");
  if (!provenance.note.trim())
    throw new Error("A policy change reason is required.");
  const measure = (field: string, value: number, unit: string): Measure => {
    const original = policy[field] as Measure | undefined;
    // Unchanged sourced values retain their original provenance and observation time.
    return original?.value === value && original.unit === unit
      ? original
      : { value, unit, provenance };
  };
  return {
    ...policy,
    currency: draft.currency,
    spend_limit: measure("spend_limit", spend, draft.currency),
    auto_approve_limit: measure(
      "auto_approve_limit",
      automatic,
      draft.currency,
    ),
    approval_sla: measure("approval_sla", sla, "hour"),
    llm_daily_budget: draft.dailyBudget.trim()
      ? measure("llm_daily_budget", numeric(draft.dailyBudget), "USD")
      : null,
    job_hourly_limit: jobHourlyLimit,
    job_timeout_seconds: jobTimeoutSeconds,
  };
}
