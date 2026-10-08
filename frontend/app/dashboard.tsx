"use client";

import dynamic from "next/dynamic";
import {
  Component,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { GraphEdge, Impact, StreamEvent, Workspace } from "./types";
import ProviderStatus from "./provider-status";

const API = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");
const Network = dynamic(() => import("./network"), {
  ssr: false,
  loading: () => (
    <div className="empty graph-canvas">Loading interactive network…</div>
  ),
});
const number = (value: number | null | undefined) =>
  value == null
    ? "—"
    : new Intl.NumberFormat("en", { maximumFractionDigits: 2 }).format(value);
const percent = (value: number) =>
  new Intl.NumberFormat("en", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(value);
const dollars = (value: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
const human = (value: string) => value.replaceAll("_", " ");

async function request(path: string, body?: object): Promise<unknown> {
  const response = await fetch(API + path, {
    method: body === undefined ? "GET" : "POST",
    cache: "no-store",
    headers:
      body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data: unknown = await response.json();
  if (!response.ok) {
    const detail =
      typeof data === "object" && data && "detail" in data ? data.detail : null;
    throw new Error(
      typeof detail === "string"
        ? detail
        : `Request failed (${response.status}). Check the entered fields.`,
    );
  }
  return data;
}

class GraphBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div className="empty">
        Graph could not load. Use the relationship list to inspect the same
        records.
      </div>
    ) : (
      this.props.children
    );
  }
}

function Badge({ value }: { value: string }) {
  return <span className={`badge ${value.toLowerCase()}`}>{human(value)}</span>;
}
function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}

function Evidence({
  edge,
  names,
}: {
  edge: GraphEdge;
  names: Map<string, string>;
}) {
  return (
    <div className="evidence-body">
      <div className="row">
        <strong>
          {names.get(edge.source)} → {names.get(edge.target)}
        </strong>
        <Badge value={edge.status} />
      </div>
      <p className="muted small">
        {human(edge.edge_type)} · Workflow score {percent(edge.confidence)} ·
        Uncalibrated
      </p>
      {edge.evidence.length === 0 ? (
        <p className="small muted">
          Declared synthetic relationship. No inferred evidence attached.
        </p>
      ) : (
        edge.evidence.map((citation) => (
          <blockquote key={citation.id}>
            <span className="eyebrow">
              {citation.stance} · {human(citation.source_kind)}
            </span>
            <p>“{citation.quote}”</p>
            <details>
              <summary>Source and integrity details</summary>
              <p className="small break">{citation.source_uri}</p>
              <p className="mono break">SHA-256: {citation.sha256}</p>
            </details>
          </blockquote>
        ))
      )}
    </div>
  );
}

function Runway({ impact }: { impact: Impact }) {
  return (
    <>
      <div className="row impact-label">
        <strong>{impact.component_name}</strong>
        <span className="muted small">
          {impact.plant_name} · {impact.unit}
        </span>
        <Badge value={impact.status} />
      </div>
      {impact.reason && (
        <p className="notice warning">
          {impact.reason} Numerical results and action approval are blocked.
        </p>
      )}
      <div className="runway-metrics">
        <div>
          <span>Stock cover</span>
          <strong>
            {number(impact.cover_days)}
            <small> days</small>
          </strong>
        </div>
        <div>
          <span>Requalification</span>
          <strong>
            {number(impact.requalification_days)}
            <small> days</small>
          </strong>
        </div>
        <div className="risk-metric">
          <span>Exposure window</span>
          <strong>
            {number(impact.exposure_window)}
            <small> days</small>
          </strong>
        </div>
        <div>
          <span>Priority score</span>
          <strong>
            {number(impact.priority)}
            <small> / 100</small>
          </strong>
        </div>
      </div>
      {impact.status === "complete" && (
        <div
          className="timeline"
          aria-label={`${number(impact.cover_days)} days covered, ${number(impact.exposure_window)} days exposed`}
        >
          <span style={{ flexGrow: impact.cover_days ?? 0 }} />
          <span style={{ flexGrow: impact.exposure_window ?? 0 }} />
        </div>
      )}
      <div className="row small muted">
        <span>
          {number(impact.on_hand)} on hand + {number(impact.in_transit)}{" "}
          eligible in transit
        </span>
        <span>
          {number(impact.daily_consumption)} {impact.unit}/day
        </span>
        <span>Path score {percent(impact.path_confidence)}</span>
      </div>
    </>
  );
}

export default function Dashboard() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [feed, setFeed] = useState<StreamEvent[]>([]);
  const [selection, setSelection] = useState<{
    kind: "node" | "edge";
    id: string;
  } | null>(null);
  const [scenarioId, setScenarioId] = useState("");
  const [impactIndex, setImpactIndex] = useState(0);
  const [actor, setActor] = useState("");
  const [role, setRole] = useState("procurement_approver");
  const [reason, setReason] = useState("");
  const [resetArmed, setResetArmed] = useState(false);
  const generation = useRef("");
  const refreshing = useRef(false);

  const refresh = useCallback(async () => {
    if (refreshing.current) return;
    refreshing.current = true;
    try {
      const data = (await request("/state")) as Workspace;
      if (!data.synthetic || !Array.isArray(data.graph?.nodes))
        throw new Error("Unexpected workspace response.");
      setWorkspace(data);
      setError(null);
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Could not load the local demo.",
      );
    } finally {
      refreshing.current = false;
    }
  }, []);

  useEffect(() => {
    const initial = setTimeout(() => void refresh(), 0);
    let timer: ReturnType<typeof setTimeout> | undefined;
    const stream = new EventSource(API + "/stream");
    stream.onopen = () => {
      setConnected(true);
      void refresh();
    };
    stream.onerror = () => setConnected(false);
    stream.onmessage = (event) => {
      try {
        const row: StreamEvent = JSON.parse(event.data);
        const nextGeneration = event.lastEventId.split(":")[0];
        const changed = generation.current !== nextGeneration;
        generation.current = nextGeneration;
        setFeed((previous) =>
          changed
            ? [row]
            : [...previous.filter((item) => item.id !== row.id), row].slice(
                -60,
              ),
        );
        if (changed) setSelection(null);
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => void refresh(), 80);
      } catch {
        setError("A live update could not be read. Refresh the workspace.");
      }
    };
    stream.addEventListener("reset", () => {
      setFeed([]);
      setSelection(null);
      void refresh();
    });
    return () => {
      stream.close();
      clearTimeout(initial);
      if (timer) clearTimeout(timer);
    };
  }, [refresh]);

  useEffect(() => {
    if (!workspace?.replay.active) return;
    const interval = setInterval(() => void refresh(), 500);
    return () => clearInterval(interval);
  }, [workspace?.replay.active, refresh]);

  const run = async (label: string, path: string, body: object = {}) => {
    setBusy(label);
    setNotice(null);
    try {
      const result = await request(path, body);
      if (
        result &&
        typeof result === "object" &&
        "scenario_id" in result &&
        typeof result.scenario_id === "string"
      ) {
        setScenarioId(result.scenario_id);
        setImpactIndex(0);
      }
      await refresh();
      setNotice(label + " complete.");
    } catch (failure) {
      setNotice(
        failure instanceof Error ? failure.message : "The request failed.",
      );
      await refresh();
    } finally {
      setBusy(null);
    }
  };
  const verify = async () => {
    setBusy("Audit verification");
    try {
      await request("/audit/verify");
      await refresh();
      setNotice("Audit verification complete.");
    } catch (failure) {
      setNotice(
        failure instanceof Error
          ? failure.message
          : "Audit verification failed.",
      );
    } finally {
      setBusy(null);
    }
  };
  const select = useCallback(
    (kind: "node" | "edge", id: string) => setSelection({ kind, id }),
    [],
  );
  const names = new Map(
    workspace?.graph.nodes.map((n) => [n.id, n.name]) ?? [],
  );
  const selectedEdge =
    selection?.kind === "edge"
      ? workspace?.graph.edges.find((e) => e.id === selection.id)
      : null;
  const selectedNode =
    selection?.kind === "node"
      ? workspace?.graph.nodes.find((n) => n.id === selection.id)
      : null;
  const scenario =
    workspace?.scenarios.find((s) => s.id === scenarioId) ??
    workspace?.scenarios.at(-1);
  const selectedImpactIndex = Math.min(
    impactIndex,
    Math.max(0, (scenario?.report.impacts.length ?? 0) - 1),
  );
  const impact = scenario?.report.impacts[selectedImpactIndex];
  const actions =
    workspace?.actions.filter((a) => a.scenario_id === scenario?.id) ?? [];
  const pendingReplies =
    workspace?.confirmations.filter((c) => c.status === "pending").length ?? 0;
  const mapped =
    (workspace?.graph.edges.some((e) => e.status !== "declared") ||
      workspace?.confirmations.length) ??
    false;
  const disabled = !!busy || !workspace || !connected;

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to workspace
      </a>
      <header className="site-header">
        <div className="shell header-inner">
          <a className="brand" href="#main">
            <svg viewBox="0 0 32 32" aria-hidden="true">
              <path
                d="m3 10 13-7 13 7-13 7-13-7Zm0 7 13 7 13-7M3 24l13 7 13-7"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.4"
              />
            </svg>
            Substrata
          </a>
          <nav aria-label="Workspace sections">
            <a href="#network">Network</a>
            <a href="#workflow">Replay</a>
            <a href="#approvals">Decisions</a>
            <a href="#audit">Audit</a>
          </nav>
          <span className="synthetic-label">Synthetic demo data</span>
        </div>
      </header>
      <main id="main" className="shell main-content">
        <div className="hero">
          <div>
            <p className="eyebrow purple">SUPPLY NETWORK INTELLIGENCE</p>
            <h1>See beneath the surface.</h1>
            <p className="muted">
              Find the shared dependency. Understand your runway. Make an
              accountable decision.
            </p>
          </div>
          <div className="hero-controls">
            <span className={`connection ${connected ? "online" : ""}`}>
              <i />
              {connected ? "Live workspace" : "Reconnecting…"}
            </span>
            <button
              className="secondary"
              disabled={disabled}
              onClick={() => setResetArmed(!resetArmed)}
            >
              Reset demo
            </button>
          </div>
        </div>
        {resetArmed && (
          <div className="notice warning row">
            <span>
              Reset clears this synthetic session, including approvals and audit
              history.
            </span>
            <button
              disabled={disabled}
              className="danger-button"
              onClick={() => {
                setResetArmed(false);
                setScenarioId("");
                setImpactIndex(0);
                void run("Demo reset", "/replay/reset");
              }}
            >
              Reset synthetic session
            </button>
            <button className="quiet" onClick={() => setResetArmed(false)}>
              Cancel
            </button>
          </div>
        )}
        {error && (
          <div className="notice error" role="alert">
            <strong>Local demo unavailable.</strong> {error} Start the API and
            UI with <code>python scripts/dev.py demo</code>.{" "}
            <button className="quiet" onClick={() => void refresh()}>
              Retry connection
            </button>
          </div>
        )}
        {(busy || notice) && (
          <div className="notice" role="status">
            {busy ? `${busy}…` : notice}
          </div>
        )}
        {!workspace ? (
          <div className="loading-grid" aria-busy="true">
            <Empty>Loading supplier network…</Empty>
            <Empty>Loading replay, impact and approval state…</Empty>
          </div>
        ) : (
          <>
            {!workspace.audit.valid && (
              <div className="notice error" role="alert">
                Audit verification failed at record{" "}
                {workspace.audit.error_sequence}. Further decisions are blocked.
              </div>
            )}
            <div className="summary-grid">
              <div>
                <span>Supplier sites</span>
                <strong>
                  {
                    workspace.graph.nodes.filter(
                      (n) => n.node_type === "SupplierSite",
                    ).length
                  }
                  <small> in the synthetic network</small>
                </strong>
              </div>
              <div>
                <span>Inferred links</span>
                <strong>
                  {
                    workspace.graph.edges.filter((e) => e.status === "inferred")
                      .length
                  }
                  <small> evidence-backed proposals</small>
                </strong>
              </div>
              <div>
                <span>Awaiting approval</span>
                <strong>
                  {
                    workspace.actions.filter(
                      (a) => a.status === "awaiting_approval",
                    ).length
                  }
                  <small> simulated options</small>
                </strong>
              </div>
              <div>
                <span>Decision trail</span>
                <strong className={workspace.audit.valid ? "teal" : "red"}>
                  {workspace.audit.valid ? "Verified" : "Invalid"}
                  <small>{workspace.audit.count} chained records</small>
                </strong>
              </div>
            </div>
            <div className="workspace-grid">
              <section
                id="network"
                className="panel network-panel"
                aria-labelledby="network-title"
              >
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">THE OBSERVABLE GRAPH</p>
                    <h2 id="network-title">Supplier network</h2>
                  </div>
                  <span className="small muted">
                    Version {workspace.graph.version} ·{" "}
                    {workspace.graph.edges.length} links
                  </span>
                </div>
                <GraphBoundary>
                  <Network
                    graph={workspace.graph}
                    sharedIds={workspace.shared_dependencies.map(
                      (d) => d.node_id,
                    )}
                    onSelect={select}
                  />
                </GraphBoundary>
                <div className="legend">
                  <span>
                    <i className="solid" />
                    Declared
                  </span>
                  <span>
                    <i className="dashed" />
                    Inferred
                  </span>
                  <span>
                    <i className="confirmed-line" />
                    Confirmed
                  </span>
                  <span>
                    <i className="faded" />
                    Rejected / expired
                  </span>
                  <span>
                    <i className="risk-dot" />
                    Shared dependency
                  </span>
                </div>
                {workspace.shared_dependencies.some(
                  (d) => d.node_id === "site_shared_source",
                ) && (
                  <div className="shared-callout">
                    <strong>One source. Three apparent alternatives.</strong>
                    <span>
                      Meridian Semiconductors connects three supplier groups
                      through the synthetic ownership/control model.
                    </span>
                  </div>
                )}
                <div className="inspector">
                  <label htmlFor="relationship">Inspect a relationship</label>
                  <select
                    id="relationship"
                    value={selectedEdge?.id ?? ""}
                    onChange={(e) =>
                      e.target.value && select("edge", e.target.value)
                    }
                  >
                    <option value="">Choose a link, or click the graph</option>
                    {[...workspace.graph.edges]
                      .sort(
                        (a, b) =>
                          (a.status === "declared" ? 1 : 0) -
                          (b.status === "declared" ? 1 : 0),
                      )
                      .map((e) => (
                        <option key={e.id} value={e.id}>
                          {names.get(e.source)} → {names.get(e.target)} ·{" "}
                          {e.status}
                        </option>
                      ))}
                  </select>
                  {selectedEdge ? (
                    <Evidence edge={selectedEdge} names={names} />
                  ) : selectedNode ? (
                    <div className="evidence-body">
                      <strong>{selectedNode.name}</strong>
                      <p className="small muted">
                        {selectedNode.node_type} · Synthetic entity
                      </p>
                      <dl className="attributes">
                        {Object.entries(selectedNode.attributes)
                          .filter(([key]) => key !== "node_type")
                          .map(([key, value]) => (
                            <div key={key}>
                              <dt>{human(key)}</dt>
                              <dd>
                                {typeof value === "object"
                                  ? JSON.stringify(value)
                                  : String(value ?? "Missing")}
                              </dd>
                            </div>
                          ))}
                      </dl>
                    </div>
                  ) : (
                    <p className="small muted">
                      Select a node or relationship to inspect its type,
                      confidence and evidence. Pan or zoom the graph; use Fit
                      graph to return.
                    </p>
                  )}
                </div>
              </section>
              <aside className="workflow-column">
                <section
                  id="workflow"
                  className="panel workflow-panel"
                  aria-labelledby="workflow-title"
                >
                  <p className="eyebrow teal">FROM CONNECTION TO DECISION</p>
                  <h2 id="workflow-title">Run the scenario</h2>
                  {workspace.llm && <ProviderStatus llm={workspace.llm} />}
                  <div className="workflow-step">
                    <span className="step-number">01</span>
                    <div>
                      <h3>Discover the shared source</h3>
                      <p>
                        Extract ownership claims from the invented evidence
                        corpus.
                      </p>
                      <button
                        className="primary"
                        disabled={disabled || workspace.replay.active}
                        onClick={() =>
                          void run("Evidence mapping", "/mapper/run")
                        }
                      >
                        Discover links <span>↗</span>
                      </button>
                    </div>
                  </div>
                  <div className="workflow-step">
                    <span className="step-number teal-step">02</span>
                    <div>
                      <h3>Resolve uncertain claims</h3>
                      <p>
                        {pendingReplies
                          ? `${pendingReplies} candidates need a supplier reply.`
                          : "Simulated replies confirm or reject uncertain links."}{" "}
                        No supplier is contacted.
                      </p>
                      <button
                        className="secondary"
                        disabled={
                          disabled || !pendingReplies || workspace.replay.active
                        }
                        onClick={() =>
                          void run(
                            "Simulated supplier replies",
                            "/confirmations/simulate",
                          )
                        }
                      >
                        Simulate supplier replies
                      </button>
                    </div>
                  </div>
                  <div className="workflow-step">
                    <span className="step-number amber-step">03</span>
                    <div>
                      <h3>Replay a disruption</h3>
                      <p>
                        The first event affects the synthetic semiconductor
                        parent.
                      </p>
                      <div className="button-row">
                        <button
                          className="primary"
                          disabled={
                            disabled ||
                            !mapped ||
                            workspace.replay.active ||
                            workspace.replay.processed >= workspace.replay.total
                          }
                          onClick={() =>
                            void run("Event replay", "/replay/start", {
                              event_limit: 1,
                            })
                          }
                        >
                          ▶ Replay next event
                        </button>
                        <button
                          className="secondary"
                          disabled={disabled || !workspace.replay.active}
                          onClick={() =>
                            void run("Replay pause", "/replay/pause")
                          }
                        >
                          Pause
                        </button>
                      </div>
                      <p className="small muted">
                        {workspace.replay.processed} / {workspace.replay.total}{" "}
                        events processed ·{" "}
                        {workspace.replay.active ? "Replaying" : "Ready"}
                      </p>
                    </div>
                  </div>
                </section>
                <section
                  className="panel feed-panel"
                  aria-labelledby="feed-title"
                >
                  <div className="row">
                    <h2 id="feed-title">Agent activity</h2>
                    <span
                      className="live-dot"
                      aria-label={
                        connected
                          ? "Live stream connected"
                          : "Stream reconnecting"
                      }
                    />
                  </div>
                  {feed.length === 0 ? (
                    <p className="small muted">
                      Live updates appear here as you discover and replay.
                    </p>
                  ) : (
                    <ol className="feed">
                      {feed
                        .slice(-12)
                        .reverse()
                        .map((event) => (
                          <li key={event.id}>
                            <span className="feed-mark" />
                            <div>
                              <strong>{human(event.event_type)}</strong>
                              <p>
                                {typeof event.payload.title === "string"
                                  ? event.payload.title
                                  : typeof event.payload.message === "string"
                                    ? event.payload.message
                                    : "Synthetic workflow update"}
                              </p>
                              <time>
                                {new Date(event.timestamp).toLocaleTimeString(
                                  [],
                                  {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                    second: "2-digit",
                                  },
                                )}
                              </time>
                            </div>
                          </li>
                        ))}
                    </ol>
                  )}
                </section>
              </aside>
            </div>
            {workspace.confirmations.length > 0 && (
              <details className="panel confirmation-panel">
                <summary>
                  Supplier confirmations ·{" "}
                  {
                    workspace.confirmations.filter(
                      (c) => c.status !== "pending",
                    ).length
                  }{" "}
                  resolved of {workspace.confirmations.length}
                </summary>
                <div className="confirmation-grid">
                  {workspace.confirmations.map((c) => (
                    <article key={c.id}>
                      <Badge value={c.status} />
                      <p>“{c.quote}”</p>
                      <span className="small muted">
                        Workflow score {percent(c.confidence)} · Simulated reply
                      </span>
                    </article>
                  ))}
                </div>
              </details>
            )}
            {workspace.events.some((e) => e.status === "NEEDS_REVIEW") && (
              <section className="panel review-panel">
                <h2>Analyst review</h2>
                <p className="muted small">
                  An uncertain entity match has paused analysis. Enter your name
                  and reason in the decision form, then select a candidate.
                </p>
                {workspace.events
                  .filter((e) => e.status === "NEEDS_REVIEW")
                  .map((event) => (
                    <div key={event.id}>
                      <h3>{event.payload.title}</h3>
                      {event.candidates.map((candidate) => (
                        <button
                          className="secondary"
                          key={candidate.node_id}
                          disabled={disabled || !actor.trim() || !reason.trim()}
                          onClick={() =>
                            void run(
                              "Analyst resolution",
                              `/events/${event.id}/resolve`,
                              { node_id: candidate.node_id, actor, reason },
                            )
                          }
                        >
                          Select {names.get(candidate.node_id)} · match{" "}
                          {percent(candidate.score)}
                        </button>
                      ))}
                    </div>
                  ))}
              </section>
            )}
            <section
              className="panel impact-panel"
              aria-labelledby="impact-title"
            >
              <div className="panel-heading">
                <div>
                  <p className="eyebrow red">PRODUCTION EXPOSURE</p>
                  <h2 id="impact-title">How much runway remains?</h2>
                </div>
                {scenario && (
                  <button
                    className="secondary"
                    disabled={disabled}
                    onClick={() =>
                      void run(
                        "New snapshot analysis",
                        `/scenarios/${scenario.id}/refresh`,
                      )
                    }
                  >
                    Recalculate with current inputs
                  </button>
                )}
              </div>
              {!scenario ? (
                <Empty>
                  Replay the disruption to calculate stock cover, qualification
                  time and exposure.
                </Empty>
              ) : (
                <div className="panel-body">
                  <div className="scenario-selects">
                    <label>
                      Analysis run
                      <select
                        value={scenario.id}
                        onChange={(e) => {
                          setScenarioId(e.target.value);
                          setImpactIndex(0);
                        }}
                      >
                        {workspace.scenarios.map((s) => (
                          <option key={s.id} value={s.id}>
                            {
                              workspace.events.find((e) => e.id === s.event_id)
                                ?.payload.title
                            }{" "}
                            · {s.id}
                          </option>
                        ))}
                      </select>
                    </label>
                    {scenario.report.impacts.length > 0 && (
                      <label>
                        Component / plant
                        <select
                          value={selectedImpactIndex}
                          onChange={(e) =>
                            setImpactIndex(Number(e.target.value))
                          }
                        >
                          {scenario.report.impacts.map((i, index) => (
                            <option
                              key={i.component_id + i.plant_id}
                              value={index}
                            >
                              {i.component_name} · {i.plant_name}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                  </div>
                  {impact ? (
                    <Runway impact={impact} />
                  ) : (
                    <Empty>
                      No affected path is visible in this graph snapshot.
                      Discover links, then recalculate to compare.
                    </Empty>
                  )}
                  {scenario.report.impacts.length > 0 && (
                    <details className="impact-details">
                      <summary>
                        All affected component / plant records (
                        {scenario.report.impacts.length})
                      </summary>
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>Component / plant</th>
                              <th>Cover</th>
                              <th>Exposure</th>
                              <th>Priority</th>
                              <th>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {scenario.report.impacts.map((row, index) => (
                              <tr key={row.component_id + row.plant_id}>
                                <td>
                                  <button
                                    className="text-button"
                                    onClick={() => setImpactIndex(index)}
                                  >
                                    {row.component_name}
                                  </button>
                                  <small>{row.plant_name}</small>
                                </td>
                                <td>{number(row.cover_days)} d</td>
                                <td>{number(row.exposure_window)} d</td>
                                <td>{number(row.priority)}</td>
                                <td>
                                  <Badge value={row.status} />
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </details>
                  )}
                  <details className="small snapshot-details">
                    <summary>
                      Calculation provenance and pinned versions
                    </summary>
                    <pre>{JSON.stringify(scenario.versions, null, 2)}</pre>
                    {impact && (
                      <p>
                        Evidence:{" "}
                        {impact.evidence_ids.join(", ") ||
                          "Declared records only"}
                        . Dependency paths:{" "}
                        {impact.paths
                          .map((p) => p.map((id) => names.get(id)).join(" → "))
                          .join("; ")}
                      </p>
                    )}
                  </details>
                </div>
              )}
            </section>
            <section
              id="approvals"
              className="panel approval-panel"
              aria-labelledby="approval-title"
            >
              <div className="panel-heading">
                <div>
                  <p className="eyebrow amber">
                    HUMAN JUDGMENT STAYS IN THE LOOP
                  </p>
                  <h2 id="approval-title">Compare simulated responses</h2>
                </div>
                <span className="small muted">
                  Estimates and policy are demo assumptions
                </span>
              </div>
              <div className="panel-body">
                <div className="decision-form">
                  <label>
                    Your name
                    <input
                      value={actor}
                      maxLength={96}
                      placeholder="Named demo approver"
                      onChange={(e) => setActor(e.target.value)}
                    />
                  </label>
                  <label>
                    Demo role
                    <select
                      value={role}
                      onChange={(e) => setRole(e.target.value)}
                    >
                      <option value="procurement_approver">
                        Procurement approver
                      </option>
                      <option value="planning_approver">
                        Planning approver
                      </option>
                    </select>
                  </label>
                  <label className="reason-field">
                    Decision reason
                    <textarea
                      value={reason}
                      maxLength={2000}
                      rows={2}
                      placeholder="Explain the decision for the audit trail"
                      onChange={(e) => setReason(e.target.value)}
                    />
                  </label>
                </div>
                <p className="small muted">
                  Roles are self-declared for this local demo. Approval records
                  a simulated draft; it sends no purchase or supplier message.
                </p>
                <div className="action-grid">
                  {actions.map((action, index) => (
                    <article
                      key={action.id}
                      className={`action-card ${action.status}`}
                      aria-label={action.title}
                    >
                      <div className="row">
                        <span className="option-number">
                          OPTION {String(index + 1).padStart(2, "0")}
                        </span>
                        <Badge value={action.status} />
                      </div>
                      <h3>{action.title}</h3>
                      <div className="action-estimates">
                        <strong>{dollars(action.cost)}</strong>
                        <span>{number(action.duration_days)} days</span>
                        <span>Risk {number(action.risk)}</span>
                      </div>
                      <p>{action.rationale}</p>
                      <details>
                        <summary>Inspect simulated payload</summary>
                        <pre>{JSON.stringify(action.payload, null, 2)}</pre>
                      </details>
                      {action.status === "awaiting_approval" && (
                        <div className="button-row">
                          <button
                            className="approve-button"
                            disabled={
                              disabled || !actor.trim() || !reason.trim()
                            }
                            onClick={() =>
                              void run(
                                "Approval",
                                `/approvals/${encodeURIComponent(action.id)}/decision`,
                                { actor, role, reason, decision: "approved" },
                              )
                            }
                          >
                            Approve simulation
                          </button>
                          <button
                            className="secondary"
                            disabled={
                              disabled || !actor.trim() || !reason.trim()
                            }
                            onClick={() =>
                              void run(
                                "Rejection",
                                `/approvals/${encodeURIComponent(action.id)}/decision`,
                                { actor, role, reason, decision: "rejected" },
                              )
                            }
                          >
                            Reject
                          </button>
                        </div>
                      )}
                      <span className="simulated-note">
                        Simulated only · No external execution
                      </span>
                    </article>
                  ))}
                </div>
                {actions.length === 0 && (
                  <Empty>
                    Mitigation drafts will appear after the cascade. Every
                    execution is simulated.
                  </Empty>
                )}
              </div>
            </section>
            <section
              id="audit"
              className="panel audit-panel"
              aria-labelledby="audit-title"
            >
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">TRACE EVERY DECISION</p>
                  <h2 id="audit-title">Audit history</h2>
                </div>
                <div className="button-row">
                  <Badge
                    value={
                      workspace.audit.valid ? "chain_verified" : "chain_invalid"
                    }
                  />
                  <button
                    className="secondary"
                    disabled={disabled}
                    onClick={() => void verify()}
                  >
                    Verify chain
                  </button>
                </div>
              </div>
              <div className="panel-body">
                <p className="small muted">
                  {workspace.audit.count} records · SHA-256 chain detects later
                  changes. It does not prove the original claims are true.
                </p>
                {workspace.audit_events.length === 0 ? (
                  <Empty>No decisions recorded yet.</Empty>
                ) : (
                  <ol className="audit-list">
                    {workspace.audit_events
                      .slice(-12)
                      .reverse()
                      .map((event) => (
                        <li key={event.sequence}>
                          <span className="audit-sequence">
                            {String(event.sequence).padStart(2, "0")}
                          </span>
                          <details>
                            <summary>
                              <strong>{human(event.event_type)}</strong>
                              <span>
                                {event.actor} ·{" "}
                                {new Date(event.timestamp).toLocaleTimeString()}
                              </span>
                            </summary>
                            <pre>{JSON.stringify(event.payload, null, 2)}</pre>
                            <p className="mono break">
                              Previous: {event.previous_hash}
                              <br />
                              Hash: {event.payload_hash}
                            </p>
                          </details>
                        </li>
                      ))}
                  </ol>
                )}
                <p className="mono break">
                  Current head: {workspace.audit.head}
                </p>
              </div>
            </section>
            <aside className="limitation-note">
              <strong>Constructed scenario, measured locally.</strong> Ownership
              propagation, cost and qualification times are assumptions. This
              prototype demonstrates the workflow on invented data; it does not
              establish real-world link quality or business value.
            </aside>
          </>
        )}
        <footer>
          <span>Substrata · See what your suppliers share.</span>
          <span>Synthetic data · Simulated actions · Local prototype</span>
        </footer>
      </main>
    </>
  );
}
