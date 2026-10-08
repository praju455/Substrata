# Frontend

Minimal Next.js App Router, TypeScript and Tailwind workspace. It visibly labels
all content as synthetic and shows an empty supplier-network panel plus the
planned demo workflow. No supplier records, graph interactions or API calls are
connected yet.

## Local development

Requires Node.js 24.x and npm. From the repository root in PowerShell:

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev
```

Open `http://127.0.0.1:3000`. Stop the server with `Ctrl+C`.

## Checks and static output

```powershell
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

The build writes static files to `frontend/out/`. Next.js is configured with
`output: "export"`; no Next.js production server is required to serve those files.
Fonts and artwork are local/system resources, so the exported page does not
need external font or image requests.

## Dependency notes

Direct versions and transitive resolutions are pinned in `package.json` and
`package-lock.json`. The lint stack uses ESLint 9 to satisfy the current plugin
peer ranges, although npm marks that ESLint release as unsupported. The npm
audit also reports an unpatched `braces` advisory through the development-only
Next.js lint plugin. Runtime-only audit reported zero vulnerabilities at this
checkpoint. See [D006](../docs/DECISIONS.md#d006-static-frontend-scaffold) for the
scope and follow-up.

## Next implementation boundaries

Cytoscape graph interactions, direct FastAPI SSE, replay controls, cascade
results, approvals and audit remain planned. **[Design]** Business calculations
stay in Python; Next.js route handlers and Server Actions are not used.
