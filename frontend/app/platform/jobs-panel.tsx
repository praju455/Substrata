"use client";

import { useState } from "react";
import { call } from "./client";
import type { Frozen, RecordItem } from "./contracts";
import { copyKeys, translate, useLocale, type CopyKey } from "./i18n";

type Props = {
  jobs: RecordItem[];
  token: string;
  busy: boolean;
  canEdit: boolean;
  snapshot: Frozen | null;
  run: (operation: () => Promise<unknown>) => Promise<void>;
};

function pinnedVersion(job: RecordItem) {
  const input = job.payload.input as
    | { graph_version?: number; arguments?: { graph_version?: number } }
    | undefined;
  return input?.graph_version ?? input?.arguments?.graph_version;
}

export default function JobsPanel({
  jobs,
  token,
  busy,
  canEdit,
  snapshot,
  run,
}: Props) {
  const [locale] = useLocale();
  const t = (key: CopyKey) => translate(locale, key);
  const label = (value: string) =>
    copyKeys.includes(value as CopyKey) ? t(value as CopyKey) : value;
  const [source, setSource] = useState("");
  const [severity, setSeverity] = useState(0.8);
  const [resumeReason, setResumeReason] = useState("");
  return (
    <section id="jobs" className="panel">
      <h2>{t("Background tasks")}</h2>
      <p className="muted">
        {t(
          "Tasks run when a worker is active or when you run the next task here. Refresh to see progress.",
        )}
      </p>
      <div className="platform-form-row">
        <label>
          {t("Affected source")}
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">{t("Choose an entity")}</option>
            {snapshot?.data.entities.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("Severity")}
          <input
            type="number"
            min={0}
            max={1}
            step={0.1}
            value={severity}
            onChange={(e) => setSeverity(Number(e.target.value))}
          />
        </label>
        <button
          className="primary"
          disabled={
            busy ||
            !canEdit ||
            !snapshot ||
            !source ||
            !Number.isFinite(severity) ||
            severity < 0 ||
            severity > 1
          }
          onClick={() =>
            void run(() =>
              call("/a2a", token, {
                jsonrpc: "2.0",
                id: crypto.randomUUID(),
                method: "tasks/send",
                params: {
                  id: crypto.randomUUID(),
                  skillId: "risk-review",
                  message: {
                    role: "user",
                    parts: [
                      {
                        type: "data",
                        data: {
                          source_id: source,
                          severity,
                          as_of: new Date().toISOString(),
                          max_depth: 8,
                          graph_version: snapshot?.version,
                        },
                      },
                    ],
                  },
                },
              }),
            )
          }
        >
          {t("Queue risk review")}
        </button>
      </div>
      <div className="button-row">
        <button
          className="secondary"
          disabled={busy || !canEdit}
          onClick={() =>
            void run(() =>
              call("/jobs", token, {
                kind: "event_poll",
                idempotency_key: crypto.randomUUID(),
                payload: {},
              }),
            )
          }
        >
          {t("Queue event feed check")}
        </button>
        <button
          className="secondary"
          disabled={busy || !canEdit}
          onClick={() => void run(() => call("/jobs/dispatch", token, {}))}
        >
          {t("Run next queued task")}
        </button>
      </div>
      {!jobs.length && <p>{t("No background tasks yet.")}</p>}
      {jobs.map((job) => (
        <div className="record-row" key={job.id}>
          <div>
            <strong>{label(String(job.payload.job_type))}</strong>
            {pinnedVersion(job) != null && (
              <p>
                {t("Graph revision")} {pinnedVersion(job)}
              </p>
            )}
            <p>
              {t("Attempt")} {String(job.payload.attempts)} ·{" "}
              {new Date(job.created_at).toLocaleString(locale)}
            </p>
            <small>{job.id}</small>
            {job.payload.error != null && <p>{String(job.payload.error)}</p>}
            {job.status === "pending" && (
              <p>
                {t("Next eligible attempt")} {String(job.payload.retry_at)}
              </p>
            )}
            {job.payload.checkpoints != null && (
              <details>
                <summary>{t("Completed review steps")}</summary>
                {Object.keys(
                  job.payload.checkpoints as Record<string, unknown>,
                ).map((step) => (
                  <p key={step}>{label(step)}</p>
                ))}
              </details>
            )}
            {job.status === "paused" && (
              <div>
                <p className="notice">
                  Human checkpoint: {String((job.payload.result as Record<string, unknown>)?.awaiting)}
                </p>
                <label>
                  Resume reason
                  <input
                    maxLength={2000}
                    value={resumeReason}
                    onChange={(event) => setResumeReason(event.target.value)}
                  />
                </label>
                <button
                  className="primary"
                  disabled={busy || !canEdit || !resumeReason.trim()}
                  onClick={() => void run(async () => {
                    const result = job.payload.result as Record<string, unknown>;
                    await call(`/jobs/${job.id}/resume`, token, {
                      checkpoint: result.awaiting,
                      reason: resumeReason.trim(),
                    });
                    setResumeReason("");
                  })}
                >
                  Resume reviewed workflow
                </button>
              </div>
            )}
          </div>
          <span className="badge">{label(job.status)}</span>
        </div>
      ))}
    </section>
  );
}
