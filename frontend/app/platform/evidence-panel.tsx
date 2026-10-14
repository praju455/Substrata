"use client";

import { useState } from "react";
import { call } from "./client";
import type { Workspace } from "./contracts";
import { copyKeys, translate, useLocale, type CopyKey } from "./i18n";

type Passage = {
  document_id: string;
  text: string;
  start: number;
  end: number;
  score: number;
};
type Props = {
  token: string;
  workspace: Workspace;
  busy: boolean;
  canEdit: boolean;
  development: boolean;
  run: (operation: () => Promise<unknown>) => Promise<void>;
};

export default function EvidencePanel({
  token,
  workspace,
  busy,
  canEdit,
  development,
  run,
}: Props) {
  const [locale] = useLocale();
  const t = (key: Parameters<typeof translate>[1]) => translate(locale, key);
  const label = (value: string) =>
    copyKeys.includes(value as CopyKey) ? t(value as CopyKey) : value;
  const [id, setId] = useState("");
  const [text, setText] = useState("");
  const [uri, setUri] = useState("");
  const [note, setNote] = useState("");
  const [kind, setKind] = useState("uploaded");
  const [query, setQuery] = useState("");
  const [passages, setPassages] = useState<Passage[] | null>(null);
  const [link, setLink] = useState("");
  const [recipient, setRecipient] = useState("");
  const [preview, setPreview] = useState("");
  const [previewRequestId, setPreviewRequestId] = useState("");
  const previewRequest = workspace.records.find((item) => item.id === previewRequestId);
  const candidates =
    workspace.snapshot?.data.links.filter(
      (item) => item.status === "declared" || item.status === "inferred",
    ) || [];
  return (
    <section id="evidence" className="panel">
      <h2>{t("Evidence and supplier review")}</h2>
      <p className="muted">
        {t(
          "Store sourced passages, retrieve evidence, and propose relationships for review.",
        )}
      </p>
      <details>
        <summary>{t("Add an evidence document")}</summary>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void run(async () => {
              await call("/documents", token, {
                id,
                text,
                provenance: {
                  uri,
                  kind,
                  note,
                  observed_at: new Date().toISOString(),
                },
              });
              setId("");
              setText("");
              setUri("");
              setNote("");
              setPassages(null);
            });
          }}
        >
          <div className="platform-form-row">
            <label>
              {t("Document ID")}
              <input
                required
                maxLength={96}
                pattern="[A-Za-z0-9][A-Za-z0-9_.:-]*"
                value={id}
                onChange={(e) => setId(e.target.value)}
              />
            </label>
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
                <option value="uploaded">{t("uploaded")}</option>
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
          <label>
            {t("Document text")}
            <textarea
              required
              maxLength={2000000}
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </label>
          <button className="primary" disabled={busy || !canEdit}>
            {t("Save document")}
          </button>
        </form>
      </details>
      <p>
        {workspace.documents.length} {t("stored documents")}
      </p>
      {workspace.documents.map((document) => (
        <p key={document.id} className="muted">
          {document.id} · {label(document.provenance.kind)} ·{" "}
          {document.provenance.uri}
        </p>
      ))}
      <button
        className="secondary"
        disabled={busy || !canEdit || !workspace.documents.length}
        onClick={() =>
          void run(async () => {
            await call("/evidence/index", token, {});
            setPassages(null);
          })
        }
      >
        {t("Index documents")}
      </button>
      <label>
        {t("Evidence query")}
        <input
          maxLength={2000}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPassages(null);
          }}
        />
      </label>
      <div className="button-row">
        <button
          className="secondary"
          disabled={busy || !query.trim() || !workspace.documents.length}
          onClick={() =>
            void run(async () =>
              setPassages(await call("/evidence/search", token, { query })),
            )
          }
        >
          {t("Search passages")}
        </button>
        <button
          className="primary"
          disabled={
            busy ||
            !canEdit ||
            !query.trim() ||
            !workspace.snapshot ||
            !workspace.documents.length
          }
          onClick={() =>
            void run(() => call("/evidence/discover", token, { query }))
          }
        >
          {t("Discover cited links")}
        </button>
      </div>
      <p className="muted">
        {t(
          "Similarity scores measure retrieval relevance, not relationship confidence. Discovered links remain inferred until supplier review.",
        )}
      </p>
      {passages?.length === 0 && (
        <p role="status">
          {t("No indexed passages found. Index documents before searching.")}
        </p>
      )}
      {passages?.map((passage) => (
        <blockquote key={passage.document_id + ":" + passage.start}>
          <p>{passage.text}</p>
          <small>
            {passage.document_id} · {passage.start}–{passage.end} ·{" "}
            {t("Relevance")} {passage.score.toFixed(3)}
          </small>
        </blockquote>
      ))}
      <h3>{t("Request supplier confirmation")}</h3>
      <label>
        {t("Relationship to review")}
        <select
          value={link}
          onChange={(e) => {
            setLink(e.target.value);
            setPreview("");
          }}
        >
          <option value="">{t("Choose a relationship")}</option>
          {candidates.map((item) => (
            <option key={item.id} value={item.id}>
              {item.source} → {item.target} · {label(item.status)}
            </option>
          ))}
        </select>
      </label>
      {development ? (
        <p className="muted">
          {t("Local preview only. No supplier email is sent.")}
        </p>
      ) : (
        <label>
          {t("Supplier email")}
          <input
            type="email"
            maxLength={256}
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
          />
        </label>
      )}
      <button
        className="primary"
        disabled={
          busy || !canEdit || !candidates.some((item) => item.id === link)
        }
        onClick={() =>
          void run(async () => {
            setPreview("");
            const result = await call("/confirmations", token, {
              link_id: link,
              expiry_hours: 72,
              recipient_email: development ? null : recipient || null,
            });
            if (development && typeof result.portal_url === "string") {
              const url = new URL(result.portal_url);
              if (url.protocol === "http:" || url.protocol === "https:")
                setPreview(url.toString());
            setPreviewRequestId(result.request.id);
            }
          })
        }
      >
        {t("Create confirmation request")}
      </button>
      {preview && previewRequest?.status === "pending" && (
        <p>
          <a
            href={preview}
            target="_blank"
            rel="noopener noreferrer"
            referrerPolicy="no-referrer"
          >
            {t("Open local supplier preview")}
          </a>
        </p>
      )}
      {workspace.records
        .filter((item) => item.kind === "confirmation")
        .map((item) => (
          <p key={item.id}>
            {String(item.payload.link_id)} · {label(item.status)} ·{" "}
            {String(item.payload.expires_at)}
          </p>
        ))}
    </section>
  );
}
