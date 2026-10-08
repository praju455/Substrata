# Development scripts

`dev.py` is the shared local command runner. From the repository root:

| Command | Behavior |
|---|---|
| `python scripts/dev.py setup` | Create/reuse `.venv`, install locked dependencies, create `.env` if absent |
| `python scripts/dev.py migrate` | Create/upgrade `data/substrata.sqlite3` to the checked-in schema revision; preserve data |
| `python scripts/dev.py seed` | Report that M1 seeding is pending; create no data |
| `python scripts/dev.py test` | Run pytest and frontend type checking |
| `python scripts/dev.py lint` | Run Ruff lint/format checks and frontend ESLint |
| `python scripts/dev.py api` | Start the API on the configured loopback port |
| `python scripts/dev.py ui` | Start the Next.js development UI on the configured loopback port |
| `python scripts/dev.py demo` | Start both scaffolds; Ctrl+C stops both |
| `python scripts/dev.py build` | Export the frontend to static files |

Commands locate the repository from the script path, so they also work when the
script is called by absolute path from another directory. Tasks after setup use
the local Python virtual environment automatically.

Edit the root `.env` ports or override `SUBSTRATA_API_PORT` /
`SUBSTRATA_UI_PORT` in your shell. Existing configuration is preserved by setup.
Stop running servers before reinstalling frontend dependencies with setup.

The Makefile forwards these tasks when GNU Make is available. Deterministic
scenario seeding and evaluation scripts remain planned. **[Design]**
