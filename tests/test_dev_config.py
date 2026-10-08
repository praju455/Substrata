"""Local launcher settings must be predictable and reject unusable ports."""

from pathlib import Path

import pytest

from scripts.dev import Ports, read_ports


@pytest.fixture(autouse=True)
def isolated_ports(monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not let the developer's shell configuration affect these cases."""
    monkeypatch.delenv("SUBSTRATA_API_PORT", raising=False)
    monkeypatch.delenv("SUBSTRATA_UI_PORT", raising=False)


def test_missing_env_uses_local_defaults(tmp_path: Path) -> None:
    assert read_ports(tmp_path / ".env") == Ports(api=8000, ui=3000)


def test_shell_overrides_env_without_mutating_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    content = "SUBSTRATA_API_PORT=8100\nSUBSTRATA_UI_PORT=3100\n"
    env_file.write_text(content, encoding="utf-8")
    monkeypatch.setenv("SUBSTRATA_API_PORT", "8200")
    assert read_ports(env_file) == Ports(api=8200, ui=3100)
    assert env_file.read_text(encoding="utf-8") == content


@pytest.mark.parametrize("value", ["0", "65536", "not-a-number", ""])
def test_invalid_port_is_rejected(value: str, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"SUBSTRATA_API_PORT={value}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SUBSTRATA_API_PORT"):
        read_ports(env_file)


def test_api_and_ui_cannot_share_a_port(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("SUBSTRATA_API_PORT=3000\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must be different"):
        read_ports(env_file)
