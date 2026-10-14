"""Verify PostgreSQL workflows in an owned, disposable Docker database."""

import argparse
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "pgvector/pgvector:pg17"


def find_docker(explicit: Path | None = None) -> Path:
    if explicit is not None:
        if not explicit.is_file():
            raise RuntimeError("The supplied Docker executable does not exist.")
        return explicit.resolve()
    executable = shutil.which("docker")
    if executable:
        return Path(executable)
    if os.name == "nt":
        locations = (
            ("LOCALAPPDATA", "Programs/DockerDesktop/resources/bin/docker.exe"),
            ("ProgramFiles", "Docker/Docker/resources/bin/docker.exe"),
        )
        for variable, relative in locations:
            base = os.environ.get(variable)
            candidate = Path(base) / relative if base else None
            if candidate is not None and candidate.is_file():
                return candidate.resolve()
    raise RuntimeError("Docker CLI is unavailable. Start Docker Desktop or supply --docker PATH.")


def verify(*, executable: Path, full_suite: bool) -> int:
    # Docker Desktop's credential helper lives beside docker.exe on Windows.
    # This affects only child processes, not the user's persistent PATH/config.
    docker_environment = {
        **os.environ,
        "PATH": str(executable.parent) + os.pathsep + os.environ.get("PATH", ""),
        "POSTGRES_PASSWORD": secrets.token_hex(24),
    }

    def docker(*arguments, timeout=30, check=True):
        return subprocess.run(
            [str(executable), *arguments],
            cwd=ROOT,
            env=docker_environment,
            capture_output=True,
            text=True,
            check=check,
            timeout=timeout,
        )

    venv_python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python = str(venv_python) if venv_python.is_file() else sys.executable
    dependencies = subprocess.run(
        [python, "-c", "import pytest, psycopg, substrata.platform"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if dependencies.returncode:
        raise RuntimeError(
            'Install project test dependencies with pip install -e ".[dev,platform]".'
        )
    docker("info", "--format", "{{.ServerVersion}}", timeout=15)
    name = f"substrata-pg-test-{uuid4().hex}"
    container_id = None
    try:
        print("Starting an isolated PostgreSQL 17/pgvector test container...", flush=True)
        started = docker(
            "run",
            "--detach",
            "--rm",
            "--name",
            name,
            "--label",
            "substrata.purpose=postgres-test",
            "--publish",
            "127.0.0.1::5432",
            "--env",
            "POSTGRES_DB=substrata_test",
            "--env",
            "POSTGRES_USER=postgres",
            "--env",
            "POSTGRES_PASSWORD",
            IMAGE,
            timeout=600,
        )
        container_id = started.stdout.strip()
        if not re.fullmatch(r"[a-f0-9]{64}", container_id):
            raise RuntimeError("Docker did not return a valid owned container ID.")
        deadline = time.monotonic() + 90
        while True:
            ready = docker(
                "exec",
                container_id,
                "pg_isready",
                "-h",
                "127.0.0.1",
                "-U",
                "postgres",
                "-d",
                "substrata_test",
                check=False,
                timeout=10,
            )
            if ready.returncode == 0:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("The disposable PostgreSQL database did not become ready.")
            time.sleep(0.5)
        binding = docker("port", container_id, "5432/tcp").stdout.strip()
        match = re.fullmatch(r"127\.0\.0\.1:(\d+)", binding)
        if not match:
            raise RuntimeError("The test database must publish exactly one loopback-only port.")
        password = docker_environment["POSTGRES_PASSWORD"]
        test_environment = {
            **os.environ,
            "SUBSTRATA_TEST_POSTGRES_ADMIN_URL": (
                f"postgresql+psycopg://postgres:{password}@127.0.0.1:{match[1]}/substrata_test"
            ),
        }
        target = "tests" if full_suite else "tests/test_platform_postgres.py"
        print(
            "PostgreSQL is ready. Running synthetic workflow checks with RLS enabled.", flush=True
        )
        result = subprocess.run(
            [python, "-m", "pytest", "-q", target],
            cwd=ROOT,
            env=test_environment,
        )
        return result.returncode
    finally:
        if container_id and re.fullmatch(r"[a-f0-9]{64}", container_id):
            # Only this invocation's exact container is stopped; --rm removes its
            # anonymous test volume. No Compose project or host volume is touched.
            stopped = docker("stop", "--time", "5", container_id, check=False)
            if stopped.returncode and "No such container" not in stopped.stderr:
                raise RuntimeError(f"Could not stop the owned test container {name}.")
            print("Disposable PostgreSQL test container removed.", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--docker", type=Path, help="Path to the Docker CLI when it is not on PATH."
    )
    parser.add_argument(
        "--full-suite",
        action="store_true",
        help="Run all Python tests with PostgreSQL integration enabled.",
    )
    args = parser.parse_args()
    try:
        return verify(executable=find_docker(args.docker), full_suite=args.full_suite)
    except (
        OSError,
        RuntimeError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as error:
        print(f"PostgreSQL verification failed: {error}", file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr.strip(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
