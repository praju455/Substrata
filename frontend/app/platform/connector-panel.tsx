"use client";

import { useState } from "react";
import { call } from "./client";
import { connectorTable } from "./connector-table";
import type { Provenance } from "./contracts";
import { localizeMessage, translate, useLocale, type CopyKey } from "./i18n";

type Connector = { name: string; resources: string[] };
export type ConnectorPreview = {
  filename: string;
  content_base64: string;
  provenance: Provenance;
};
type Props = {
  token: string;
  busy: boolean;
  canEdit: boolean;
  run: (operation: () => Promise<unknown>) => Promise<void>;
  prepareMapping: (preview: ConnectorPreview) => Promise<void>;
};

export default function ConnectorPanel({
  token,
  busy,
  canEdit,
  run,
  prepareMapping,
}: Props) {
  const [locale] = useLocale();
  const t = (key: CopyKey) => translate(locale, key);
  const [connectors, setConnectors] = useState<Connector[] | null>(null);
  const [name, setName] = useState("");
  const [resource, setResource] = useState("");
  const [preview, setPreview] = useState<
    | (ConnectorPreview & {
        columns: string[];
        row_count: number;
        sample: Record<string, string>[];
      })
    | null
  >(null);
  const connector = connectors?.find((item) => item.name === name);
  return (
    <details>
      <summary>{t("Read-only connector imports")}</summary>
      <p className="muted">
        {t(
          "Read a configured resource, then use the same column mapping and review as file imports. This does not write to the source system.",
        )}
      </p>
      <button
        className="secondary"
        disabled={busy}
        onClick={() =>
          void run(async () => {
            setPreview(null);
            setName("");
            setResource("");
            setConnectors(await call("/connectors", token));
          })
        }
      >
        {t("Load configured connectors")}
      </button>
      {connectors?.length === 0 && (
        <p>{t("No connectors are configured for this organisation.")}</p>
      )}
      {!!connectors?.length && (
        <div className="platform-form-row">
          <label>
            {t("Connector")}
            <select
              value={name}
              disabled={busy}
              onChange={(e) => {
                setName(e.target.value);
                setResource("");
                setPreview(null);
              }}
            >
              <option value="">{t("Choose a connector")}</option>
              {connectors.map((item) => (
                <option key={item.name} value={item.name}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("Resource")}
            <select
              value={resource}
              disabled={busy || !connector}
              onChange={(e) => {
                setResource(e.target.value);
                setPreview(null);
              }}
            >
              <option value="">{t("Choose a resource")}</option>
              {connector?.resources.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <button
            className="secondary"
            disabled={
              busy || !canEdit || !connector?.resources.includes(resource)
            }
            onClick={() =>
              void run(async () => {
                setPreview(null);
                const result = await call(
                  `/connectors/${encodeURIComponent(name)}/read/${encodeURIComponent(resource)}`,
                  token,
                  {},
                );
                const table = connectorTable(result.rows);
                setPreview({
                  ...table,
                  filename: (name + "-" + resource).slice(0, 240) + ".csv",
                  provenance: result.provenance,
                });
              })
            }
          >
            {t("Read resource preview")}
          </button>
        </div>
      )}
      {preview && (
        <>
          <p>
            {preview.row_count} {t("rows")} ·{" "}
            {localizeMessage(locale, preview.provenance.kind)} ·{" "}
            {preview.provenance.uri}
          </p>
          <p className="muted">{preview.provenance.note}</p>
          <p>{preview.columns.join(" · ")}</p>
          <p className="muted">
            {t(
              "Preview shows up to five rows and eight columns. All fields remain available for mapping.",
            )}
          </p>
          <div className="connector-sample">
            <table aria-label={t("Connector preview rows")}>
              <thead>
                <tr>
                  {preview.columns.slice(0, 8).map((column) => (
                    <th scope="col" key={column}>
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.sample.map((row, index) => (
                  <tr key={index}>
                    {preview.columns.slice(0, 8).map((column) => (
                      <td key={column}>{row[column]?.slice(0, 300) || "—"}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            className="primary"
            disabled={busy || !canEdit}
            onClick={() => void run(() => prepareMapping(preview))}
          >
            {t("Use preview for column mapping")}
          </button>
        </>
      )}
    </details>
  );
}
