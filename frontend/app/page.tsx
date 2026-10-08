const workflow = [
  {
    number: "01",
    title: "Find the shared source",
    description: "Map supplier connections and review the evidence behind inferred links.",
    color: "text-graph bg-purple-50",
  },
  {
    number: "02",
    title: "Understand your runway",
    description: "Replay a disruption and compare stock cover with recovery lead times.",
    color: "text-agent bg-teal-50",
  },
  {
    number: "03",
    title: "Make a governed decision",
    description: "Review a proposed response, approve a simulated action and trace its history.",
    color: "text-human bg-amber-50",
  },
];

function BrandMark() {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden="true" className="size-8">
      <path d="m4 10 12-6 12 6-12 6-12-6Z" fill="currentColor" />
      <path d="m4 17 12 6 12-6M4 23l12 6 12-6" stroke="currentColor" strokeWidth="2.5" />
    </svg>
  );
}

export default function Home() {
  return (
    <>
      <a
        href="#main"
        className="sr-only z-10 rounded-lg bg-white px-4 py-3 focus:not-sr-only focus:absolute focus:top-3 focus:left-3"
      >
        Skip to main content
      </a>

      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-5 sm:px-8">
          <div className="flex items-center gap-3">
            <span className="text-graph"><BrandMark /></span>
            <span className="text-xl font-semibold tracking-tight">Substrata</span>
            <span className="ml-3 hidden border-l border-slate-200 pl-5 text-sm text-muted sm:block">
              Supply chain workspace
            </span>
          </div>
          <span className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-human">
            <span className="size-1.5 rounded-full bg-amber-600" aria-hidden="true" />
            Synthetic demo data
          </span>
        </div>
      </header>

      <main id="main" className="mx-auto max-w-6xl px-6 pt-10 pb-8 sm:px-8 sm:pt-14">
        <div className="mb-3 flex items-center gap-2 text-xs font-semibold tracking-widest text-muted uppercase">
          <span className="h-px w-6 bg-graph" aria-hidden="true" />
          Network intelligence
        </div>
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div>
            <h1 className="max-w-2xl text-3xl leading-tight font-semibold tracking-tight sm:text-4xl">
              See what your suppliers share.
            </h1>
            <p className="mt-4 max-w-xl text-base leading-7 text-muted">
              Discover hidden dependencies, understand production exposure and keep every decision accountable.
            </p>
          </div>
          <a href="#workflow" className="inline-flex shrink-0 items-center gap-3 self-start rounded-lg bg-graph px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-purple-800 sm:self-auto">
            Explore the workflow <span aria-hidden="true">↗</span>
          </a>
        </div>

        <div className="mt-9 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
          <section aria-labelledby="network-title" className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-6 py-5">
              <h2 id="network-title" className="text-base font-semibold">Supplier network</h2>
              <span className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-muted">No data loaded</span>
            </div>
            <div className="network-grid flex min-h-80 flex-col items-center justify-center px-6 py-10 text-center">
              <div className="mb-5 flex size-16 items-center justify-center rounded-2xl border border-purple-100 bg-white text-graph shadow-sm">
                <svg viewBox="0 0 48 48" fill="none" aria-hidden="true" className="size-10">
                  <path d="M24 13v9M12 33l12-11 12 11" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" />
                  <circle cx="24" cy="10" r="5" fill="#ede5fa" stroke="currentColor" strokeWidth="1.5" />
                  <circle cx="11" cy="36" r="5" fill="#ede5fa" stroke="currentColor" strokeWidth="1.5" />
                  <circle cx="37" cy="36" r="5" fill="#ede5fa" stroke="currentColor" strokeWidth="1.5" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold">A clearer picture starts here</h3>
              <p className="mt-2 max-w-xs text-sm leading-6 text-muted">
                Supplier connections and supporting evidence will appear here once the synthetic scenario is connected.
              </p>
            </div>
            <div className="border-t border-slate-200 px-6 py-4 text-xs leading-5 text-muted">
              Prototype preview · The interactive graph is planned.
            </div>
          </section>

          <section id="workflow" aria-labelledby="workflow-title" className="rounded-2xl border border-slate-200 bg-white p-6">
            <p className="text-xs font-semibold tracking-widest text-muted uppercase">The planned demo</p>
            <h2 id="workflow-title" className="mt-2 text-xl font-semibold tracking-tight">From connection to decision</h2>
            <ol className="mt-7 space-y-7">
              {workflow.map((step) => (
                <li key={step.number} className="flex gap-4">
                  <span className={`flex size-9 shrink-0 items-center justify-center rounded-lg text-xs font-semibold ${step.color}`} aria-hidden="true">
                    {step.number}
                  </span>
                  <div>
                    <h3 className="text-sm font-semibold">{step.title}</h3>
                    <p className="mt-1.5 text-sm leading-6 text-muted">{step.description}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </div>

        <aside className="mt-6 flex items-start gap-3 rounded-xl border border-teal-100 bg-teal-50/60 px-5 py-4 text-sm leading-6 text-agent">
          <span aria-hidden="true" className="mt-0.5 font-semibold">↳</span>
          <p><strong className="font-semibold">Human judgment stays in the loop.</strong> The planned demo uses invented business records and simulated actions only.</p>
        </aside>

        <footer className="mt-8 flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
          <p>Substrata · See beneath the surface.</p>
          <p>Prototype preview · Scenario replay and approvals are planned.</p>
        </footer>
      </main>
    </>
  );
}
