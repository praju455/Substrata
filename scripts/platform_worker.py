"""Run durable platform jobs for one explicitly selected tenant."""

import argparse
import json
import logging
import os
import time

from pydantic import TypeAdapter

from substrata.observability import configure_logging, configured_tracing
from substrata.platform.auth import Principal
from substrata.platform.database import build_engine
from substrata.platform.domain import Identifier
from substrata.platform.jobs import run_next
from substrata.platform.store import PlatformStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", required=True, type=TypeAdapter(Identifier).validate_python)
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if not 0.1 <= args.poll_seconds <= 60:
        parser.error("--poll-seconds must be between 0.1 and 60.")
    database_url = os.environ.get("SUBSTRATA_PLATFORM_DATABASE_URL")
    if not database_url:
        parser.error("SUBSTRATA_PLATFORM_DATABASE_URL must be configured.")

    engine = build_engine(database_url)
    store = PlatformStore(engine)
    tracing = configured_tracing("substrata-worker")
    configure_logging()
    worker = Principal(subject="platform-worker", tenant_id=args.tenant, roles={"analyst"})
    try:
        with tracing.activate():
            while True:
                result = run_next(store, worker)
                if result is not None:
                    if result.get("kind") == "notification_delivery":
                        logging.getLogger("substrata.worker").info(
                            json.dumps(
                                {
                                    "event": "worker.notification_delivery",
                                    "attempted": result.get("attempted", 0),
                                    "delivered": result.get("delivered", 0),
                                },
                                separators=(",", ":"),
                            )
                        )
                elif args.once:
                    return 0
                else:
                    time.sleep(args.poll_seconds)
    except KeyboardInterrupt:
        return 0
    finally:
        try:
            tracing.shutdown()
        finally:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
