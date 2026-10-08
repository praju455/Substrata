"""Reset the known local synthetic scenario; never connects to an external ERP."""

from scripts.dev import ROOT
from substrata.database import build_engine, upgrade_database
from substrata.seed import seed_database, write_fixtures


def main():
    fingerprint = write_fixtures(ROOT / "data")
    engine = build_engine(ROOT / "data/substrata.sqlite3")
    try:
        upgrade_database(engine)
        assert seed_database(engine, ROOT / "data") == fingerprint
    finally:
        engine.dispose()
    print(f"Synthetic scenario reset. Fixture SHA-256: {fingerprint}")


if __name__ == "__main__":
    main()
