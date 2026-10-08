# Tests

`test_api.py` verifies process health, the synthetic-data label and the published
OpenAPI health response contract using an independent FastAPI app instance.

`test_dev_config.py` verifies launcher defaults, environment precedence,
configuration preservation and rejection of invalid/conflicting ports.

Run `python scripts/dev.py test` and `python scripts/dev.py lint` from the root.

Graph calculations, inference, approval rules, audit integrity and the complete
synthetic replay will receive tests when those features are implemented. **[Design]**
