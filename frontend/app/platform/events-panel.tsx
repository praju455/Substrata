"use client";

import { useState } from "react";
import { call } from "./client";
import type { Provenance, RecordItem } from "./contracts";
import { copyKeys, translate, useLocale, type CopyKey } from "./i18n";

const categories = [
  "supply_disruption",
  "weather",
  "transport",
  "sanctions",
  "other",
] as const;
const categoryNames: Record<string, CopyKey> = {
  supply_disruption: "Supply disruption",
  weather: "Weather",
  transport: "Transport",
  sanctions: "Sanctions review",
  other: "Other events",
};
type Props = {
  token: string;
  records: RecordItem[];
  busy: boolean;
  canEdit: boolean;
  canAdmin: boolean;
  run: (operation: () => Promise<unknown>) => Promise<void>;
};

export default function EventsPanel({
  token,
  records,
  busy,
  canEdit,
  canAdmin,
  run,
}: Props) {
  const [locale] = useLocale();
  const t = (key: CopyKey) => translate(locale, key);
  const label = (value: string) =>
    categoryNames[value]
      ? t(categoryNames[value])
      : copyKeys.includes(value as CopyKey)
        ? t(value as CopyKey)
        : value;
  const [sourceId, setSourceId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [uri, setUri] = useState("");
  const [kind, setKind] = useState("assumption");
  const [note, setNote] = useState("");
  const [observed, setObserved] = useState(() =>
    new Date(Date.now() - new Date().getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16),
  );
  const [ruleName, setRuleName] = useState("");
  const [selected, setSelected] = useState<string[]>([...categories]);
  const [minimum, setMinimum] = useState(0.5);
  const [enabled, setEnabled] = useState(true);
  const [ruleOpen, setRuleOpen] = useState(false);
  const subscriptions = records.filter(
    (item) => item.kind === "event_subscription",
  );
  return (
    <section id="event-intake" className="panel">
      <h2>{t("Event intake and alert rules")}</h2>
      <p className="muted">
        {t(
          "Submit a sourced event. Classification and severity use heuristic rules; ambiguous entity matches require review.",
        )}
      </p>
      <details>
        <summary>{t("Submit an event")}</summary>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void run(async () => {
              const observed_at = new Date(observed).toISOString();
              await call("/events", token, {
                source_id: sourceId,
                title,
                description,
                observed_at,
                provenance: { uri, kind, note, observed_at },
              });
              setTitle("");
              setDescription("");
              setSourceId("");
              setUri("");
              setNote("");
            });
          }}
        >
          <div className="platform-form-row">
            <label>
              {t("Event source ID")}
              <input
                required
                maxLength={96}
                pattern="[A-Za-z0-9][A-Za-z0-9_.:-]*"
                value={sourceId}
                onChange={(e) => setSourceId(e.target.value)}
              />
            </label>
            <label>
              {t("Observed at")}
              <input
                required
                type="datetime-local"
                value={observed}
                onChange={(e) => setObserved(e.target.value)}
              />
            </label>
          </div>
          <label>
            {t("Event title")}
            <input
              required
              maxLength={256}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <label>
            {t("Event description")}
            <textarea
              maxLength={10000}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </label>
          <div className="platform-form-row">
            <label>
              {t("Source URI")}
              <input
                required
                maxLength={2048}
                value={uri}
                onChange={(e) => setUri(e.target.value)}
              />
            </label>
            <label>
              {t("Source kind")}
              <select value={kind} onChange={(e) => setKind(e.target.value)}>
                <option value="assumption">{t("assumption")}</option>
                <option value="synthetic">{t("synthetic")}</option>
                <option value="public">{t("public")}</option>
              </select>
            </label>
          </div>
          <label>
            {t("Source note")}
            <input
              required
              maxLength={2000}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </label>
          <button className="primary" disabled={busy || !canEdit}>
            {t("Submit sourced event")}
          </button>
        </form>
      </details>
      <details
        open={ruleOpen}
        onToggle={(event) => setRuleOpen(event.currentTarget.open)}
      >
        <summary>{t("Configure alert rules")}</summary>
        <p className="muted">
          {t(
            "Rules apply to newly ingested events. Saving a rule does not resend existing alerts.",
          )}
        </p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void run(async () => {
              await call("/events/subscriptions", token, {
                name: ruleName,
                categories: selected,
                minimum_severity: minimum,
                enabled,
              });
              setRuleName("");
            });
          }}
        >
          <div className="platform-form-row">
            <label>
              {t("Rule name")}
              <input
                required
                maxLength={96}
                pattern="[A-Za-z0-9][A-Za-z0-9_.:-]*"
                value={ruleName}
                onChange={(e) => setRuleName(e.target.value)}
              />
            </label>
            <label>
              {t("Minimum heuristic severity")}
              <input
                type="number"
                required
                min={0}
                max={1}
                step={0.05}
                value={minimum}
                onChange={(e) => setMinimum(Number(e.target.value))}
              />
            </label>
          </div>
          <fieldset className="event-categories">
            <legend>{t("Event categories")}</legend>
            {categories.map((category) => (
              <label key={category}>
                <input
                  type="checkbox"
                  checked={selected.includes(category)}
                  onChange={(e) =>
                    setSelected((current) =>
                      e.target.checked
                        ? [...current, category]
                        : current.filter((item) => item !== category),
                    )
                  }
                />
                {label(category)}
              </label>
            ))}
            <label>
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
              />
              {t("Enable rule")}
            </label>
          </fieldset>
          <button
            className="primary"
            disabled={busy || !canAdmin || !selected.length}
          >
            {t("Save alert rule")}
          </button>
        </form>
      </details>
      {subscriptions.map((item) => (
        <div className="record-row" key={item.id}>
          <div>
            <strong>{item.id.replace(/^subscription-/, "")}</strong>
            <p>
              {label(item.status)} · {t("Minimum heuristic severity")}{" "}
              {String(item.payload.minimum_severity)}
            </p>
            <p>
              {(item.payload.categories as string[]).map(label).join(" · ")}
            </p>
          </div>
          <button
            className="quiet"
            disabled={busy || !canAdmin}
            onClick={() => {
              setRuleName(item.id.replace(/^subscription-/, ""));
              setSelected(item.payload.categories as string[]);
              setMinimum(Number(item.payload.minimum_severity));
              setEnabled(item.status === "active");
              setRuleOpen(true);
            }}
          >
            {t("Edit alert rule")}
          </button>
        </div>
      ))}
      {!subscriptions.length && (
        <p className="muted">{t("No alert rules configured.")}</p>
      )}
      {records
        .filter((item) => item.kind === "event")
        .slice(0, 10)
        .map((item) => (
          <div className="record-row" key={item.id}>
            <div>
              <strong>{String(item.payload.title)}</strong>
              <p>
                {label(String(item.payload.category))} · {label(item.status)}
              </p>
              <p className="muted">
                {label((item.payload.provenance as Provenance).kind)} ·{" "}
                {(item.payload.provenance as Provenance).uri}
              </p>
            </div>
          </div>
        ))}
    </section>
  );
}
