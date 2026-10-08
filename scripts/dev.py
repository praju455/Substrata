"""Cross-platform scaffold commands; run from any working directory."""

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
HOST = "127.0.0.1"


@dataclass(frozen=True)
class Ports:
    """Validated loopback ports for the local API and UI."""

    api: int
    ui: int


def read_ports(env_file: Path = ROOT / ".env") -> Ports:
    """Read local settings without modifying the caller's environment."""
    from dotenv import dotenv_values

    values = {**dotenv_values(env_file), **os.environ}
    ports = []
    for name, default in (("SUBSTRATA_API_PORT", "8000"), ("SUBSTRATA_UI_PORT", "3000")):
        try:
            port = int(values.get(name, default) or "")
        except ValueError as exc:
            raise ValueError(f"{name} must be an integer between 1 and 65535.") from exc
        if not 1 <= port <= 65535:
            raise ValueError(f"{name} must be between 1 and 65535.")
        ports.append(port)
    if ports[0] == ports[1]:
        raise ValueError("API and UI ports must be different.")
    return Ports(api=ports[0], ui=ports[1])


def npm_command(*arguments: str) -> list[str]:
    """Find npm without relying on PowerShell execution policy or shell strings."""
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if npm is None:
        raise RuntimeError("npm is missing. Install Node.js 24.x and retry.")
    return [npm, "--prefix", str(ROOT / "frontend"), *arguments]


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    """Run a finite task and propagate its failure."""
    subprocess.run(command, cwd=ROOT, check=True, env=env)


def local_environment() -> dict[str, str]:
    """Use the same root configuration for development and static builds."""
    from dotenv import dotenv_values

    environment = {
        **{k: v for k, v in dotenv_values(ROOT / ".env").items() if v is not None},
        **os.environ,
        "NEXT_TELEMETRY_DISABLED": "1",
    }
    environment.setdefault("NEXT_PUBLIC_API_URL", f"http://{HOST}:{read_ports(ROOT / '.env').api}")
    return environment


def setup() -> None:
    """Install locked dependencies and preserve any existing local configuration."""
    # Bootstrap runs before Python project metadata can enforce the minimum version.
    if sys.version_info < (3, 12):  # noqa: UP036
        raise RuntimeError("Setup requires Python 3.12 or newer.")
    npm = npm_command("ci")
    if not VENV_PYTHON.exists():
        run([sys.executable, "-m", "venv", str(ROOT / ".venv")])
    run(
        [
            str(VENV_PYTHON),
            "-m",
            "pip",
            "install",
            "-e",
            ".[dev]",
            "-c",
            "requirements-dev.lock",
        ]
    )
    run(npm)
    env_file = ROOT / ".env"
    if not env_file.exists():
        shutil.copyfile(ROOT / ".env.example", env_file)
    print("Setup complete. Local configuration is in .env.", flush=True)


def require_free_port(port: int) -> None:
    """Fail before launching servers if another process owns a requested port."""
    with socket.socket() as probe:
        try:
            probe.bind((HOST, port))
        except OSError as exc:
            raise RuntimeError(
                f"Port {port} is unavailable. Stop its server or change the port in .env."
            ) from exc


def stop_process(process: subprocess.Popen, timeout: int = 5) -> None:
    """Stop an owned child tree; Windows children share the console for Ctrl+C."""
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except OSError:
        process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def in_virtualenv(task: str) -> int:
    """Run with project dependencies and clean up the owned tree on interruption."""
    child = subprocess.Popen(
        [str(VENV_PYTHON), str(Path(__file__).resolve()), task],
        cwd=ROOT,
        start_new_session=os.name != "nt",
    )
    try:
        return child.wait()
    except KeyboardInterrupt:
        stop_process(child, timeout=15)
        return 0 if task in {"api", "ui", "demo"} else 130


def serve(task: str) -> int:
    """Supervise the requested servers and clean up on interruption or failure."""
    ports = read_ports()
    commands = []
    if task in {"api", "demo"}:
        commands.append(
            (
                "API",
                ports.api,
                [
                    str(VENV_PYTHON),
                    "-m",
                    "uvicorn",
                    "substrata.app:app",
                    "--host",
                    HOST,
                    "--port",
                    str(ports.api),
                ],
            )
        )
    if task in {"ui", "demo"}:
        node = shutil.which("node")
        next_cli = ROOT / "frontend/node_modules/next/dist/bin/next"
        if node is None or not next_cli.exists():
            raise RuntimeError("Frontend dependencies are missing. Run setup first.")
        commands.append(
            (
                "UI",
                ports.ui,
                [
                    node,
                    str(next_cli),
                    "dev",
                    "--hostname",
                    HOST,
                    "--port",
                    str(ports.ui),
                ],
            )
        )
    for _, port, _ in commands:
        require_free_port(port)
    children = []
    environment = local_environment()
    try:
        if task == "demo":
            print("Starting the synthetic demo. All actions are simulated only.", flush=True)
        for name, port, command in commands:
            print(f"Starting {name}: http://{HOST}:{port}", flush=True)
            children.append(
                subprocess.Popen(
                    command,
                    cwd=ROOT / "frontend" if name == "UI" else ROOT,
                    env=environment,
                    start_new_session=os.name != "nt",
                )
            )
        while True:
            for child in children:
                code = child.poll()
                if code is not None:
                    return code or (1 if task == "demo" else 0)
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nStopping local servers...", flush=True)
        return 0
    finally:
        for child in reversed(children):
            stop_process(child)


def main() -> int:
    """Dispatch a task, bootstrapping first or using the local virtual environment."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "task",
        choices=(
            "setup",
            "migrate",
            "seed",
            "evaluate",
            "test",
            "lint",
            "api",
            "ui",
            "demo",
            "build",
        ),
    )
    task = parser.parse_args().task
    signal.signal(
        signal.SIGBREAK if os.name == "nt" else signal.SIGTERM, signal.default_int_handler
    )
    try:
        if task == "setup":
            setup()
            return 0
        if not VENV_PYTHON.exists():
            raise RuntimeError(
                "Local environment is missing. Run python scripts/dev.py setup first."
            )
        if Path(sys.executable).resolve() != VENV_PYTHON.resolve():
            return in_virtualenv(task)
        if task in {"api", "ui", "demo"}:
            return serve(task)
        if task == "migrate":
            from substrata.database import build_engine, upgrade_database

            path = ROOT / "data" / "substrata.sqlite3"
            engine = build_engine(path)
            try:
                upgrade_database(engine)
            finally:
                engine.dispose()
            print(
                f"Database migrated: {path}. Run seed to initialize/reset the synthetic scenario."
            )
        elif task == "seed":
            run([str(VENV_PYTHON), "-m", "scripts.seed"])
        elif task == "evaluate":
            run([str(VENV_PYTHON), "-m", "scripts.evaluate"])
        elif task == "test":
            run([str(VENV_PYTHON), "-m", "pytest", "-q"])
            run(npm_command("run", "typecheck"))
        elif task == "lint":
            run([str(VENV_PYTHON), "-m", "ruff", "check", "."])
            run([str(VENV_PYTHON), "-m", "ruff", "format", "--check", "."])
            run(npm_command("run", "lint"))
        elif task == "build":
            run(npm_command("run", "build"), env=local_environment())
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        return exc.returncode or 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
