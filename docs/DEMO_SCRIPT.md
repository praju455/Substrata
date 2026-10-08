# Three-minute synthetic demo

## Prepare

Requires Python 3.12+, Node.js 24.x and npm. From the repository root:

```powershell
python scripts/dev.py setup
python scripts/dev.py seed
python scripts/dev.py evaluate
python scripts/dev.py demo
```

Setup needs internet for dependencies; default mock replay works offline afterward.
Open http://127.0.0.1:3000/ and leave the terminal running. Start fresh; if needed
click **Reset demo → Reset synthetic session**. Reset intentionally clears demo
approvals and audit history. All session records are disposable synthetic data.

## Exact click path and talking points

1. **0:00–0:25 — Network.** Point out **Synthetic demo data** and 12 supplier
   sites. Several visible Tier-1 groups appear independent. “These companies and
   ERP inputs are invented. We are demonstrating a decision workflow.”
2. **0:25–0:55 — Discover links.** Click **Discover links ↗**. Two claims become
   dashed inferred edges; three candidates need review. In **Inspect a
   relationship**, select **Cobalt Assemblies → Meridian Semiconductors · inferred**.
   Inspect the synthetic quote, 92% uncalibrated workflow score, source URI and
   content hash. “A score is not verification.”
3. **0:55–1:20 — Verify claims.** Click **Simulate supplier replies**. Expand
   **Supplier confirmations**: two true claims confirm and one false rumor rejects.
   Meridian is highlighted as shared through three groups. “Replies use separate
   synthetic truth. No supplier was contacted. Ownership/control propagation is
   an explicit scenario assumption.”
4. **1:20–1:55 — Replay.** Click **▶ Replay next event** once. Watch Agent activity
   receive/match/cascade/propose updates. The runway defaults to Power module /
   Pune assembly: **18 days cover**, **90 days requalification**, **72 days exposure**.
   Open **Calculation provenance and pinned versions**. “Python calculates these
   values from frozen graph, ERP and formula inputs. The model computes no numbers.”
5. **1:55–2:35 — Govern the decision.** In **Compare simulated responses**, enter
   **Your name** (e.g. Demo Reviewer), keep **Procurement approver**, and enter a
   **Decision reason** (e.g. Review the buffer draft for the 72-day exposure).
   Find **Draft a buffer purchase**, inspect its payload, then click **Approve
   simulation** inside that card. “Costs, duration, risk and the USD 10,000 threshold
   are assumptions. This records a draft, not a purchase.”
6. **2:35–3:00 — Trace it.** Click **Audit** in navigation, then **Verify chain**.
   Expand **approved** and **logged** to inspect the name, reason, input hashes
   and exact simulated payload. “The chain detects later changes; it does not
   establish source truth. Local roles are self-declared, not authenticated.”

Optional: replay through event four to show an ambiguous entity in **Analyst
review**. Enter name/reason in the decision form and select a candidate. Refresh
creates a new frozen analysis and supersedes pending requests from the old one.

## Recovery

If disconnected, check the terminal and restart `python scripts/dev.py demo`.
If a preview shows an old connection-error page, reopen the HTTP workspace URL.
Use **Reset demo** before repeating. To recreate fixtures manually: stop servers
with Ctrl+C, run `python scripts/dev.py seed`, optionally `evaluate`, then `demo`.
Do not reseed a running API from another terminal.

A stale or expired approval is intentionally rejected: click **Recalculate with
current inputs**, inspect the new snapshot, and decide again. Missing inputs or
truncated traversal block decisions. An invalid chain blocks changes; reset the
disposable synthetic session to recover the demo.

## Three checks before presenting

1. Verify ports, the live indicator and one full mock click path on the presenting
   machine. GNU Make and non-Windows process cleanup were not executed here.
2. Use mock mode unless a real provider has been separately verified. The optional
   HTTP adapter has mocked transport-contract tests only.
3. Explain synthetic assumptions and local roles. SAP, supplier contact, production
   authentication and real execution remain unimplemented. Full npm audit retains
   the development lint-chain advisory described in D006.
