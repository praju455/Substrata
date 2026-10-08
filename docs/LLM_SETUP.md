# Gemini primary, Grok backup

The application's extraction provider is **Google Gemini**, with **xAI Grok** as
backup. It calls the providers directly from Python; no OpenAI service or SDK is
used. API keys are never sent to the browser or stored in agent results.

## Configure

Setup creates a root `.env` without overwriting an existing file. Set:

```dotenv
SUBSTRATA_LLM_PROVIDER=gemini
GEMINI_API_KEY=your-google-api-key
XAI_API_KEY=your-xai-api-key
SUBSTRATA_GEMINI_MODEL=gemini-3.8-flash
SUBSTRATA_GROK_MODEL=grok-4.7
SUBSTRATA_LLM_TIMEOUT_SECONDS=20
```

Use keys from [Google AI Studio](https://aistudio.google.com/apikey) and the
[xAI console](https://console.x.ai/). Model access and billing belong to those
accounts. Keep `.env` local and ignored by Git. Shell environment values override
it. Restart `python scripts/dev.py demo` (or the API process) after changing keys.
Do not put keys in `NEXT_PUBLIC_*` variables or share them in chat.

The **Run the scenario** panel shows the primary and backup models and whether
keys are configured. A configured key is not proof of account access. Click
**Discover links** to run extraction; the panel identifies the answering provider.
Previous saved mock results remain historical mock results.

## Failover and evidence

Each extraction starts with Gemini. On a connection/HTTP failure, incomplete
response or invalid extraction JSON, it tries Grok once. The next extraction starts
with Gemini again. Explicit refusals are not retried through another provider.
Both providers use the same JSON schema and evidence. Each request has a configured
socket timeout (maximum 120 seconds), a 4,096-token output cap and a 1 MiB response
limit. There is no unbounded retry loop or automatic fallback to mock data.

If both providers fail or have no keys, `/mapper/run` returns HTTP 503 with safe
setup/error guidance. The workspace stays available and no graph links are written.
Agent runs retain the actual provider/model, prompt version, attempt statuses,
error codes and latency; upstream error bodies and credentials are excluded.

The Mapper still checks exact evidence quotes and known endpoints before committing
any links. Schema-valid but unsupported claims fail closed; they do not trigger
another model attempt. Confidence, graph traversal, stock cover, mitigation ranking,
approval and audit remain deterministic Python operations. The current extraction
scope is explicit ownership sentences, not general web research or semantic search.
Real provider embedding methods remain deferred.

## Offline demo and verification

Set `SUBSTRATA_LLM_PROVIDER=mock` explicitly for the reproducible offline demo.
Tests and `python scripts/dev.py evaluate` always use offline fixtures/mocks,
regardless of the application's provider setting. Evaluation results do not measure
Gemini or Grok quality. Provider tests intercept HTTP to exercise request formats,
primary success, failover, recovery, malformed responses and missing credentials.
Live provider calls have not been verified yet; the user will add keys later.

Official API contracts checked on 8 October 2026:

- [Gemini Interactions API](https://ai.google.dev/api/interactions-api) and
  [structured output](https://ai.google.dev/gemini-api/docs/structured-output).
- [Grok structured output](https://docs.x.ai/developers/model-capabilities/text/structured-outputs)
  and [Chat Completions](https://docs.x.ai/developers/rest-api-reference/inference/chat-completions).
  The supported stateless endpoint is used directly; xAI recommends Responses for
  new stateful integrations. This adapter uses no conversation storage or tools.
