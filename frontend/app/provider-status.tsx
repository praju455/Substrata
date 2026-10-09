import type { LLMProvider, Workspace } from "./types";

function providerLabel(provider: string) {
  if (provider === "gemini") return "Gemini";
  if (provider === "groq") return "Groq";
  return provider;
}

function Provider({ label, provider }: { label: string; provider: LLMProvider }) {
  return (
    <div className="provider-row">
      <div>
        <span className="muted">{label}</span>
        <strong>{providerLabel(provider.provider)}</strong>
        <span className="provider-model">{provider.model}</span>
      </div>
      <span>{provider.credential_configured ? "Key configured" : "Key needed"}</span>
    </div>
  );
}

export default function ProviderStatus({ llm }: { llm: Workspace["llm"] }) {
  if (llm.mode === "mock") {
    return (
      <div className="provider-status">
        <strong>Offline mock extraction</strong>
        <p>Deterministic template demo. No live LLM calls.</p>
      </div>
    );
  }
  const last = llm.last_attempts.at(-1);
  return (
    <div className="provider-status" aria-label="AI providers">
      <Provider label="Primary" provider={llm.primary} />
      {llm.backup && <Provider label="Backup" provider={llm.backup} />}
      {(!llm.primary.credential_configured || !llm.backup?.credential_configured) && (
        <p>Add the missing API keys to .env, then restart the API.</p>
      )}
      {last && (
        <p role="status">
          {last.status === "completed"
            ? `Last extraction answered by ${providerLabel(last.provider)}.`
            : "Last extraction failed. Check the provider configuration."}
        </p>
      )}
    </div>
  );
}
