"""Shared isolated tenant-platform database fixture."""

import pytest

from substrata.platform.database import build_engine, migrate
from substrata.platform.store import PlatformStore


@pytest.fixture
def platform(tmp_path):
    engine = build_engine(f"sqlite:///{(tmp_path / 'platform.sqlite3').as_posix()}")
    migrate(engine)
    migrate(engine)
    store = PlatformStore(engine)
    for tenant in ("alpha", "beta"):
        store.provision(tenant, tenant.title(), "test-admin")
    yield store
    engine.dispose()
