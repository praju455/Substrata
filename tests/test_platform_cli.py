"""Development key setup must be exclusive and restrictive."""

import os
import stat
import sys

import pytest

from substrata.platform.cli import main


def test_dev_key_is_exclusive_and_owner_only(tmp_path, monkeypatch, capsys):
    key = tmp_path / "nested" / "auth.secret"
    monkeypatch.setenv("SUBSTRATA_ENV", "development")
    monkeypatch.setenv("SUBSTRATA_AUTH_KEY_FILE", str(key))
    monkeypatch.setattr(sys, "argv", ["platform.cli", "dev-key"])

    assert main() == 0
    original = key.read_text()
    assert len(original) >= 32
    assert "Development key created" in capsys.readouterr().out
    if os.name != "nt":
        assert stat.S_IMODE(key.stat().st_mode) == 0o600

    with pytest.raises(FileExistsError):
        main()
    assert key.read_text() == original
