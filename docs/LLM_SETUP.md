# Gemini primary, Groq backup

The application's extraction provider is **Google Gemini**, with **Groq** as
backup. It calls the providers directly from Python without a provider SDK. API
keys are never sent to the browser or stored in agent results.

## Configure

Setup creates a root `.env` without overwriting an existing file. Set:

```dotenv
SUBSTRATA_LLM_PROVIDER=gemini
GEMINI_API_KEY=your-google-api-key
GROQ_API_KEY=your-groq-api-key
SUBSTRATA_GEMINI_MODEL=gemini-3.8-flash
SUBSTRATA_GROQ_MODEL=openai/gpt-oss-120b
SUBSTRATA_LLM_TIMEOUT_SECONDS=20
```

Use keys from [Google AI Studio](https://aistudio.google.com/apikey) and the
[Groq console](https://console.groq.com/keys). Model access and billing belong to those
accounts. Keep `.env` local and ignored by Git. Shell environment values override
it. Restart `python scripts/dev.py demo` (or the API process) after changing keys.
Do not put keys in `NEXT_PUBLIC_*` variables or share them in chat.

The **Run the scenario** panel shows the primary and backup models and whether
keys are configured. A configured key is not proof of account access. Click
**Discover links** to run extraction; the panel identifies the answering provider.
Previous saved mock results remain historical mock results.

## Failover and evidence

Each extraction starts with Gemini. On a connection/HTTP failure, incomplete
response or invalid extraction JSON, it tries Groq once. The next extraction starts
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
Gemini or Groq quality. Provider tests intercept HTTP to exercise request formats,
primary success, failover, recovery, malformed responses and missing credentials.
Live extraction was exercised on 9 October 2026 with an isolated synthetic
workspace. Gemini returned `connection_failed`; Groq successfully answered the
fallback request using `openai/gpt-oss-120b`. The Mapper accepted two supported
links and queued three uncertain claims for simulated supplier confirmation.
This verifies the live Groq path and fallback for that run, not Gemini extraction
success or real-world extraction quality. Requests identify the application with
`User-Agent: Substrata/0.1`; the default Python user agent was rejected by Groq
with HTTP 403 during the initial check. Credentials remain local and ignored.

Official API contracts checked on 9 October 2026:

- [Gemini Interactions API](https://ai.google.dev/api/interactions-api) and
  [structured output](https://ai.google.dev/gemini-api/docs/structured-output).
- [Groq structured outputs](https://console.groq.com/docs/structured-outputs),
  [Chat Completions API](https://console.groq.com/docs/api-reference) and the
  [`openai/gpt-oss-120b` model](https://console.groq.com/docs/model/openai/gpt-oss-120b).
  The OpenAI-compatible Groq endpoint is used directly; this adapter uses no
  conversation storage or tools.
