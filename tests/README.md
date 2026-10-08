# Tests

`test_api.py` verifies process health, the synthetic-data label and the published
OpenAPI health response contract using an independent FastAPI app instance.

`test_dev_config.py` verifies launcher defaults, environment precedence,
configuration preservation and rejection of invalid/conflicting ports.

`test_database.py` exercises real temporary SQLite files: per-connection WAL,
foreign keys, busy timeout, transaction commit/rollback, a reader during a
pending write, and repeatable migrations that preserve test records. Test-only
probe tables do not become part of the application schema.

Run `python scripts/dev.py test` and `python scripts/dev.py lint` from the root.

Graph calculations, inference, approval rules, audit integrity and the complete
synthetic replay will receive tests when those features are implemented. **[Design]**
