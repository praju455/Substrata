"use client";

import { call } from "./client";
import type { RecordItem } from "./contracts";
import {
  localizeMessage,
  localeTag,
  translate,
  useLocale,
  type CopyKey,
} from "./i18n";

type Evaluation = {
  precision: number;
  recall: number;
  average_precision: number;
  brier_score: number;
  synthetic: boolean;
  scope: string;
  limitation: string;
  splits: Record<string, { rows: number; groups: string[] }>;
  calibration: { observed: number[]; predicted: number[] };
};
type Props = {
  models: RecordItem[];
  token: string;
  busy: boolean;
  canAdmin: boolean;
  development: boolean;
  run: (operation: () => Promise<unknown>) => Promise<void>;
};

export default function ScorerPanel({
  models,
  token,
  busy,
  canAdmin,
  development,
  run,
}: Props) {
  const [locale] = useLocale();
  const t = (key: CopyKey) => translate(locale, key);
  const number = (value: number) =>
    Number.isFinite(value)
      ? new Intl.NumberFormat(localeTag(locale), {
          maximumFractionDigits: 3,
        }).format(value)
      : "—";
  return (
    <section id="scorer" className="panel">
      <h2>{t("Link scorer models")}</h2>
      <p className="muted">
        {t(
          "Train only from supplier confirm/reject labels. At least 50 labels across 10 independent supplier groups are required, with both classes in each split. This does not train an LLM.",
        )}
      </p>
      <div className="button-row">
        <button
          className="primary"
          disabled={busy || !canAdmin}
          onClick={() => void run(() => call("/models/train", token, {}))}
        >
          {t("Train scorer candidate")}
        </button>
        <button
          className="secondary"
          disabled={busy}
          onClick={() => void run(async () => {})}
        >
          {t("Refresh scorer registry")}
        </button>
      </div>
      <p className="muted">
        {t(
          "Activation requires held-out precision of at least 0.8 and recall of at least 0.7. Synthetic-trained models are limited to development. The server enforces these checks.",
        )}
      </p>
      {!models.length && (
        <p>{t("No scorer versions are registered for this organisation.")}</p>
      )}
      {models.map((model) => {
        const report = model.payload.report as Evaluation;
        return (
          <article className="record-row" key={model.id}>
            <div>
              <strong>{String(model.payload.model_type)}</strong>
              <span className="badge">
                {localizeMessage(locale, model.status)}
              </span>
              {report.synthetic && (
                <p className="notice">
                  {t(
                    "Synthetic training data; these metrics do not establish real-world accuracy.",
                  )}
                </p>
              )}
              <p>
                {model.id} ·{" "}
                {new Date(model.created_at).toLocaleString(localeTag(locale))}
              </p>
              <p>
                {t("Held-out precision")} {number(report.precision)} ·{" "}
                {t("Held-out recall")} {number(report.recall)}
              </p>
              <p>
                {t("Average precision")} {number(report.average_precision)} ·{" "}
                {t("Brier score")} {number(report.brier_score)}
              </p>
              <p className="muted">
                {report.scope} {report.limitation}
              </p>
              <details>
                <summary>{t("Evaluation and model provenance")}</summary>
                <p>
                  {t("Feature version")} {String(model.payload.feature_version)}
                </p>
                <p>
                  {t("Training labels hash")}{" "}
                  {String(model.payload.labels_sha256)}
                </p>
                <p>
                  {t("Model artifact hash")}{" "}
                  {String(model.payload.model_sha256)}
                </p>
                {Object.entries(report.splits).map(([split, values]) => (
                  <p key={split}>
                    {localizeMessage(locale, split)} · {number(values.rows)}{" "}
                    {t("rows")} · {number(values.groups.length)}{" "}
                    {t("supplier groups")}
                  </p>
                ))}
                <table>
                  <caption>{t("Holdout calibration")}</caption>
                  <thead>
                    <tr>
                      <th scope="col">{t("Predicted frequency")}</th>
                      <th scope="col">{t("Observed frequency")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.calibration.predicted.map((value, index) => (
                      <tr key={index}>
                        <td>{number(value)}</td>
                        <td>{number(report.calibration.observed[index])}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            </div>
            {model.status !== "active" && (
              <button
                className="secondary"
                disabled={
                  busy || !canAdmin || (report.synthetic && !development)
                }
                onClick={() =>
                  void run(() =>
                    call(
                      `/models/${encodeURIComponent(model.id)}/activate`,
                      token,
                      {},
                    ),
                  )
                }
              >
                {t("Activate scorer")}
              </button>
            )}
          </article>
        );
      })}
    </section>
  );
}
