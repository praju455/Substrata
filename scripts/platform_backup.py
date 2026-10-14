"""Create/inspect authenticated backups or restore into a brand-new PostgreSQL database."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def database_url(variable):
    from sqlalchemy.engine import make_url

    value = os.environ.get(variable)
    if not value:
        raise ValueError(f"Configure {variable} through the backend environment.")
    url = make_url(value)
    if url.drivername != "postgresql+psycopg" or not url.database:
        raise ValueError("Configure a PostgreSQL/psycopg database URL.")
    if (
        os.environ.get("SUBSTRATA_ENV", "development") != "development"
        and url.query.get("sslmode") != "verify-full"
    ):
        raise ValueError("Production backup/recovery connections require sslmode=verify-full.")
    return url


def executable(name, configured):
    path = shutil.which(configured or name)
    if path is None:
        raise ValueError(f"Install {name} or configure its executable path.")
    return path


def main():
    if VENV_PYTHON.is_file() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
        return subprocess.run(
            [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]], cwd=ROOT
        ).returncode
    from substrata.platform.backup_ops import backup_database, client_environment, restore_database
    from substrata.platform.backups import authenticated_backup, create_key
    from substrata.platform.database import build_engine

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["key", "create", "inspect", "restore"])
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--file", type=Path, help="Encrypted artifact; create refuses overwrite.")
    parser.add_argument(
        "--new-database", help="Required for restore; existing databases are refused."
    )
    parser.add_argument("--pg-dump", help="Trusted PostgreSQL pg_dump executable path.")
    parser.add_argument("--pg-restore", help="Trusted PostgreSQL pg_restore executable path.")
    parser.add_argument(
        "--synthetic", action="store_true", help="Label a known synthetic source explicitly."
    )
    args = parser.parse_args()
    engine = None
    try:
        if args.command == "key":
            create_key(args.key_file)
            print("A separate backup key was created without overwriting an existing file.")
            return 0
        if args.file is None:
            parser.error("--file is required for create, inspect and restore.")
        key = args.key_file.read_bytes()
        if args.command == "inspect":
            with authenticated_backup(args.file, key) as (result, _):
                manifest = result["manifest"]
                summary = {
                    "authenticated": True,
                    "archive_bytes": result["archive_bytes"],
                    "created_at": manifest.get("created_at"),
                    "synthetic": manifest.get("synthetic"),
                    "tenant_count": len(manifest.get("tenant_heads", {})),
                }
        elif args.command == "create":
            url = database_url("SUBSTRATA_BACKUP_DATABASE_URL")
            engine = build_engine(url.render_as_string(hide_password=False))
            tool = executable("pg_dump", args.pg_dump)
            result = backup_database(
                engine,
                args.file,
                key,
                lambda snapshot: [
                    tool,
                    "--format=custom",
                    "--no-owner",
                    "--no-privileges",
                    f"--snapshot={snapshot}",
                ],
                environment=client_environment(url),
                synthetic=args.synthetic,
            )
            summary = {key: value for key, value in result.items() if key != "manifest"}
            summary["synthetic"] = args.synthetic
        else:
            if not args.new_database:
                parser.error("--new-database is required for restore.")
            url = database_url("SUBSTRATA_RESTORE_ADMIN_URL")
            engine = build_engine(url.render_as_string(hide_password=False))
            tool = executable("pg_restore", args.pg_restore)
            result = restore_database(
                engine,
                args.file,
                key,
                args.new_database,
                lambda name: [tool, "--dbname", name],
                environment=client_environment(url),
            )
            summary = {
                "authenticated": True,
                "new_database": result["database"],
                "archive_bytes": result["archive_bytes"],
                "restore": "complete",
            }
        print(json.dumps(summary, separators=(",", ":")))
        return 0
    except Exception as error:
        # Native tools, libpq exceptions and manifests can contain private names
        # or connection secrets; no raw stderr/URL/manifest is dumped to logs.
        print(
            f"Backup operation failed ({type(error).__name__}); "
            "check configuration, key and artifact.",
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
