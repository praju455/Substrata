"use client";

import dynamic from "next/dynamic";
import NextLink from "next/link";

import { useCallback, useEffect, useState } from "react";

import type {
  Frozen,
  Impact,
  Measure,
  Provenance,
  RecordPage,
  RecordItem,
  Report,
  Workspace,
} from "./contracts";

import type { GraphData } from "../types";
import { dependencyDepths } from "../graph-layout";
import {
  copyKeys,
  localeTag,
  localizeMessage,
  translate,
  useLocale,
  type CopyKey,
  type Locale,
} from "./i18n";

import "./workspace.css";
import { API, call } from "./client";
import EvidencePanel from "./evidence-panel";
import JobsPanel from "./jobs-panel";
import { reportSnapshot } from "./report-snapshot";
import EventsPanel from "./events-panel";
import { eventForAlert, recordTitle } from "./record-title";
import Delegation from "./delegation";
import ConnectorPanel from "./connector-panel";
import ScorerPanel from "./scorer-panel";
import IdentityReview from "./identity-review";
import PolicyPanel from "./policy-panel";
import { defaultUnits, importFields } from "./import-fields";
import AssistantPanel from "./assistant-panel";

const Network = dynamic(() => import("../network"), { ssr: false });

const recordKinds = [
  "assessment",
  "import",
  "mitigation",
  "event_subscription",
  "event",
  "alert",
  "notification",
  "confirmation",
  "agent_run",
] as const;

const format = (value: number | null | undefined, locale: Locale) =>
  value == null
    ? "—"
    : new Intl.NumberFormat(localeTag(locale), { maximumFractionDigits: 2 }).format(value);

function provenance(note: string) {
  return {
    uri: "user://workspace",
    observed_at: new Date().toISOString(),
    kind: "assumption",
    note,
  };
}

function measure(value: number, unit: string, note: string) {
  return { value, unit, provenance: provenance(note) };
}

async function beginLogin() {
  const config = await call("/auth/config", "");

  const verifier = Array.from(crypto.getRandomValues(new Uint8Array(48)), (b) =>
    b.toString(16).padStart(2, "0"),
  ).join("");

  const state = crypto.randomUUID();

  const hash = new Uint8Array(
    await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)),
  );

  const challenge = btoa(String.fromCharCode(...hash))
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");

  sessionStorage.setItem("substrata-pkce", JSON.stringify({ verifier, state }));

  const redirect = location.origin + location.pathname;

  const url = new URL(config.authorization_endpoint);

  for (const [key, value] of Object.entries({
    client_id: config.client_id,
    response_type: "code",
    scope: config.scope,
    redirect_uri: redirect,
    state,
    code_challenge: challenge,
    code_challenge_method: "S256",
  }))
    url.searchParams.set(key, String(value));

  location.assign(url.toString());
}

export default function PlatformWorkspace() {
  const [locale, setLocale] = useLocale();

  const t = (key: CopyKey) => translate(locale, key);
  const tStatus = (value: string) =>
    copyKeys.includes(value as CopyKey) ? t(value as CopyKey) : value;

  const [token, setToken] = useState("");

  const [devToken, setDevToken] = useState("");

  const [auth, setAuth] = useState<{
    enabled: boolean;
    development: boolean;
  } | null>(null);

  const [state, setState] = useState<Workspace | null>(null);

  const [message, setMessage] = useState("");

  const [busy, setBusy] = useState(false);

  const [orgName, setOrgName] = useState("");

  const [industry, setIndustry] = useState("automotive");

  const [search, setSearch] = useState("");
  const [graphDepth, setGraphDepth] = useState(8);

  const [statusFilter, setStatusFilter] = useState("");

  const [asOf, setAsOf] = useState("");

  const [historical, setHistorical] = useState<Frozen | null>(null);

  const [selectedLink, setSelectedLink] = useState("");

  const [source, setSource] = useState("");

  const [severity, setSeverity] = useState(0.9);

  const [depth, setDepth] = useState(8);

  const [assessment, setAssessment] = useState<RecordItem | null>(null);

  const [report, setReport] = useState<Report | null>(null);

  const [reason, setReason] = useState("");

  const [alertReasons, setAlertReasons] = useState<Record<string, string>>({});

  const [eventResolutions, setEventResolutions] = useState<
    Record<string, { entityId: string; reason: string }>
  >({});

  const [file, setFile] = useState<File | null>(null);

  const [target, setTarget] = useState("entities");

  const [columns, setColumns] = useState<string[]>([]);

  const [mapping, setMapping] = useState<Record<string, string>>({});

  const [units, setUnits] = useState<Record<string, string>>(() => defaultUnits("entities"));

  const [recordCursors, setRecordCursors] = useState<Record<string, string | null>>({});

  const [historyKind, setHistoryKind] = useState<string>("import");

  const [uploadBody, setUploadBody] = useState<Record<string, unknown> | null>(
    null,
  );

  const [currency, setCurrency] = useState("USD");

  const [quote, setQuote] = useState("");

  const [cost, setCost] = useState(0);

  const [duration, setDuration] = useState(7);

  useEffect(() => {
    document.documentElement.lang = localeTag(locale);
  }, [locale]);

  const refresh = useCallback(
    async (accessToken = token) => {
      const [workspace, jobPage, modelPage, ...pages]: [
        Workspace,
        RecordPage,
        RecordPage,
        ...RecordPage[],
      ] = await Promise.all([
        call("/state", accessToken),
        call("/records/page?kind=job&limit=50", accessToken),
        call("/records/page?kind=model_registry&limit=50", accessToken),
        ...recordKinds.map((kind) =>
          call(`/records/page?kind=${encodeURIComponent(kind)}&limit=50`, accessToken),
        ),
      ]);
      workspace.records = pages.flatMap((page) => page.items).sort((left, right) =>
        right.created_at.localeCompare(left.created_at) || right.id.localeCompare(left.id),
      );
      workspace.jobs = jobPage.items;
      workspace.models = modelPage.items;
      setRecordCursors({
        ...Object.fromEntries(
          recordKinds.map((kind, index) => [kind, pages[index].next_cursor]),
        ),
        job: jobPage.next_cursor,
        model_registry: modelPage.next_cursor,
      });

      setState(workspace);
      const latest = workspace.records.find((r) => r.kind === "assessment");
      setAssessment(latest || null);
      setReport(latest ? (latest.payload.report as Report) : null);
      const policy = workspace.organisation?.policy;
      if (policy?.spend_limit) {
        setCurrency(String(policy.currency));
      }
    },
    [token],
  );

  const loadOlderRecords = async (kind: string) => {
    const cursor = recordCursors[kind];
    if (!cursor) return;
    setBusy(true);
    setMessage("");
    try {
      const page: RecordPage = await call(
        `/records/page?kind=${encodeURIComponent(kind)}&limit=50&cursor=${encodeURIComponent(cursor)}`,
        token,
      );
      setState((current) => {
        if (!current) return current;
        const known = new Set(current.records.map((record) => record.id));
        return {
          ...current,
          records: [...current.records, ...page.items.filter((record) => !known.has(record.id))].sort(
            (left, right) =>
              right.created_at.localeCompare(left.created_at) || right.id.localeCompare(left.id),
          ),
        };
      });
      setRecordCursors((current) => ({ ...current, [kind]: page.next_cursor }));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t("The operation failed."));
    } finally {
      setBusy(false);
    }
  };

  const run = async (operation: () => Promise<unknown>) => {
    setBusy(true);
    setMessage("");

    try {
      await operation();
      if (token) await refresh();
      setMessage(t("Saved. Your workspace is up to date."));
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : t("The operation failed."),
      );
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    const init = async () => {
      try {
        setAuth(await call("/auth/config", ""));

        const params = new URLSearchParams(location.search);

        if (params.has("code")) {
          const pending = JSON.parse(
            sessionStorage.getItem("substrata-pkce") || "null",
          );

          sessionStorage.removeItem("substrata-pkce");

          if (!pending || pending.state !== params.get("state"))
            throw new Error(
              "Sign-in state did not match. Start sign-in again.",
            );

          const result = await call("/auth/exchange", "", {
            code: params.get("code"),
            verifier: pending.verifier,
            redirect_uri: location.origin + location.pathname,
          });

          history.replaceState(null, "", location.pathname);

          setToken(result.access_token);
        }
      } catch (error) {
        setMessage(
          error instanceof Error ? error.message : "Platform is unavailable.",
        );
      }
    };

    void init();
  }, []);

  useEffect(() => {
    if (!token) return;
    const timer = setTimeout(
      () => void refresh().catch((error) => setMessage(error.message)),
      0,
    );
    return () => clearTimeout(timer);
  }, [token, refresh]);

  const snapshot = historical || state?.snapshot;

  const can = (role: string) =>
    !!state?.identity.roles.some((r) => r === role || r === "admin");

  const graph: GraphData | null = snapshot
    ? {
        version: snapshot.version,
        as_of: snapshot.recorded_at,
        nodes: snapshot.data.entities.map((e) => ({
          id: e.id,
          name: e.name,
          node_type:
            (
              {
                Supplier: "SupplierSite",
                Site: "SupplierSite",
                Material: "Component",
              } as Record<string, string>
            )[e.kind] || e.kind,
          attributes: e.attributes,
          synthetic: e.provenance.kind === "synthetic",
        })),
        edges: snapshot.data.links
          .filter((e) => !statusFilter || e.status === statusFilter)
          .map((e) => ({
            id: e.id,
            source: e.source,
            target: e.target,
            edge_type: e.type,
            status: e.status,
            confidence: e.confidence,
            evidence: e.evidence.map((c) => ({
              id: c.document_id,
              quote: c.passage,
              stance: c.stance,
              source_uri: e.provenance.uri,
              source_kind: e.provenance.kind,
              sha256: "",
            })),
          })),
      }
    : null;

  const depths = graph ? dependencyDepths(graph) : new Map<string, number>();
  const filteredGraph = graph
    ? {
        ...graph,
        nodes: graph.nodes.filter(
          (n) =>
            (n.name + " " + n.id)
              .toLocaleLowerCase()
              .includes(search.toLocaleLowerCase()) &&
            (depths.get(n.id) ?? 0) <= graphDepth,
        ),
      }
    : null;

  const visibleEntities =
    snapshot?.data.entities.filter((e) =>
      (e.name + " " + e.id)
        .toLocaleLowerCase()
        .includes(search.toLocaleLowerCase()),
    ) || [];

  const link = snapshot?.data.links.find((e) => e.id === selectedLink);

  const fields = importFields[target] || [];

  const records = state?.records || [];

  const download = async (path: string, filename: string) => {
    const response = await fetch(API + "/platform" + path, {
      headers: { Authorization: "Bearer " + token },
    });

    if (!response.ok) throw new Error(t("Export failed."));

    const url = URL.createObjectURL(await response.blob());

    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const printRiskReport = async () => {
    const workspace = state;
    const snapshot = reportSnapshot(historical || state?.snapshot, assessment);
    if (!workspace || !snapshot)
      throw new Error(t("Load a graph snapshot before exporting a report."));
    const reportWindow = window.open("", "_blank");
    if (!reportWindow)
      throw new Error(t("Allow the report window to open, then try again."));
    reportWindow.opener = null;
    const safe = (value: unknown) =>
      String(value ?? "—").replace(/[&<>"']/g, (character) => {
        const entities: Record<string, string> = {
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        };
        return entities[character];
      });
    const payload = assessment?.payload.report;
    const report =
      payload && typeof payload === "object"
        ? (payload as Partial<Report>)
        : null;
    const impacts = Array.isArray(report?.impacts) ? report.impacts : [];
    const impactRows = impacts.length
      ? impacts
          .map(
            (impact) =>
              `<tr><td>${safe(impact.material_name)}</td><td>${safe(impact.plant_name)}</td><td>${safe(format(impact.cover_days, locale))} ${impact.cover_days === null ? "" : safe(t("days"))}</td><td>${safe(format(impact.requalification_days, locale))} ${impact.requalification_days === null ? "" : safe(t("days"))}</td><td>${safe(impact.exposure_days_range?.map((days) => format(days, locale)).join("–"))}</td><td>${safe(t(impact.status as CopyKey))}</td></tr>`,
          )
          .join("")
      : `<tr><td colspan="6">${safe(t("No saved assessment is available for this graph revision."))}</td></tr>`;
    const entitiesByKind = [
      ...new Set(snapshot.data.entities.map((entity) => entity.kind)),
    ]
      .sort()
      .map(
        (kind) =>
          `<li>${safe(t(kind as CopyKey))}: ${snapshot.data.entities.filter((entity) => entity.kind === kind).length}</li>`,
      )
      .join("");
    const dateTime = (value: string | Date) =>
      safe(new Date(value).toLocaleString(localeTag(locale)));
    const links = snapshot.data.links;
    const html = `<!doctype html><html lang="${localeTag(locale)}"><head><meta charset="utf-8"><title>${safe(t("Supply risk assessment"))}</title><style>
      @page{size:auto;margin:18mm}body{font:14px/1.45 Arial,sans-serif;color:#17212a;max-width:1000px;margin:36px auto;padding:0 24px}h1,h2{color:#163b46}h1{font-size:28px}h2{font-size:18px;margin-top:28px}p,li{color:#394b54}.meta{display:grid;grid-template-columns:1fr 1fr;gap:8px}.meta p{margin:4px 0}table{width:100%;border-collapse:collapse;margin-top:12px}th,td{text-align:left;border:1px solid #c7d1d5;padding:8px;vertical-align:top}th{background:#eaf1f2}.notice{padding:12px;border-left:4px solid #aa6b18;background:#fff7e9}.footer{margin-top:32px;font-size:11px;color:#596a72;word-break:break-word}@media print{body{margin:0;padding:0}h1,h2,table{break-after:avoid}tr{break-inside:avoid}}
      </style></head><body><h1>${safe(t("Supply risk assessment"))}</h1><p>${safe(workspace.organisation?.name)} · ${safe(workspace.identity.tenant_id)}</p><div class="meta"><p><strong>${safe(t("Report generated:"))}</strong> ${dateTime(new Date())}</p><p><strong>${safe(t("Graph revision"))}:</strong> ${format(snapshot.version, locale)}</p><p><strong>${safe(t("Revision recorded:"))}</strong> ${dateTime(snapshot.recorded_at)}</p><p><strong>${safe(t("Entities / links:"))}</strong> ${format(snapshot.data.entities.length, locale)} / ${format(snapshot.data.links.length, locale)}</p><p><strong>${safe(t("Assessment created:"))}</strong> ${assessment ? dateTime(assessment.created_at) : safe(t("No saved assessment"))}</p><p><strong>${safe(t("Assessment as of:"))}</strong> ${safe(report?.as_of)}</p><p><strong>${safe(t("Audit chain"))}:</strong> ${safe(t(workspace.audit?.valid ? "Verified" : "Not verified"))} (${format(workspace.audit?.count ?? 0, locale)} ${safe(t("records"))})</p></div><h2>${safe(t("Graph coverage"))}</h2><ul>${entitiesByKind}</ul><p>${format(links.filter((link) => link.status === "confirmed").length, locale)} ${safe(t("confirmed"))} · ${format(links.filter((link) => link.status === "inferred").length, locale)} ${safe(t("inferred"))} · ${format(links.filter((link) => link.status === "declared").length, locale)} ${safe(t("declared links"))}</p><h2>${safe(t("Affected materials and plants"))}</h2><table><thead><tr><th>${safe(t("Material"))}</th><th>${safe(t("Plant"))}</th><th>${safe(t("Cover"))}</th><th>${safe(t("Requalification"))}</th><th>${safe(t("Exposure range"))}</th><th>${safe(t("Status"))}</th></tr></thead><tbody>${impactRows}</tbody></table>${report?.range_assumption ? `<h2>${safe(t("Uncertainty and method"))}</h2><p>${safe(report.range_assumption)}</p>` : ""}<p class="notice">${safe(t("This report reflects the selected graph revision and any saved deterministic assessment shown above. Inferred relationships and exposure ranges carry uncertainty; review their source evidence and provenance before acting. The report is informational and does not authorize procurement or legal clearance."))}</p><p class="footer">${safe(t("Graph snapshot SHA-256:"))} ${safe(snapshot.sha256)}<br>${safe(t("Audit chain head:"))} ${safe(workspace.audit?.head)}</p></body></html>`;
    reportWindow.document.open();
    reportWindow.document.write(html);
    reportWindow.document.close();
    reportWindow.setTimeout(() => reportWindow.print(), 250);
  };

  return (
    <>
      <a className="skip-link" href="#platform-main">
        {t("Skip to workspace")}
      </a>
      <header className="site-header">
        <div className="shell header-inner">
          <NextLink className="brand" href="/">
            Substrata
          </NextLink>
          <nav aria-label={t("Platform sections")}>
            <a href="#onboarding">{t("Onboarding")}</a>
            <a href="#imports">{t("Imports")}</a>
            <a href="#graph">{t("Network")}</a>
            <a href="#evidence">{t("Evidence")}</a>
            <a href="#assistant">Assistant</a>
            <a href="#jobs">{t("Background tasks")}</a>
            <a href="#event-intake">{t("Events")}</a>
            <a href="#approvals">{t("Approvals")}</a>
          </nav>
          <label className="locale-picker">
            <span className="visually-hidden">{t("Language")}</span>
            <select
              aria-label={t("Language")}
              value={locale}
              onChange={(event) => setLocale(event.target.value as Locale)}
            >
              <option value="en">English</option>
              <option value="hi">हिन्दी</option>
            </select>
          </label>
          <span>{state ? state.identity.tenant_id : t("Tenant workspace")}</span>
        </div>
      </header>
      <main
        id="platform-main"
        className="shell main-content platform-workspace"
      >
        <div className="hero">
          <div>
          <p className="eyebrow purple">{t("SUPPLY NETWORK INTELLIGENCE")}</p>
            <h1>{t("Your supply network")}</h1>
            <p className="muted">
              {t("Trace your dependencies, measure production runway, and review the next action.")}
            </p>
          </div>
          {token && (
            <div className="button-row">
              <button
                className="quiet"
                disabled={busy}
                onClick={() => void run(() => refresh())}
              >
                {t("Refresh workspace")}
              </button>
              <button
                className="secondary"
                onClick={() => {
                  setToken("");
                  setState(null);
                  setDevToken("");
                  setHistorical(null);
                  setMessage("");
                }}
              >
                {t("Sign out")}
              </button>
            </div>
          )}
        </div>

        {message && (
          <p className="notice" role="status">
            {localizeMessage(locale, message)}
          </p>
        )}

        {!token ? (
          <section className="panel">
            <h2>{t("Sign in with your organisation")}</h2>
            <p className="muted">
              {t("Your organisation determines the network and approvals you can access.")}
            </p>
            {auth?.enabled && (
              <button className="primary" onClick={() => void run(beginLogin)}>
                {t("Continue with SSO")}
              </button>
            )}
            {auth?.development && (
              <details>
                <summary>{t("Local development access")}</summary>
                <label>
                  {t("Development access token")}
                  <textarea
                    value={devToken}
                    onChange={(e) => setDevToken(e.target.value)}
                    autoComplete="off"
                    spellCheck={false}
                  />
                </label>
                <button
                  className="secondary"
                  onClick={() => {
                    setToken(devToken.trim());
                    setDevToken("");
                  }}
                >
                  {t("Open local workspace")}
                </button>
              </details>
            )}
            {!auth && <p>{t("Start the platform API to connect this workspace.")}</p>}
          </section>
        ) : !state ? (
          <section className="panel" aria-busy="true">
            {t("Loading your organisation…")}
          </section>
        ) : (
          <>
            <section id="onboarding" className="panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow teal">{t("GET STARTED")}</p>
                  <h2>
                    {state.organisation?.name || t("Set up your organisation")}
                  </h2>
                </div>
                    <span>{state.identity.roles.map(tStatus).join(" · ")}</span>
              </div>
              {!state.organisation ? (
                <>
                  <label>
                    {t("Organisation name")}
                    <input
                      value={orgName}
                      onChange={(e) => setOrgName(e.target.value)}
                    />
                  </label>
                  <button
                    disabled={busy || !can("admin") || !orgName.trim()}
                    className="primary"
                    onClick={() =>
                      void run(() =>
                        call("/organisation", token, { name: orgName }),
                      )
                    }
                  >
                    {t("Create organisation")}
                  </button>
                </>
              ) : (
                <>
                  <ol className="onboarding-steps">
                    <li>{t("Organisation created")}</li>
                    <li>
                      {snapshot
                        ? t("Network data loaded")
                        : t("Import your network data")}
                    </li>
                    <li>
                      {Object.keys(state.organisation.policy).length
                        ? t("Approval policy configured")
                        : t("Set an approval policy")}
                    </li>
                    <li>{t("Assess a disruption and review an action")}</li>
                  </ol>
                  {auth?.development && (
                    <details>
                      <summary>{t("Explore synthetic industry examples")}</summary>
                      <p>
                        {t("Invented records for demonstration. These are not customer or supplier facts.")}
                      </p>
                      <label>
                        {t("Industry")}
                        <select
                          value={industry}
                          onChange={(e) => setIndustry(e.target.value)}
                        >
                          <option value="automotive">
                            {t("Automotive electronics")}
                          </option>
                          <option value="pharma">{t("Pharma")}</option>
                          <option value="food">{t("Food")}</option>
                        </select>
                      </label>
                      <button
                        disabled={busy || !can("admin")}
                        className="secondary"
                        onClick={() =>
                          void run(() =>
                            call("/seeds", token, {
                              industry,
                              expected_version: state.organisation!.version,
                            }),
                          )
                        }
                      >
                        {t("Load synthetic example")}
                      </button>
                    </details>
                  )}
                </>
              )}
            </section>

            {state.organisation && (
              <>
                <section className="quality-grid" aria-label={t("Data quality")}>
                  <div>
                    <span>{t("Graph revision")}</span>
                    <strong>{snapshot?.version || 0}</strong>
                  </div>
                  <div>
                    <span>{t("Missing inventory rows")}</span>
                    <strong>
                      {state.quality.inventory?.missing_row_count || 0}
                    </strong>
                    <small className="muted">
                      {state.quality.inventory?.missing_value_row_count || 0} {t("rows have missing values")}
                    </small>
                  </div>
                  <div>
                    <span>{t("Complete inventory rows")}</span>
                    <strong>
                      {state.quality.inventory?.complete_rows || 0}
                    </strong>
                  </div>
                  <div>
                    <span>{t("Inferred links")}</span>
                    <strong>
                      {snapshot?.data.links.filter(
                        (e) => e.status === "inferred",
                      ).length || 0}
                    </strong>
                  </div>
                  <div>
                    <span>{t("Audit chain")}</span>
                    <strong>
                      {state.audit?.valid ? t("Verified") : t("Check required")}
                    </strong>
                  </div>
                </section>

                <EvidencePanel key={state.identity.tenant_id} token={token} workspace={state}
                  canEdit={can("analyst")} busy={busy} run={run}
                  development={auth?.development === true} />
                <AssistantPanel
                  token={token}
                  entities={state.snapshot?.data.entities || []}
                  selectedRelationshipId={selectedLink}
                  onSelectRelationship={setSelectedLink}
                />
                <JobsPanel jobs={state.jobs || []} token={token} busy={busy}
                  canEdit={can("analyst")} run={run} snapshot={snapshot || null} />
                <section id="imports" className="panel">
                  <h2>{t("Data imports")}</h2>
                  <ConnectorPanel token={token} busy={busy} canEdit={can("analyst")} run={run}
                    prepareMapping={async (preview) => {
                      const body = { filename: preview.filename, content_base64: preview.content_base64,
                        provenance: preview.provenance, target, mapping: {}, expected_version: state.organisation!.version };
                      const staged = await call("/imports/stage", token, body);
                      setFile(null); setMapping({}); setUnits(defaultUnits(target)); setColumns(staged.columns);
                      setUploadBody({ ...body, schema_sha256: staged.schema_sha256 });
                    }} />
                  <p className="muted">
                    {t("Preview CSV or Excel columns, validate the mapping, then apply a reviewed import.")}
                  </p>
                  <div className="platform-form-row">
                    <label>
                      {t("Table")}
                      <select
                        value={target}
                        onChange={(e) => {
                          setTarget(e.target.value);
                          setMapping({});
                          setUnits(defaultUnits(e.target.value));
                        }}
                      >
                        <option value="entities">{t("Entities")}</option>
                        <option value="inventory">{t("Inventory")}</option>
                        <option value="links">{t("Links")}</option>
                        <option value="purchase_orders">{t("Purchase orders")}</option>
                        <option value="boms">{t("BOM items")}</option>
                      </select>
                    </label>
                    <label>
                      {t("File")}
                      <input
                        type="file"
                        accept=".csv,.xlsx"
                        onChange={(e) => {
                          setFile(e.target.files?.[0] || null);
                          setColumns([]);
                        }}
                      />
                    </label>
                    <button
                      disabled={busy || !file || !can("analyst")}
                      className="secondary"
                      onClick={() =>
                        void run(async () => {
                          if (!file) return;
                          const bytes = new Uint8Array(
                            await file.arrayBuffer(),
                          );
                          if (bytes.length > 3000000)
                            throw new Error(t("Choose a file smaller than 3 MB."));
                          let encoded = "";
                          for (let i = 0; i < bytes.length; i += 8192)
                            encoded += String.fromCharCode(
                              ...bytes.subarray(i, i + 8192),
                            );
                          const body = {
                            filename: file.name,
                            content_base64: btoa(encoded),
                            target,
                            mapping: {},
                            expected_version: state.organisation!.version,
                            provenance: {
                              ...provenance("Uploaded " + file.name),
                              kind: "uploaded",
                              uri: "upload://" + file.name,
                            },
                          };
                          const preview = await call(
                            "/imports/stage",
                            token,
                            body,
                          );
                          setColumns(preview.columns);
                          setUploadBody({
                            ...body,
                            schema_sha256: preview.schema_sha256,
                          });
                        })
                      }
                    >
                    {t("Preview columns")}
                    </button>
                  </div>
                  {columns.length > 0 && (
                    <>
                      <div className="mapping-grid">
                        {fields.map((field) => (
                          <div className="mapping-field" key={field.path}>
                          <label>
                            {field.label}
                            <span className="muted small">{field.path}</span>
                            <select
                              value={mapping[field.path] || ""}
                              onChange={(e) =>
                                setMapping({
                                  ...mapping,
                                  [field.path]: e.target.value,
                                })
                              }
                            >
                              <option value="">{t("Not mapped")}</option>
                              {columns.map((c) => (
                                <option key={c}>{c}</option>
                              ))}
                            </select>
                          </label>
                          {field.defaultUnit && (
                            <label>
                              {t("Unit")}
                              <input
                                required={Boolean(mapping[field.path])}
                                value={units[field.path] || ""}
                                onChange={(event) =>
                                  setUnits({ ...units, [field.path]: event.target.value })
                                }
                              />
                            </label>
                          )}
                          </div>
                        ))}
                      </div>
                      <button
                        disabled={busy || !can("analyst")}
                        className="primary"
                        onClick={() =>
                          void run(() =>
                            call("/imports/stage", token, {
                              ...uploadBody,
                              target,
                              expected_version: state.organisation!.version,
                              mapping: Object.fromEntries(
                                Object.entries(mapping).filter(([, v]) => v),
                              ),
                              units: Object.fromEntries(
                                Object.entries(units).filter(
                                  ([field, unit]) => mapping[field] && unit.trim(),
                                ),
                              ),
                            }),
                          )
                        }
                      >
                    {t("Validate and stage")}
                      </button>
                    </>
                  )}
                  {records
                    .filter((r) => r.kind === "import")
                    .map((r) => (
                      <article className="record-row" key={r.id}>
                        <div>
                          <strong>
                            {String(
                              r.payload.filename ||
                                r.payload.connector ||
                                "Import",
                            )}
                          </strong>
                          <span className="badge">{tStatus(r.status)}</span>
                          <p className="muted small">
                            {format(Number(r.payload.row_count || 0), locale)} {t("rows")} ·{" "}
                            {String(r.payload.schema_sha256 || "").slice(0, 12)}
                          </p>
                          {r.status === "invalid" && (
                            <pre>
                              {JSON.stringify(r.payload.errors, null, 2)}
                            </pre>
                          )}
                        </div>
                        {r.status === "staged" && (
                          <button
                            disabled={busy || !can("analyst")}
                            className="primary"
                            onClick={() =>
                              void run(() =>
                                call(`/imports/${r.id}/apply`, token, {}),
                              )
                            }
                          >
                            {t("Apply import")}
                          </button>
                        )}
                        {r.status === "applied" && (
                          <button
                            disabled={busy || !can("admin") || !reason.trim()}
                            className="secondary"
                            onClick={() =>
                              void run(() =>
                                call(`/imports/${r.id}/rollback`, token, {
                                  reason,
                                }),
                              )
                            }
                          >
                            {t("Rollback with reason")}
                          </button>
                        )}
                        {r.status === "needs_review" && (
                          <IdentityReview key={r.id} record={r} token={token} busy={busy}
                            canEdit={can("analyst")} run={run} />
                        )}
                      </article>
                    ))}
                </section>

                {snapshot && (
                  <section id="graph" className="panel">
                    <div className="panel-heading">
                      <h2>{t("Graph explorer")}</h2>
                      <span>
                        {t("Revision")} {snapshot.version} ·{" "}
                        {new Date(snapshot.recorded_at).toLocaleString(localeTag(locale))}
                      </span>
                    </div>
                    <div className="platform-form-row">
                      <label>
                        {t("Search")}
                        <input
                          value={search}
                          onChange={(e) => setSearch(e.target.value)}
                          placeholder={t("Name or identifier")}
                        />
                      </label>
                      <label>
                        {t("Relationship status")}
                        <select
                          value={statusFilter}
                          onChange={(e) => setStatusFilter(e.target.value)}
                        >
                          <option value="">{t("All statuses")}</option>
                          {[
                            "declared",
                            "inferred",
                            "confirmed",
                            "rejected",
                            "expired",
                          ].map((s) => (
                            <option key={s}>{t(s as CopyKey)}</option>
                          ))}
                        </select>
                      </label>
                      <label>
                        {t("Dependency depth")}
                        <input
                          type="number"
                          min="0"
                          max="32"
                          value={graphDepth}
                          onChange={(e) =>
                            setGraphDepth(Number(e.target.value))
                          }
                        />
                      </label>
                      <label>
                        {t("As-of date")}
                        <input
                          type="datetime-local"
                          value={asOf}
                          onChange={(e) => setAsOf(e.target.value)}
                        />
                      </label>
                      <button
                        className="secondary"
                        disabled={busy || !asOf}
                        onClick={() =>
                          void run(async () =>
                            setHistorical(
                              await call(
                                "/graph?as_of=" +
                                  encodeURIComponent(
                                    new Date(asOf).toISOString(),
                                  ),
                                token,
                              ),
                            ),
                          )
                        }
                      >
                        {t("View history")}
                      </button>
                      <button
                        className="quiet"
                        onClick={() => setHistorical(null)}
                      >
                        {t("Latest revision")}
                      </button>
                    </div>
                    {filteredGraph && (
                      <Network
                        graph={filteredGraph}
                        sharedIds={
                          report?.shared_dependencies.map((d) => d.id) || []
                        }
                        onSelect={(kind, id) => {
                          if (kind === "edge") setSelectedLink(id);
                        }}
                        labels={{
                          scope: t("Supplier sites → materials → products and plants"),
                          allEntities: t("All entities"),
                          fitGraph: t("Fit graph"),
                          ariaLabel: t(
                            "Interactive supplier network. Use the relationship list below for keyboard access.",
                          ),
                        }}
                      />
                    )}
                    <div className="entity-list">
                      {visibleEntities.map((e) => (
                        <span key={e.id} className="badge">
                          {e.name} · {tStatus(e.kind)} · {tStatus(e.provenance.kind)}
                        </span>
                      ))}
                    </div>
                    <label>
                      {t("Inspect a link")}
                      <select
                        value={selectedLink}
                        onChange={(e) => setSelectedLink(e.target.value)}
                      >
                        <option value="">{t("Choose a relationship")}</option>
                        {snapshot.data.links.map((e) => (
                          <option value={e.id} key={e.id}>
                            {e.source} → {e.target} · {tStatus(e.status)}
                          </option>
                        ))}
                      </select>
                    </label>
                    {link && (
                      <div className="evidence-body">
                        <strong>
                          {link.type} · {tStatus(link.status)}
                        </strong>
                        <p>
                          {t("Evidence support")} {format(link.confidence * 100, locale)}% ·
                          {link.confidence_provenance?.calibrated
                            ? t("calibrated scorer")
                            : t("rule-supported, uncalibrated")}
                        </p>
                        {link.confidence_provenance && (
                          <div className="muted small">
                            <p>
                              {t("Scorer version")}: {link.confidence_provenance.scorer_version} · {t("Feature version")}: {link.confidence_provenance.feature_version}
                            </p>
                            {link.confidence_provenance.evaluation_scope && (
                              <p>{link.confidence_provenance.evaluation_scope}</p>
                            )}
                            {link.confidence_provenance.synthetic_evaluation && (
                              <p>{t("Synthetic evaluation; not a real-world accuracy claim.")}</p>
                            )}
                          </div>
                        )}
                        <p className="muted">
                          {link.provenance.kind} · {link.provenance.uri}
                        </p>
                        {link.evidence.map((c, i) => (
                          <blockquote key={i}>
                            <p>{c.passage}</p>
                            <small>
                              {c.document_id} · {c.stance}
                            </small>
                          </blockquote>
                        ))}
                      </div>
                    )}
                  </section>
                )}

                {snapshot && (
                  <section className="panel">
                    <h2>Deterministic Impact Engine</h2>
                    <p className="muted">
                      {t("Assess a full source interruption using the selected immutable graph revision.")}
                    </p>
                    <div className="platform-form-row">
                      <label>
                        {t("Affected source")}
                        <select
                          value={source}
                          onChange={(e) => setSource(e.target.value)}
                        >
                          <option value="">{t("Choose an entity")}</option>
                          {snapshot.data.entities.map((e) => (
                            <option value={e.id} key={e.id}>
                              {e.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        {t("Severity")}
                        <input
                          type="number"
                          min="0"
                          max="1"
                          step=".1"
                          value={severity}
                          onChange={(e) => setSeverity(Number(e.target.value))}
                        />
                      </label>
                      <label>
                        {t("Traversal depth")}
                        <input
                          type="number"
                          min="1"
                          max="32"
                          value={depth}
                          onChange={(e) => setDepth(Number(e.target.value))}
                        />
                      </label>
                      <button
                        className="primary"
                        disabled={busy || !source || !can("analyst")}
                        onClick={() =>
                          void run(async () => {
                            const result = await call(
                              "/scenarios/assess",
                              token,
                              {
                                source_id: source,
                                severity,
                                as_of: new Date().toISOString(),
                                version: snapshot.version,
                                max_depth: depth,
                              },
                            );
                            setAssessment(result);
                            setReport(result.payload.report);
                          })
                        }
                      >
                      {t("Calculate runway")}
                      </button>
                    </div>
                    {report && (
                      <>
                        <p className="muted">
                          {t("Graph revision")} {report.graph_version} · formula {report.formula_version}
                          {" · "}source {report.source_id} · severity {report.severity}
                        </p>
                        <p className="notice">
                          Stock cover = usable stock ÷ daily consumption. Exposure runway =
                          requalification time − remaining stock cover. Missing values or unit
                          mismatches produce an incomplete result, never a guessed number.
                        </p>
                        <p className="notice">{report.range_assumption}</p>
                        {report.truncated && (
                          <p role="alert">
                            {t("Traversal was truncated. Mitigations are blocked until assessment is complete.")}
                          </p>
                        )}
                        {report.impacts.map((impact: Impact, i) => (
                          <article className="runway-card" key={i}>
                            <strong>
                              {impact.material_name} · {impact.plant_name}
                            </strong>
                            <span className="badge">{tStatus(impact.status)}</span>
                            {impact.reason && <p>{impact.reason}</p>}
                            <div className="runway-metrics">
                              <div>
                                <span>{t("Stock cover")}</span>
                                <strong>
                                  {format(impact.cover_days, locale)} {t("days")}
                                </strong>
                              </div>
                              <div>
                                <span>{t("Requalification")}</span>
                                <strong>
                                  {format(impact.requalification_days, locale)} {t("days")}
                                </strong>
                              </div>
                              <div>
                                <span>{t("Exposure range")}</span>
                                <strong>
                                  {impact.exposure_days_range
                                    ?.map((days) => format(days, locale))
                                    .join("–") || "—"}{" "}
                                  {t("days")}
                                </strong>
                              </div>
                            </div>
                          </article>
                        ))}
                      </>
                    )}
                  </section>
                )}

                <PolicyPanel key={JSON.stringify(state.organisation.policy)} policy={state.organisation.policy}
                  token={token} busy={busy} canAdmin={can("admin")} run={run} />

                <section id="approvals" className="panel">
                  <h2>Mitigation options, policy and approval</h2>
                  <label>
                    {t("Decision or rollback reason")}
                    <textarea
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder={t("Explain the evidence and decision")}
                    />
                  </label>
                  {assessment && (
                    <details>
                      <summary>{t("Draft a mitigation from a sourced quote")}</summary>
                      <div className="platform-form-row">
                        <label>
                          {t("Quote source and rationale")}
                          <input
                            value={quote}
                            onChange={(e) => setQuote(e.target.value)}
                          />
                        </label>
                        <label>
                          {t("Cost")}
                          <input
                            type="number"
                            min="0"
                            value={cost}
                            onChange={(e) => setCost(Number(e.target.value))}
                          />
                        </label>
                        <label>
                          {t("Duration in days")}
                          <input
                            type="number"
                            min="0"
                            value={duration}
                            onChange={(e) =>
                              setDuration(Number(e.target.value))
                            }
                          />
                        </label>
                        <button
                          className="primary"
                          disabled={busy || !quote.trim() || !can("analyst")}
                          onClick={() =>
                            void run(() =>
                              call("/mitigations", token, {
                                assessment_id: assessment.id,
                                kind: "buffer_buy",
                                title: "Buffer supply quote",
                                cost: measure(cost, currency, quote),
                                duration: measure(duration, "day", quote),
                                rationale: quote,
                              }),
                            )
                          }
                        >
                          {t("Create approval draft")}
                        </button>
                      </div>
                    </details>
                  )}
                  {records
                    .filter((r) => r.kind === "mitigation")
                    .map((r) => (
                      <article className="record-row" key={r.id}>
                        <div>
                          <strong>{String(r.payload.title)}</strong>
                          <span className="badge">{tStatus(r.status)}</span>
                          <p>{String(r.payload.rationale)}</p>
                          {typeof r.payload.assigned_to === "string" && <p>{t("Assigned reviewer")} {r.payload.assigned_to}</p>}
                          {r.status === "pending" && <Delegation token={token} actionId={r.id}
                            busy={busy} canDelegate={can("approver") &&
                              (typeof r.payload.assigned_to !== "string" ||
                               r.payload.assigned_to === state.identity.subject || can("admin"))} run={run} />}
                          <p className="muted small">
                            {format((r.payload.cost as Measure).value, locale)}{" "}
                            {(r.payload.cost as Measure).unit} ·{" "}
                            {(r.payload.cost as Measure).provenance.note}
                          </p>
                          {r.status === "blocked" && (
                            <p>
                              {(r.payload.blocked_reasons as string[]).join(
                                " ",
                              )}
                            </p>
                          )}
                        </div>
                        <div className="button-row">
                          {r.status === "pending" && (
                            <>
                              <button
                                disabled={
                                  busy || !reason.trim() || !can("approver") ||
                                  (typeof r.payload.assigned_to === "string" && r.payload.assigned_to !== state.identity.subject)
                                }
                                className="primary"
                                onClick={() =>
                                  void run(() =>
                                    call(`/approvals/${r.id}/decision`, token, {
                                      decision: "approved",
                                      reason,
                                    }),
                                  )
                                }
                              >
                                {t("Approve")}
                              </button>
                              <button
                                disabled={
                                  busy || !reason.trim() || !can("approver") ||
                                  (typeof r.payload.assigned_to === "string" && r.payload.assigned_to !== state.identity.subject)
                                }
                                className="secondary"
                                onClick={() =>
                                  void run(() =>
                                    call(`/approvals/${r.id}/decision`, token, {
                                      decision: "rejected",
                                      reason,
                                    }),
                                  )
                                }
                              >
                                {t("Reject")}
                              </button>
                            </>
                          )}
                          {r.status === "approved" && (
                            <button
                              disabled={busy || !can("approver")}
                              className="secondary"
                              onClick={() =>
                                void run(() =>
                                  call(`/actions/${r.id}/execute`, token, {}),
                                )
                              }
                            >
                              Generate approved dry-run action
                            </button>
                          )}
                        </div>
                      </article>
                    ))}
                  {!records.some((r) => r.kind === "mitigation") && (
                    <p className="muted">
                      {t("Assess a disruption, then draft a sourced mitigation to begin review.")}
                    </p>
                  )}
                </section>

                <ScorerPanel token={token} models={state.models || []} busy={busy}
                  canAdmin={can("admin")} development={auth?.development === true} run={run} />
                <EventsPanel token={token} records={records} busy={busy}
                  canEdit={can("analyst")} canAdmin={can("admin")} run={run} />
                <section className="panel">
                  <h2>{t("Alert centre")}</h2>
                  {records
                    .filter((r) => ["alert", "notification"].includes(r.kind))
                    .map((r) => (
                      <article className="record-row" key={r.id}>
                        <div>
                          <strong>
                            {tStatus(recordTitle(r, records))}
                          </strong>
                          <p className="muted">{tStatus(r.status)}</p>
                          {r.payload.type === "approval_delegated" && <p>{t("Assigned reviewer")} {String(r.payload.subject)}</p>}
                          {eventForAlert(r, records) && <p className="muted">
                            {tStatus((eventForAlert(r, records)!.payload.provenance as Provenance).kind)} · {(eventForAlert(r, records)!.payload.provenance as Provenance).uri}
                          </p>}
                          {r.kind === "alert" && r.status === "open" && (
                            <div className="button-row">
                              <label>
                                {t("Acknowledgement reason")}
                                <input
                                  value={alertReasons[r.id] || ""}
                                  onChange={(event) =>
                                    setAlertReasons((current) => ({
                                      ...current,
                                      [r.id]: event.target.value,
                                    }))
                                  }
                                />
                              </label>
                              <button
                                className="secondary"
                                disabled={
                                  busy ||
                                  !alertReasons[r.id]?.trim() ||
                                  !can("analyst")
                                }
                                onClick={() =>
                                  void run(() =>
                                    call(
                                      `/alerts/${encodeURIComponent(r.id)}/acknowledge`,
                                      token,
                                      { reason: alertReasons[r.id].trim() },
                                    ),
                                  )
                                }
                              >
                                {t("Acknowledge alert")}
                              </button>
                            </div>
                          )}
                        </div>
                      </article>
                    ))}
                  {records
                    .filter(
                      (r) => r.kind === "event" && r.status === "needs_review",
                    )
                    .map((r) => {
                      const resolution = eventResolutions[r.id] || {
                        entityId: "",
                        reason: "",
                      };
                      return (
                        <article className="record-row" key={r.id}>
                          <div>
                            <strong>
                              {String(
                                r.payload.title ||
                                  r.payload.headline ||
                                  t("Unmatched event"),
                              )}
                            </strong>
                            <p className="muted">
                              {r.payload.category === "sanctions"
                                ? t("Possible name-only sanctions or export-control candidate. Mapping the entity does not determine sanctions status, export authorization, or clearance.")
                                : t("Event needs entity review")}
                            </p>
                            {typeof r.payload.provenance === "object" &&
                              r.payload.provenance !== null &&
                              "uri" in r.payload.provenance &&
                              typeof r.payload.provenance.uri === "string" &&
                              r.payload.provenance.uri.startsWith(
                                "https://data.trade.gov/",
                              ) && (
                                <p className="muted">
                                  {t("This product uses the International Trade Administration’s Data API but is not endorsed or certified by the International Trade Administration.")}
                                </p>
                              )}
                            <div className="button-row">
                              <label>
                                {t("Match to entity")}
                                <select
                                  value={resolution.entityId}
                                  onChange={(event) =>
                                    setEventResolutions((current) => ({
                                      ...current,
                                      [r.id]: {
                                        ...resolution,
                                        entityId: event.target.value,
                                      },
                                    }))
                                  }
                                >
                                  <option value="">{t("Select an entity")}</option>
                                  {(state.snapshot?.data.entities || []).map(
                                    (entity) => (
                                      <option key={entity.id} value={entity.id}>
                                        {entity.name} ({entity.kind})
                                      </option>
                                    ),
                                  )}
                                </select>
                              </label>
                              <label>
                                {t("Resolution reason")}
                                <input
                                  value={resolution.reason}
                                  onChange={(event) =>
                                    setEventResolutions((current) => ({
                                      ...current,
                                      [r.id]: {
                                        ...resolution,
                                        reason: event.target.value,
                                      },
                                    }))
                                  }
                                />
                              </label>
                              <button
                                className="secondary"
                                disabled={
                                  busy ||
                                  !resolution.entityId ||
                                  !resolution.reason.trim() ||
                                  !can("analyst")
                                }
                                onClick={() =>
                                  void run(() =>
                                    call(
                                      `/events/${encodeURIComponent(r.id)}/resolve`,
                                      token,
                                      {
                                        entity_id: resolution.entityId,
                                        reason: resolution.reason.trim(),
                                      },
                                    ),
                                  )
                                }
                              >
                                {r.payload.category === "sanctions"
                                  ? t("Map entity for review")
                                  : t("Map event to entity")}
                              </button>
                            </div>
                          </div>
                        </article>
                      );
                    })}
                  {!records.some(
                    (r) =>
                      ["alert", "notification"].includes(r.kind) ||
                      (r.kind === "event" && r.status === "needs_review"),
                  ) && (
                    <p className="muted">
                      {t("No alerts or approval notifications yet.")}
                    </p>
                  )}
                </section>

                <section className="panel">
                  <h2>{t("Reports and audit")}</h2>
                  <p>
                    {state.audit?.valid
                      ? t("Audit chain verified")
                      : t("Audit verification requires attention")}{" "}
                    · {state.audit?.count || 0} {t("records")}
                  </p>
                  <div className="history-browser">
                    <h3>{t("Workflow history")}</h3>
                    <label>
                      {t("Record type")}
                      <select
                        value={historyKind}
                        onChange={(event) => setHistoryKind(event.target.value)}
                      >
                        {recordKinds.map((kind) => (
                          <option key={kind} value={kind}>{tStatus(kind)}</option>
                        ))}
                      </select>
                    </label>
                    <div aria-live="polite">
                      {records.filter((record) => record.kind === historyKind).map((record) => (
                        <p className="history-row" key={record.id}>
                          <span className="mono">{record.id}</span>
                          <span>{tStatus(record.status)}</span>
                          <time dateTime={record.created_at}>
                            {new Date(record.created_at).toLocaleString(localeTag(locale))}
                          </time>
                        </p>
                      ))}
                    </div>
                    {recordCursors[historyKind] && (
                      <button
                        className="secondary"
                        disabled={busy}
                        onClick={() => void loadOlderRecords(historyKind)}
                      >
                        {t("Load older records")}
                      </button>
                    )}
                  </div>
                  <div className="button-row">
                    <button
                      className="secondary"
                      onClick={() => void run(() => printRiskReport())}
                    >
                      {t("Print or save PDF")}
                    </button>
                    <button
                      className="secondary"
                      onClick={() =>
                        void run(() =>
                          download("/audit", "substrata-audit.json"),
                        )
                      }
                    >
                      {t("Export audit JSON")}
                    </button>
                    <button
                      className="secondary"
                      onClick={() =>
                        void run(() =>
                          download("/exports/graph.csv", "substrata-graph.csv"),
                        )
                      }
                    >
                      {t("Export CSV")}
                    </button>
                  </div>
                  <p className="mono break">{t("Chain head:")} {state.audit?.head}</p>
                </section>
              </>
            )}
          </>
        )}
      </main>
    </>
  );
}
