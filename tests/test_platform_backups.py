"""Backup streaming, authentication-before-output, privacy and ownership boundaries."""

import io
import os

import pytest

from substrata.platform.backups import authenticated_backup, create_key, encrypt_backup


def test_backup_roundtrip_streams_large_archive_and_encrypts_manifest(tmp_path):
    key = os.urandom(32)
    archive = b"PGDMP" + os.urandom(3_000_000)
    manifest = {"tenant": "private-tenant", "head": "a" * 64, "synthetic": True}
    path = tmp_path / "backup.enc"
    result = encrypt_backup(io.BytesIO(archive), path, key, manifest)
    assert result["archive_bytes"] == len(archive)
    assert result["encrypted_bytes"] == path.stat().st_size
    assert b"private-tenant" not in path.read_bytes()
    with authenticated_backup(path, key) as (verified, restore_to):
        assert verified["manifest"] == manifest
        restored = io.BytesIO()
        assert restore_to(restored) == verified
        assert restored.getvalue() == archive


@pytest.mark.parametrize("offset", [8, 25, -1])
def test_tampered_nonce_ciphertext_or_tag_never_exposes_restore_callback(tmp_path, offset):
    key = os.urandom(32)
    path = tmp_path / "backup.enc"
    encrypt_backup(io.BytesIO(b"PGDMPsynthetic-data"), path, key, {"synthetic": True})
    corrupted = bytearray(path.read_bytes())
    corrupted[offset] ^= 1
    path.write_bytes(corrupted)
    exposed = False
    with pytest.raises(ValueError):
        with authenticated_backup(path, key):
            exposed = True
    assert not exposed


def test_wrong_key_truncation_and_unknown_format_are_rejected_before_restore(tmp_path):
    key = os.urandom(32)
    path = tmp_path / "backup.enc"
    encrypt_backup(io.BytesIO(b"PGDMPsynthetic-data"), path, key, {"synthetic": True})
    with pytest.raises(ValueError):
        with authenticated_backup(path, os.urandom(32)):
            pytest.fail("Unverified plaintext was exposed.")
    path.write_bytes(path.read_bytes()[:22])
    with pytest.raises(ValueError, match="truncated"):
        with authenticated_backup(path, key):
            pytest.fail("Truncated plaintext was exposed.")
    path.write_bytes(b"not-a-supported-backup-format" * 10)
    with pytest.raises(ValueError, match="unsupported"):
        with authenticated_backup(path, key):
            pytest.fail("Unknown-format plaintext was exposed.")


def test_original_file_change_after_authentication_cannot_change_restore_data(tmp_path):
    key = os.urandom(32)
    path = tmp_path / "backup.enc"
    original = b"PGDMPoriginal-authenticated-data"
    encrypt_backup(io.BytesIO(original), path, key, {})
    with authenticated_backup(path, key) as (_, restore_to):
        path.write_bytes(b"attacker-replacement")
        target = io.BytesIO()
        restore_to(target)
        assert target.getvalue() == original


def test_key_and_archive_creation_never_overwrite_existing_files(tmp_path):
    key_file = tmp_path / "key.secret"
    create_key(key_file)
    original_key = key_file.read_bytes()
    assert len(original_key) == 32
    with pytest.raises(FileExistsError):
        create_key(key_file)
    assert key_file.read_bytes() == original_key
    path = tmp_path / "backup.enc"
    path.write_bytes(b"existing-evidence")
    with pytest.raises(FileExistsError):
        encrypt_backup(io.BytesIO(b"PGDMPnew-data"), path, original_key, {})
    assert path.read_bytes() == b"existing-evidence"


def test_failed_dump_stream_removes_only_its_new_incomplete_artifact(tmp_path):
    class Broken(io.BytesIO):
        def read(self, count):
            if self.tell() >= 5:
                raise OSError("synthetic interrupted dump")
            return super().read(count)

    path = tmp_path / "incomplete.enc"
    with pytest.raises(OSError):
        encrypt_backup(Broken(b"PGDMPpartial"), path, os.urandom(32), {})
    assert not path.exists()
    with pytest.raises(ValueError, match="32-byte"):
        encrypt_backup(io.BytesIO(b"PGDMPdata"), path, b"short", {})
    assert not path.exists()


def test_identical_archives_use_distinct_nonce_and_ciphertext(tmp_path):
    key = os.urandom(32)
    first, second = tmp_path / "first.enc", tmp_path / "second.enc"
    for path in (first, second):
        encrypt_backup(io.BytesIO(b"PGDMPsame-data"), path, key, {})
    assert first.read_bytes() != second.read_bytes()
