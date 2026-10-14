"""Owned disposable PostgreSQL instances for synthetic recovery checks."""

import os
import re
import secrets
import subprocess
import time
from urllib.parse import quote
from uuid import uuid4

if __package__:
    from .verify_postgres import IMAGE, ROOT, find_docker
else:
    from verify_postgres import IMAGE, ROOT, find_docker


class DisposablePostgres:
    def __init__(self, *, executable=None):
        self.executable = executable or find_docker()
        self.password = secrets.token_hex(24)
        self.environment = {
            **os.environ,
            "PATH": str(self.executable.parent) + os.pathsep + os.environ.get("PATH", ""),
            "POSTGRES_PASSWORD": self.password,
        }
        self.name = f"substrata-recovery-{uuid4().hex}"
        self.id = None
        self.port = None

    def docker(self, *args, check=True, timeout=30):
        return subprocess.run(
            [str(self.executable), *args],
            cwd=ROOT,
            env=self.environment,
            capture_output=True,
            text=True,
            check=check,
            timeout=timeout,
        )

    def command(self, *args):
        if self.id is None:
            raise RuntimeError("No owned PostgreSQL container is active.")
        return (
            [str(self.executable), "exec", *args[:1], self.id, *args[1:]]
            if args and args[0] == "-i"
            else [str(self.executable), "exec", self.id, *args]
        )

    def url(self, *, database="substrata_test", user="postgres", password=None):
        if self.port is None:
            raise RuntimeError("The owned test database is not ready.")
        return (
            f"postgresql+psycopg://{quote(user, safe='')}:"
            f"{quote(password or self.password, safe='')}"
            f"@127.0.0.1:{self.port}/{quote(database, safe='')}"
        )

    def __enter__(self):
        try:
            self.docker("info", "--format", "{{.ServerVersion}}", timeout=15)
            self.id = self.docker(
                "create",
                "--rm",
                "--name",
                self.name,
                "--label",
                "substrata.purpose=recovery-drill",
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
            ).stdout.strip()
            if not re.fullmatch(r"[a-f0-9]{64}", self.id):
                self.id = None
                raise RuntimeError("Docker did not return a valid owned container ID.")
            self.docker("start", self.id)
            deadline = time.monotonic() + 90
            while self.docker(
                "exec",
                self.id,
                "pg_isready",
                "-h",
                "127.0.0.1",
                "-U",
                "postgres",
                "-d",
                "substrata_test",
                check=False,
                timeout=10,
            ).returncode:
                if time.monotonic() >= deadline:
                    raise RuntimeError("The recovery database did not become ready.")
                time.sleep(0.5)
            binding = self.docker("port", self.id, "5432/tcp").stdout.strip()
            match = re.fullmatch(r"127\.0\.0\.1:(\d+)", binding)
            if not match:
                raise RuntimeError("The owned test database must publish a loopback-only port.")
            self.port = int(match[1])
            return self
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.id:
            # Only the exact ID returned by this object's CREATE is eligible.
            # No Compose project, named volume or host directory is touched.
            removed = self.docker("rm", "--force", "--volumes", self.id, check=False)
            if removed.returncode and "No such container" not in removed.stderr:
                raise RuntimeError("Could not remove the owned recovery container.")
            self.id = None

    def __exit__(self, *args):
        self.close()
