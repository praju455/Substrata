# Prototype build checkpoints

The implementation follows README.md, ARCHITECTURE.md, DATA_MODEL.md,
TECH_STACK.md, EVALUATION.md and RESEARCH.md. The demo uses synthetic data and
simulated actions only. **[Design]**

## Working agreement

At each small checkpoint: implement only that checkpoint, run applicable checks,
commit locally, explain what exists and what was verified, then stop for the
user's review. Handle pushing after that review and wait for the user's direction
before starting the next checkpoint. This follows the user's explicit request
on 8 October 2026.

Working branch: `feat/prototype-vertical-slice`.

## M0: scaffold, split into small steps

| Checkpoint | Deliverable | Status |
|---|---|---|
| M0.1 | Specification review, project folders, Git ignore rules and this checklist | Complete; no runnable application yet |
| M0.2 | Minimal FastAPI app, health endpoint, pinned Python dependencies, pytest and Ruff configuration | Planned |
| M0.3 | Minimal Next.js / TypeScript / Tailwind app, synthetic-data label and verified static build | Planned |
| M0.4 | Verified setup, seed, test, lint, api, ui and demo entry points; `.env.example`; README commands | Planned |

For M0.4, `seed` must clearly report that scenario seeding is pending until M1;
`demo` can launch the scaffold only. Neither command may imply that the complete
scenario exists. **[Design]** Windows command support must be verified because
GNU Make is not available in the current shell.

## Later milestones

These remain planned. Before starting each milestone, split it into small,
reviewable checkpoints and update this checklist. **[Design]**

| Milestone | Scope | Status |
|---|---|---|
| M1 | Database schema, deterministic seed, separate true/declared graphs and synthetic evidence | Planned |
| M2 | GraphStore, deterministic cascade formulas and edge-case tests | Planned |
| M3 | Mock-first LLM interface, evidence-backed Mapper, supplier confirmations and measured evaluation | Planned |
| M4 | Event replay, ranked simulated actions, approval gate, hash-chained audit, API and SSE | Planned |
| M5 | Graph, replay feed, cascade card, approval queue, audit view and demo script | Planned |

## Current verification

M0.1 checks are limited to repository structure, documentation consistency,
ignored local artifacts and `git diff --check`. Tests and Ruff are not yet
configured; no application test or lint success is claimed.
