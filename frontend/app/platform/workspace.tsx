"use client";

import dynamic from "next/dynamic";
import NextLink from "next/link";

import { useCallback, useEffect, useState } from "react";

import type {
  Frozen,
  Impact,
  Measure,
  RecordItem,
  Report,
  Workspace,
} from "./contracts";

import type { GraphData } from "../types";
import { dependencyDepths } from "../graph-layout";

import "./workspace.css";

const Network = dynamic(() => import("../network"), { ssr: false });

const API = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

const labels = {
  title: "Your supply network",
  signIn: "Sign in with your organisation",
  imports: "Data imports",
  network: "Graph explorer",
  approvals: "Approvals inbox",
  alerts: "Alert centre",
};

const format = (value: number | null | undefined) =>
  value == null
    ? "—"
    : new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(
        value,
      );

async function call(path: string, token: string, body?: unknown) {
  const response = await fetch(API + "/platform" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: "Bearer " + token } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });

  const data = await response.json();

  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Check the entered values and permissions.",
    );

  return data;
}

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

  const [importUnit, setImportUnit] = useState("piece");

  const [columns, setColumns] = useState<string[]>([]);

  const [mapping, setMapping] = useState<Record<string, string>>({});

  const [uploadBody, setUploadBody] = useState<Record<string, unknown> | null>(
    null,
  );

  const [spend, setSpend] = useState(50000);

  const [automatic, setAutomatic] = useState(0);

  const [currency, setCurrency] = useState("USD");

  const [quote, setQuote] = useState("");

  const [cost, setCost] = useState(0);

  const [duration, setDuration] = useState(7);

  const refresh = useCallback(
    async (accessToken = token) => {
      const workspace: Workspace = await call("/state", accessToken);

      setState(workspace);
      const latest = workspace.records.find((r) => r.kind === "assessment");
      setAssessment(latest || null);
      setReport(latest ? (latest.payload.report as Report) : null);
      const policy = workspace.organisation?.policy;
      if (policy?.spend_limit) {
        setSpend((policy.spend_limit as Measure).value);
        setAutomatic((policy.auto_approve_limit as Measure).value);
        setCurrency(String(policy.currency));
      }
    },
    [token],
  );

  const run = async (operation: () => Promise<unknown>) => {
    setBusy(true);
    setMessage("");

    try {
      await operation();
      if (token) await refresh();
      setMessage("Saved. Your workspace is up to date.");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "The operation failed.",
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

  const fields =
    target === "entities"
      ? [
          "id",
          "kind",
          "name",
          "attributes.unit",
          "measures.requalification_days",
        ]
      : target === "inventory"
        ? ["material_id", "plant_id", "as_of", "on_hand", "daily_consumption"]
        : target === "links"
          ? [
              "id",
              "source",
              "target",
              "type",
              "status",
              "confidence",
              "valid_from",
            ]
          : target === "purchase_orders"
            ? [
                "id",
                "supplier_id",
                "material_id",
                "plant_id",
                "quantity",
                "expected_at",
                "status",
              ]
            : ["material_id", "product_id", "quantity"];

  const records = state?.records || [];

  const download = async (path: string, filename: string) => {
    const response = await fetch(API + "/platform" + path, {
      headers: { Authorization: "Bearer " + token },
    });

    if (!response.ok) throw new Error("Export failed.");

    const url = URL.createObjectURL(await response.blob());

    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <a className="skip-link" href="#platform-main">
        Skip to workspace
      </a>
      <header className="site-header">
        <div className="shell header-inner">
          <NextLink className="brand" href="/">
            Substrata
          </NextLink>
          <nav aria-label="Platform sections">
            <a href="#onboarding">Onboarding</a>
            <a href="#imports">Imports</a>
            <a href="#graph">Network</a>
            <a href="#approvals">Approvals</a>
          </nav>
          <span>{state ? state.identity.tenant_id : "Tenant workspace"}</span>
        </div>
      </header>
      <main
        id="platform-main"
        className="shell main-content platform-workspace"
      >
        <div className="hero">
          <div>
            <p className="eyebrow purple">SUPPLY NETWORK INTELLIGENCE</p>
            <h1>{labels.title}</h1>
            <p className="muted">
              Trace your dependencies, measure production runway, and review the
              next action.
            </p>
          </div>
          {token && (
            <div className="button-row">
              <button
                className="quiet"
                disabled={busy}
                onClick={() => void run(() => refresh())}
              >
                Refresh workspace
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
                Sign out
              </button>
            </div>
          )}
        </div>

        {message && (
          <p className="notice" role="status">
            {message}
          </p>
        )}

        {!token ? (
          <section className="panel">
            <h2>{labels.signIn}</h2>
            <p className="muted">
              Your organisation determines the network and approvals you can
              access.
            </p>
            {auth?.enabled && (
              <button className="primary" onClick={() => void run(beginLogin)}>
                Continue with SSO
              </button>
            )}
            {auth?.development && (
              <details>
                <summary>Local development access</summary>
                <label>
                  Development access token
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
                  Open local workspace
                </button>
              </details>
            )}
            {!auth && <p>Start the platform API to connect this workspace.</p>}
          </section>
        ) : !state ? (
          <section className="panel" aria-busy="true">
            Loading your organisation…
          </section>
        ) : (
          <>
            <section id="onboarding" className="panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow teal">GET STARTED</p>
                  <h2>
                    {state.organisation?.name || "Set up your organisation"}
                  </h2>
                </div>
                <span>{state.identity.roles.join(" · ")}</span>
              </div>
              {!state.organisation ? (
                <>
                  <label>
                    Organisation name
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
                    Create organisation
                  </button>
                </>
              ) : (
                <>
                  <ol className="onboarding-steps">
                    <li>Organisation created</li>
                    <li>
                      {snapshot
                        ? "Network data loaded"
                        : "Import your network data"}
                    </li>
                    <li>
                      {Object.keys(state.organisation.policy).length
                        ? "Approval policy configured"
                        : "Set an approval policy"}
                    </li>
                    <li>Assess a disruption and review an action</li>
                  </ol>
                  {auth?.development && (
                    <details>
                      <summary>Explore synthetic industry examples</summary>
                      <p>
                        Invented records for demonstration. These are not
                        customer or supplier facts.
                      </p>
                      <label>
                        Industry
                        <select
                          value={industry}
                          onChange={(e) => setIndustry(e.target.value)}
                        >
                          <option value="automotive">
                            Automotive electronics
                          </option>
                          <option value="pharma">Pharma</option>
                          <option value="food">Food</option>
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
                        Load synthetic example
                      </button>
                    </details>
                  )}
                </>
              )}
            </section>

            {state.organisation && (
              <>
                <section className="quality-grid" aria-label="Data quality">
                  <div>
                    <span>Graph revision</span>
                    <strong>{snapshot?.version || 0}</strong>
                  </div>
                  <div>
                    <span>Missing inventory inputs</span>
                    <strong>
                      {snapshot?.data.inventory.filter(
                        (i) => !i.on_hand || !i.daily_consumption,
                      ).length || 0}
                    </strong>
                  </div>
                  <div>
                    <span>Inferred links</span>
                    <strong>
                      {snapshot?.data.links.filter(
                        (e) => e.status === "inferred",
                      ).length || 0}
                    </strong>
                  </div>
                  <div>
                    <span>Audit chain</span>
                    <strong>
                      {state.audit?.valid ? "Verified" : "Check required"}
                    </strong>
                  </div>
                </section>

                <section id="imports" className="panel">
                  <h2>{labels.imports}</h2>
                  <p className="muted">
                    Preview CSV or Excel columns, validate the mapping, then
                    apply a reviewed import.
                  </p>
                  <div className="platform-form-row">
                    <label>
                      Table
                      <select
                        value={target}
                        onChange={(e) => {
                          setTarget(e.target.value);
                          setMapping({});
                        }}
                      >
                        <option value="entities">Entities</option>
                        <option value="inventory">Inventory</option>
                        <option value="links">Links</option>
                        <option value="purchase_orders">Purchase orders</option>
                        <option value="boms">BOM items</option>
                      </select>
                    </label>
                    <label>
                      Quantity unit
                      <input
                        value={importUnit}
                        onChange={(e) => setImportUnit(e.target.value)}
                      />
                    </label>
                    <label>
                      File
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
                            throw new Error("Choose a file smaller than 3 MB.");
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
                      Preview columns
                    </button>
                  </div>
                  {columns.length > 0 && (
                    <>
                      <div className="mapping-grid">
                        {fields.map((field) => (
                          <label key={field}>
                            {field}
                            <select
                              value={mapping[field] || ""}
                              onChange={(e) =>
                                setMapping({
                                  ...mapping,
                                  [field]: e.target.value,
                                })
                              }
                            >
                              <option value="">Not mapped</option>
                              {columns.map((c) => (
                                <option key={c}>{c}</option>
                              ))}
                            </select>
                          </label>
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
                              units:
                                target === "entities"
                                  ? { "measures.requalification_days": "day" }
                                  : target === "inventory"
                                    ? {
                                        on_hand: importUnit,
                                        daily_consumption: `${importUnit}/day`,
                                      }
                                    : { quantity: importUnit },
                            }),
                          )
                        }
                      >
                        Validate and stage
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
                          <span className="badge">{r.status}</span>
                          <p className="muted small">
                            {Number(r.payload.row_count || 0)} rows ·{" "}
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
                            Apply import
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
                            Rollback with reason
                          </button>
                        )}
                        {r.status === "needs_review" && (
                          <details>
                            <summary>Resolve ambiguous identities</summary>
                            <pre>
                              {JSON.stringify(r.payload.reviews, null, 2)}
                            </pre>
                            <button
                              disabled={busy || !reason.trim()}
                              onClick={() =>
                                void run(() =>
                                  call(`/imports/${r.id}/resolve`, token, {
                                    reason,
                                    decisions: Object.fromEntries(
                                      (
                                        r.payload.reviews as {
                                          incoming_id: string;
                                        }[]
                                      ).map((review) => [
                                        review.incoming_id,
                                        null,
                                      ]),
                                    ),
                                  }),
                                )
                              }
                            >
                              Keep each incoming entity separate
                            </button>
                          </details>
                        )}
                      </article>
                    ))}
                </section>

                {snapshot && (
                  <section id="graph" className="panel">
                    <div className="panel-heading">
                      <h2>{labels.network}</h2>
                      <span>
                        Revision {snapshot.version} ·{" "}
                        {new Date(snapshot.recorded_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="platform-form-row">
                      <label>
                        Search
                        <input
                          value={search}
                          onChange={(e) => setSearch(e.target.value)}
                          placeholder="Name or identifier"
                        />
                      </label>
                      <label>
                        Relationship status
                        <select
                          value={statusFilter}
                          onChange={(e) => setStatusFilter(e.target.value)}
                        >
                          <option value="">All statuses</option>
                          {[
                            "declared",
                            "inferred",
                            "confirmed",
                            "rejected",
                            "expired",
                          ].map((s) => (
                            <option key={s}>{s}</option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Dependency depth
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
                        As-of date
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
                        View history
                      </button>
                      <button
                        className="quiet"
                        onClick={() => setHistorical(null)}
                      >
                        Latest revision
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
                      />
                    )}
                    <div className="entity-list">
                      {visibleEntities.map((e) => (
                        <span key={e.id} className="badge">
                          {e.name} · {e.kind} · {e.provenance.kind}
                        </span>
                      ))}
                    </div>
                    <label>
                      Inspect a link
                      <select
                        value={selectedLink}
                        onChange={(e) => setSelectedLink(e.target.value)}
                      >
                        <option value="">Choose a relationship</option>
                        {snapshot.data.links.map((e) => (
                          <option value={e.id} key={e.id}>
                            {e.source} → {e.target} · {e.status}
                          </option>
                        ))}
                      </select>
                    </label>
                    {link && (
                      <div className="evidence-body">
                        <strong>
                          {link.type} · {link.status}
                        </strong>
                        <p>
                          Evidence support {format(link.confidence * 100)}% ·
                          uncalibrated
                        </p>
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
                    <h2>Scenario runner</h2>
                    <p className="muted">
                      Assess a full source interruption using the selected
                      immutable graph revision.
                    </p>
                    <div className="platform-form-row">
                      <label>
                        Affected source
                        <select
                          value={source}
                          onChange={(e) => setSource(e.target.value)}
                        >
                          <option value="">Choose an entity</option>
                          {snapshot.data.entities.map((e) => (
                            <option value={e.id} key={e.id}>
                              {e.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Severity
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
                        Traversal depth
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
                        Calculate runway
                      </button>
                    </div>
                    {report && (
                      <>
                        <p className="notice">{report.range_assumption}</p>
                        {report.truncated && (
                          <p role="alert">
                            Traversal was truncated. Mitigations are blocked
                            until assessment is complete.
                          </p>
                        )}
                        {report.impacts.map((impact: Impact, i) => (
                          <article className="runway-card" key={i}>
                            <strong>
                              {impact.material_name} · {impact.plant_name}
                            </strong>
                            <span className="badge">{impact.status}</span>
                            {impact.reason && <p>{impact.reason}</p>}
                            <div className="runway-metrics">
                              <div>
                                <span>Stock cover</span>
                                <strong>
                                  {format(impact.cover_days)} days
                                </strong>
                              </div>
                              <div>
                                <span>Requalification</span>
                                <strong>
                                  {format(impact.requalification_days)} days
                                </strong>
                              </div>
                              <div>
                                <span>Exposure range</span>
                                <strong>
                                  {impact.exposure_days_range
                                    ?.map(format)
                                    .join("–") || "—"}{" "}
                                  days
                                </strong>
                              </div>
                            </div>
                          </article>
                        ))}
                      </>
                    )}
                  </section>
                )}

                <section className="panel">
                  <h2>Approval policy</h2>
                  <p className="muted">
                    Limits are explicit organisation assumptions. A separate
                    approver is required by default.
                  </p>
                  <div className="platform-form-row">
                    <label>
                      Currency
                      <input
                        maxLength={3}
                        value={currency}
                        onChange={(e) =>
                          setCurrency(e.target.value.toUpperCase())
                        }
                      />
                    </label>
                    <label>
                      Maximum spend
                      <input
                        type="number"
                        min="0"
                        value={spend}
                        onChange={(e) => setSpend(Number(e.target.value))}
                      />
                    </label>
                    <label>
                      Automatic approval limit
                      <input
                        type="number"
                        min="0"
                        value={automatic}
                        onChange={(e) => setAutomatic(Number(e.target.value))}
                      />
                    </label>
                    <button
                      className="secondary"
                      disabled={busy || !can("admin")}
                      onClick={() =>
                        void run(() =>
                          call("/policy", token, {
                            currency,
                            spend_limit: measure(
                              spend,
                              currency,
                              "Organisation spending limit",
                            ),
                            auto_approve_limit: measure(
                              automatic,
                              currency,
                              "Organisation automatic approval limit",
                            ),
                            approval_sla: measure(
                              24,
                              "hour",
                              "Organisation approval SLA",
                            ),
                          }),
                        )
                      }
                    >
                      Save policy
                    </button>
                  </div>
                </section>

                <section id="approvals" className="panel">
                  <h2>{labels.approvals}</h2>
                  <label>
                    Decision or rollback reason
                    <textarea
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder="Explain the evidence and decision"
                    />
                  </label>
                  {assessment && (
                    <details>
                      <summary>Draft a mitigation from a sourced quote</summary>
                      <div className="platform-form-row">
                        <label>
                          Quote source and rationale
                          <input
                            value={quote}
                            onChange={(e) => setQuote(e.target.value)}
                          />
                        </label>
                        <label>
                          Cost
                          <input
                            type="number"
                            min="0"
                            value={cost}
                            onChange={(e) => setCost(Number(e.target.value))}
                          />
                        </label>
                        <label>
                          Duration in days
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
                          Create approval draft
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
                          <span className="badge">{r.status}</span>
                          <p>{String(r.payload.rationale)}</p>
                          <p className="muted small">
                            {format((r.payload.cost as Measure).value)}{" "}
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
                                  busy || !reason.trim() || !can("approver")
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
                                Approve
                              </button>
                              <button
                                disabled={
                                  busy || !reason.trim() || !can("approver")
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
                                Reject
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
                              Record dry-run preview
                            </button>
                          )}
                        </div>
                      </article>
                    ))}
                  {!records.some((r) => r.kind === "mitigation") && (
                    <p className="muted">
                      Assess a disruption, then draft a sourced mitigation to
                      begin review.
                    </p>
                  )}
                </section>

                <section className="panel">
                  <h2>{labels.alerts}</h2>
                  {records
                    .filter((r) => ["alert", "notification"].includes(r.kind))
                    .map((r) => (
                      <article className="record-row" key={r.id}>
                        <div>
                          <strong>
                            {String(r.payload.title || r.payload.type)}
                          </strong>
                          <p className="muted">{r.status}</p>
                          {r.kind === "alert" && r.status === "open" && (
                            <div className="button-row">
                              <label>
                                Acknowledgement reason
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
                                Acknowledge alert
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
                                  "Unmatched event",
                              )}
                            </strong>
                            <p className="muted">Event needs entity review</p>
                            <div className="button-row">
                              <label>
                                Match to entity
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
                                  <option value="">Select an entity</option>
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
                                Resolution reason
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
                                Resolve event
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
                      No alerts or approval notifications yet.
                    </p>
                  )}
                </section>

                <section className="panel">
                  <h2>Reports and audit</h2>
                  <p>
                    {state.audit?.valid
                      ? "Audit chain verified"
                      : "Audit verification requires attention"}{" "}
                    · {state.audit?.count || 0} records
                  </p>
                  <div className="button-row">
                    <button
                      className="secondary"
                      onClick={() =>
                        void run(() =>
                          download("/audit", "substrata-audit.json"),
                        )
                      }
                    >
                      Export audit JSON
                    </button>
                    <button
                      className="secondary"
                      onClick={() =>
                        void run(() =>
                          download("/exports/graph.csv", "substrata-graph.csv"),
                        )
                      }
                    >
                      Export CSV
                    </button>
                  </div>
                  <p className="mono break">Chain head: {state.audit?.head}</p>
                </section>
              </>
            )}
          </>
        )}
      </main>
    </>
  );
}
