"use client";

import { useState } from "react";
import { call } from "./client";
import type { Graph, RecordItem } from "./contracts";
import { localeTag, translate, useLocale, type CopyKey } from "./i18n";

type Review = {
  incoming_id: string;
  candidates: {
    id: string;
    name: string;
    score: number;
    name_rule_score: number;
    embedding_score: number;
  }[];
};

export default function IdentityReview({ record, token, busy, canEdit, run }: {
  record: RecordItem;
  token: string;
  busy: boolean;
  canEdit: boolean;
  run: (operation: () => Promise<unknown>) => Promise<void>;
}) {
  const [locale] = useLocale();
  const t = (key: CopyKey) => translate(locale, key);
  const [decisions, setDecisions] = useState<Record<string, string>>({});
  const [reason, setReason] = useState("");
  const reviews = record.payload.reviews as Review[];
  const entities = (record.payload.candidate as Graph).entities;
  const score = (value: number) => new Intl.NumberFormat(localeTag(locale), {
    maximumFractionDigits: 3,
  }).format(value);
  return (
    <details>
      <summary>{t("Resolve ambiguous identities")}</summary>
      <p className="muted">{t("Review every incoming identity. Similarity scores are suggestions, not verified matches. Matching preserves the existing identifier and imports the incoming entity details.")}</p>
      {reviews.map((review) => (
        <fieldset key={review.incoming_id} disabled={busy || !canEdit}>
          <legend>{entities.find((entity) => entity.id === review.incoming_id)?.name} · {review.incoming_id}</legend>
          <ul>
            {review.candidates.map((candidate) => (
              <li key={candidate.id}>
                <strong>{candidate.name}</strong> · {candidate.id}
                <p className="muted">{t("Name-rule similarity")} {score(candidate.name_rule_score)} · {t("Embedding similarity")} {score(candidate.embedding_score)}</p>
              </li>
            ))}
          </ul>
          <label>
            {t("Identity decision")} · {review.incoming_id}
            <select value={decisions[review.incoming_id] || ""}
              onChange={(event) => setDecisions({ ...decisions, [review.incoming_id]: event.target.value })}>
              <option value="">{t("Choose an identity decision")}</option>
              <option value="null">{t("Keep as a separate entity")}</option>
              {review.candidates.map((candidate) => (
                <option key={candidate.id} value={JSON.stringify(candidate.id)}>{candidate.name} · {candidate.id}</option>
              ))}
            </select>
          </label>
        </fieldset>
      ))}
      <label>
        {t("Identity review reason")}
        <textarea value={reason} disabled={busy || !canEdit} maxLength={2000}
          onChange={(event) => setReason(event.target.value)} />
      </label>
      <button className="secondary" disabled={busy || !canEdit || !reason.trim() ||
        !reviews.length || reviews.some((review) => !decisions[review.incoming_id])}
        onClick={() => void run(() => call(`/imports/${encodeURIComponent(record.id)}/resolve`, token, {
          reason: reason.trim(),
          decisions: Object.fromEntries(reviews.map((review) => [review.incoming_id, JSON.parse(decisions[review.incoming_id])])),
        }))}>
        {t("Save identity review")}
      </button>
    </details>
  );
}
