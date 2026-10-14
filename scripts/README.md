# Development scripts

Invoke `python scripts/dev.py TASK` from the root, or use the script's absolute path.

| Task | Behavior |
|---|---|
| setup | Install locked dev/platform dependencies; create .venv and preserve existing .env |
| migrate | Upgrade schema without resetting records |
| seed | Write fixtures and reset synthetic business/session data |
| evaluate | Measure fixture, persist results and regenerate EVALUATION.md results |
| test | Run pytest and frontend type checking |
| lint | Check Ruff lint/format and frontend ESLint |
| api / ui | Start the selected loopback service |
| demo | Start API/UI; Ctrl+C stops both owned process trees |
| build | Export frontend/out |

Tasks after setup use .venv automatically. Root .env supplies ports and optional
LLM/policy settings; shell values take precedence. Dev/build share API URL
selection; NEXT_PUBLIC_API_URL is embedded at build time. Gemini primary/Groq
backup needs backend keys; explicit provider=mock needs no network after installation.
See [LLM setup](../docs/LLM_SETUP.md). Stop servers before setup or CLI seed.

Makefile forwards the same tasks. GNU Make is unavailable on this Windows
workstation; the Python runner is verified. Non-Windows process cleanup remains
unverified. See docs/DEMO_SCRIPT.md for recovery.

`python scripts/verify_postgres.py` starts an owned disposable PostgreSQL/pgvector
container and runs the PostgreSQL workflow/isolation checks using project `.venv`
dependencies. `--full-suite` runs every Python test with PostgreSQL integration
enabled. Docker Desktop's Windows CLI is discovered even when missing from PATH;
`--docker PATH` overrides discovery. Generated test credentials stay in child
environments, the loopback port is selected dynamically, and cleanup removes only
this command's container/anonymous volume. See [Operations](../docs/OPERATIONS.md).
