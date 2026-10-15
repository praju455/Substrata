"""Explicit migrations and local development identities; no startup schema mutation."""

import argparse
import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "dev-key", "dev-token", "verify-audit"])
    parser.add_argument("--tenant", default="demo")
    parser.add_argument("--subject", default="local-developer")
    parser.add_argument(
        "--role", choices=["viewer", "analyst", "approver", "admin"], default="admin"
    )
    parser.add_argument("--file")
    args = parser.parse_args()
    if args.command == "migrate":
        from substrata.platform.database import build_engine, migrate

        engine = build_engine(os.environ["SUBSTRATA_PLATFORM_DATABASE_URL"])
        try:
            migrate(engine)
        finally:
            engine.dispose()
        print("Platform migrations complete.")
    elif args.command == "verify-audit":
        from substrata.audit import verify_chain

        export = json.loads(Path(args.file).read_text(encoding="utf-8"))
        result = verify_chain(export["records"], export["verification"]["head"])
        print(json.dumps(result))
        return 0 if result["valid"] else 1
    else:
        if os.environ.get("SUBSTRATA_ENV") != "development":
            raise ValueError("Development keys/tokens require SUBSTRATA_ENV=development.")
        path = Path(os.environ["SUBSTRATA_AUTH_KEY_FILE"])
        if args.command == "dev-key":
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(secrets.token_urlsafe(48))
            print("Development key created with owner-only permissions where supported.")
        else:
            import jwt

            from substrata.platform.auth import Principal

            actor = Principal(subject=args.subject, tenant_id=args.tenant, roles={args.role})
            now = datetime.now(UTC)
            print(
                jwt.encode(
                    {
                        "sub": actor.subject,
                        "tenant_id": actor.tenant_id,
                        "roles": sorted(actor.roles),
                        "iat": now,
                        "nbf": now,
                        "exp": now + timedelta(hours=1),
                        "iss": os.environ["SUBSTRATA_OIDC_ISSUER"],
                        "aud": os.environ.get("SUBSTRATA_OIDC_AUDIENCE", "substrata"),
                    },
                    path.read_text().strip(),
                    algorithm="HS256",
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
