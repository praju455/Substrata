"use client";

import { useState } from "react";
import { call } from "./client";
import { localizeMessage, translate, useLocale, type CopyKey } from "./i18n";
import { editedPolicy, policyDraft, type PolicyDraft } from "./policy-edit";

export default function PolicyPanel({
  policy,
  token,
  busy,
  canAdmin,
  run,
}: {
  policy: Record<string, unknown>;
  token: string;
  busy: boolean;
  canAdmin: boolean;
  run: (operation: () => Promise<unknown>) => Promise<void>;
}) {
  const [locale] = useLocale();
  const t = (key: CopyKey) => translate(locale, key);
  const [draft, setDraft] = useState(() => policyDraft(policy));
  const [reason, setReason] = useState("");
  const update = (field: keyof PolicyDraft, value: string) =>
    setDraft((previous) => ({ ...previous, [field]: value }));
  return (
    <section className="panel" id="policy">
      <h2>{t("Approval policy")}</h2>
      <p className="muted">
        {t(
          "Limits are explicit organisation assumptions. A separate approver is required by default.",
        )}
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (busy || !canAdmin) return;
          void run(() =>
            call(
              "/policy",
              token,
              editedPolicy(policy, draft, {
                uri: "user://workspace/policy",
                observed_at: new Date().toISOString(),
                kind: "assumption",
                note: reason.trim(),
              }),
            ),
          );
        }}
      >
        <fieldset disabled={busy || !canAdmin}>
          <legend className="visually-hidden">{t("Approval policy")}</legend>
          <div className="platform-form-row">
            <label>
              {t("Currency")}
              <input
                required
                pattern="[A-Z]{3}"
                maxLength={3}
                value={draft.currency}
                onChange={(event) =>
                  update("currency", event.target.value.toUpperCase())
                }
              />
            </label>
            <label>
              {t("Maximum spend")}
              <input
                required
                type="number"
                min="0"
                step="any"
                value={draft.spend}
                onChange={(event) => update("spend", event.target.value)}
              />
            </label>
            <label>
              {t("Automatic approval limit")}
              <input
                required
                type="number"
                min="0"
                max={draft.spend || undefined}
                step="any"
                value={draft.automatic}
                onChange={(event) => update("automatic", event.target.value)}
              />
            </label>
            <label>
              {t("Approval SLA in hours")}
              <input
                required
                type="number"
                min="0"
                max="168"
                step="any"
                value={draft.sla}
                onChange={(event) => update("sla", event.target.value)}
              />
            </label>
            <label>
              {t("Daily inference budget in USD")}
              <input
                type="number"
                min="0"
                step="any"
                value={draft.dailyBudget}
                aria-describedby="policy-budget-help"
                onChange={(event) => update("dailyBudget", event.target.value)}
              />
            </label>
          </div>
          <p className="muted" id="policy-budget-help">
            {t(
              "Leave the inference budget blank to disable live inference. Zero permits no paid usage. Provider credentials and sourced prices must also be configured.",
            )}
          </p>
          <label>
            {t("Policy change reason")}
            <textarea
              required
              maxLength={2000}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </label>
          <button type="submit" className="secondary" disabled={!reason.trim()}>
            {t("Save policy")}
          </button>
        </fieldset>
      </form>
      <details>
        <summary>{t("Retained approval controls")}</summary>
        <p>
          {t(
            "Spending edits retain the configured approver roles, separation of duties and allowed action kinds.",
          )}
        </p>
        <p>
          {t("Approver roles")}:{" "}
          {(
            (policy.approver_roles as string[] | undefined) ?? [
              "approver",
              "admin",
            ]
          )
            .map((role) => localizeMessage(locale, role))
            .join(" · ")}
        </p>
        <p>
          {t("Separate approver required")}:{" "}
          {t(policy.require_separate_approver === false ? "No" : "Yes")}
        </p>
        {Array.isArray(policy.allowed_kinds) && (
          <p>
            {t("Allowed action kinds")}: {policy.allowed_kinds.join(" · ")}
          </p>
        )}
      </details>
    </section>
  );
}
