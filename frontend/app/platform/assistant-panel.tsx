"use client";

import { useState } from "react";

import { call } from "./client";
import type { AssistantResponse, Entity } from "./contracts";
import { humanizeAssistantLabel, safeSourceHref } from "./assistant-utils";
import { useLocale } from "./i18n";

type Props = {
  token: string;
  entities: Entity[];
  selectedRelationshipId?: string;
  onSelectRelationship?: (id: string) => void;
};

const english = {
  title: "Investigate with the domain assistant",
  intro:
    "Ask about suppliers, evidence, disruptions, affected plants, assumptions or saved runway results.",
  question: "Supply-chain question",
  placeholder: "Could a current port disruption affect this plant, and what evidence supports it?",
  focus: "Optional graph focus",
  all: "Search the relevant network",
  web: "Public web evidence",
  auto: "Automatic when current information is needed",
  off: "Off — tenant evidence only",
  required: "Required for this question",
  ask: "Investigate",
  working: "Checking evidence…",
  boundary:
    "Read-only: the assistant cannot confirm a relationship, calculate impact, approve an action or write to SAP.",
  sources: "Cited sources",
  uncertainty: "What remains uncertain",
  noCitation: "No supporting source was available.",
  graph: "Graph revision",
  retrieved: "retrieved",
};

const hindi = {
  title: "डोमेन सहायक से जाँच करें",
  intro:
    "आपूर्तिकर्ता, साक्ष्य, बाधा, प्रभावित संयंत्र, मान्यता या सहेजे गए रनवे परिणाम पूछें।",
  question: "आपूर्ति-शृंखला प्रश्न",
  placeholder: "क्या मौजूदा बंदरगाह बाधा इस संयंत्र को प्रभावित कर सकती है और इसका साक्ष्य क्या है?",
  focus: "वैकल्पिक ग्राफ़ केंद्र",
  all: "संबंधित नेटवर्क खोजें",
  web: "सार्वजनिक वेब साक्ष्य",
  auto: "वर्तमान जानकारी आवश्यक होने पर स्वचालित",
  off: "बंद — केवल संगठन का साक्ष्य",
  required: "इस प्रश्न के लिए आवश्यक",
  ask: "जाँच करें",
  working: "साक्ष्य जाँचा जा रहा है…",
  boundary:
    "केवल पढ़ने योग्य: सहायक संबंध की पुष्टि, प्रभाव गणना, कार्रवाई अनुमोदन या SAP में बदलाव नहीं कर सकता।",
  sources: "उद्धृत स्रोत",
  uncertainty: "जो अभी अनिश्चित है",
  noCitation: "कोई सहायक स्रोत उपलब्ध नहीं था।",
  graph: "ग्राफ़ संशोधन",
  retrieved: "प्राप्त स्रोत",
};

export default function AssistantPanel({
  token,
  entities,
  selectedRelationshipId,
  onSelectRelationship,
}: Props) {
  const [locale] = useLocale();
  const copy = locale === "hi" ? hindi : english;
  const [question, setQuestion] = useState("");
  const [focus, setFocus] = useState("");
  const [webSearch, setWebSearch] = useState<"off" | "auto" | "required">("auto");
  const [response, setResponse] = useState<AssistantResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const ask = async () => {
    setBusy(true);
    setError("");
    try {
      setResponse(
        await call("/assistant/ask", token, {
          question: question.trim(),
          focus_entity_ids: focus ? [focus] : [],
          focus_relationship_ids: selectedRelationshipId ? [selectedRelationshipId] : [],
          web_search: webSearch,
        }),
      );
    } catch (problem) {
      setResponse(null);
      setError(
        problem instanceof Error
          ? problem.message
          : "The assistant could not complete this investigation.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <section id="assistant" className="panel assistant-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow purple">EVIDENCE-GROUNDED Q&amp;A</p>
          <h2>{copy.title}</h2>
        </div>
        <span className="badge">READ ONLY</span>
      </div>
      <p className="muted">{copy.intro}</p>
      {selectedRelationshipId && (
        <p className="notice">Focused supply-chain path: {selectedRelationshipId}</p>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void ask();
        }}
      >
        <label>
          {copy.question}
          <textarea
            required
            minLength={3}
            maxLength={2000}
            placeholder={copy.placeholder}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
          />
        </label>
        <div className="platform-form-row">
          <label>
            {copy.focus}
            <select value={focus} onChange={(event) => setFocus(event.target.value)}>
              <option value="">{copy.all}</option>
              {entities.map((entity) => (
                <option value={entity.id} key={entity.id}>
                  {entity.name} ({entity.kind})
                </option>
              ))}
            </select>
          </label>
          <label>
            {copy.web}
            <select
              value={webSearch}
              onChange={(event) =>
                setWebSearch(event.target.value as "off" | "auto" | "required")
              }
            >
              <option value="auto">{copy.auto}</option>
              <option value="off">{copy.off}</option>
              <option value="required">{copy.required}</option>
            </select>
          </label>
          <button className="primary" disabled={busy || !question.trim()}>
            {busy ? copy.working : copy.ask}
          </button>
        </div>
      </form>
      <p className="notice assistant-boundary">{copy.boundary}</p>
      {error && <p role="alert">{error}</p>}
      {response && (
        <div className="assistant-result" aria-live="polite">
          <div className="assistant-result-heading">
            <div>
              <span className={`assistant-verdict ${response.verdict}`}>
                {humanizeAssistantLabel(response.verdict)}
              </span>
              <p>{response.answer}</p>
            </div>
            <p className="muted small">
              {copy.graph}: {response.graph_version ?? "—"}<br />
              {response.model.provider} · {response.model.model}
            </p>
          </div>
          <div className="assistant-claims">
            {response.claims.map((claim, index) => (
              <article className={`assistant-claim ${claim.status}`} key={`${index}-${claim.statement}`}>
                <span className="badge">{claim.status}</span>
                <p>{claim.statement}</p>
                <small>
                  {claim.source_ids.length ? claim.source_ids.join(" · ") : copy.noCitation}
                </small>
              </article>
            ))}
          </div>
          {!!response.uncertainties.length && (
            <div className="assistant-uncertainty">
              <h3>{copy.uncertainty}</h3>
              <ul>
                {response.uncertainties.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          <h3>{copy.sources}</h3>
          <p className="muted small">
            {response.retrieval.internal_source_count} internal ·{" "}
            {response.retrieval.web_source_count} public · {copy.retrieved}
          </p>
          <div className="assistant-sources">
            {response.sources.map((source) => {
              const href = safeSourceHref(source.uri);
              return (
                <article key={source.id} className="assistant-source">
                  <span className={`badge ${source.status}`}>{source.status}</span>
                  <h4>
                    {href ? (
                      <a href={href} target="_blank" rel="noopener noreferrer">
                        {source.title}
                      </a>
                    ) : (
                      source.title
                    )}
                  </h4>
                  <p>{source.excerpt}</p>
                  <small className="mono">{source.id}</small>
                  {source.source_type === "graph_relationship" && onSelectRelationship && (
                    <button
                      className="secondary"
                      onClick={() => {
                        const id = source.id.replace("graph:relationship:", "");
                        onSelectRelationship(id);
                        document.getElementById("graph")?.scrollIntoView({ behavior: "smooth" });
                      }}
                    >
                      View relationship
                    </button>
                  )}
                </article>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}
