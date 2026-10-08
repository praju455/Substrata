# Frontend

Next.js App Router, TypeScript, Tailwind and client-only Cytoscape dashboard:
graph/evidence inspector, replay controls, direct FastAPI SSE, server-calculated
runway, simulated approval queue and audit history. Synthetic data is labelled.

Use `python scripts/dev.py demo` from the root after setup and seed. The runner
supplies the API URL from root .env/shell configuration. Direct npm commands
use port 8000 unless NEXT_PUBLIC_API_URL is explicitly set.

```powershell
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run typecheck
python scripts/dev.py build
```

Static output is `frontend/out/`; serve it over HTTP while FastAPI runs. No
Next.js server, route handlers or Server Actions are needed. NEXT_PUBLIC_API_URL
is embedded at build time: rebuild after changing it. CORS must permit the UI
port. Fonts use system resources. Cytoscape is dynamically imported with SSR
disabled in a Client Component; graph metrics and business calculations stay
in Python. A native relationship selector provides keyboard evidence access.
Responsive panels stack on phones; loading/error/empty states give recovery.

Versions are pinned in manifests/lockfiles. Full npm audit retains the dev-only
lint-chain advisory recorded in D006; runtime audit is reported separately.
No production security or real supplier integration is claimed.
