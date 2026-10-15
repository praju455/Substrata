"""Versioned AES-256-GCM backup envelopes; authenticate before restoring any data."""

import hashlib
import json
import os
import secrets
import shutil
import struct
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryFile

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b"SUBPG01\0"
HEADER_SIZE = len(MAGIC) + 12
TAG_SIZE = 16
CHUNK_SIZE = 1024 * 1024
MAX_MANIFEST = 1024 * 1024
DUMP_MAGIC = b"PGDMP"


def _key(value):
    if not isinstance(value, bytes) or len(value) != 32:
        raise ValueError("Backup encryption requires a separate 32-byte key.")
    return value


def create_key(path: Path):
    """Never overwrite a key; the operator keeps it outside backup artifact storage."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(secrets.token_bytes(32))


def _exact(stream, count):
    blocks = bytearray()
    while len(blocks) < count:
        incoming = stream.read(count - len(blocks))
        if not incoming:
            raise ValueError("Backup is truncated or uses an unsupported format.")
        blocks.extend(incoming)
    return bytes(blocks)


def encrypt_backup(source, path: Path, key: bytes, manifest: dict):
    """Encrypt a custom pg_dump stream without persisting its plaintext on disk."""
    key = _key(key)
    if not isinstance(manifest, dict):
        raise ValueError("Backup manifest must be a JSON object.")
    metadata = json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if len(metadata) > MAX_MANIFEST:
        raise ValueError("Backup manifest exceeds 1 MB.")
    prefix = _exact(source, len(DUMP_MAGIC))
    if prefix != DUMP_MAGIC:
        raise ValueError("Backup source must be a PostgreSQL custom-format archive.")
    header = MAGIC + secrets.token_bytes(12)
    encryptor = Cipher(algorithms.AES(key), modes.GCM(header[len(MAGIC) :])).encryptor()
    encryptor.authenticate_additional_data(header)
    destination = Path(path).absolute()
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    size = len(prefix)
    digest = hashlib.sha256()
    try:
        with os.fdopen(descriptor, "wb") as target:

            def write(block):
                target.write(block)
                digest.update(block)

            write(header)
            write(encryptor.update(struct.pack(">I", len(metadata)) + metadata + prefix))
            while incoming := source.read(CHUNK_SIZE):
                size += len(incoming)
                write(encryptor.update(incoming))
            write(encryptor.finalize())
            write(encryptor.tag)
            target.flush()
            os.fsync(target.fileno())
        return {
            "archive_bytes": size,
            "encrypted_sha256": digest.hexdigest(),
            "encrypted_bytes": destination.stat().st_size,
        }
    except BaseException:
        # This exact, newly created artifact is owned by this call. Existing
        # paths failed O_EXCL before entering this block and are never removed.
        destination.unlink(missing_ok=True)
        raise


def _plaintext(stream, key):
    stream.seek(0, 2)
    length = stream.tell()
    if length < HEADER_SIZE + TAG_SIZE + 4 + 2 + len(DUMP_MAGIC):
        raise ValueError("Backup is truncated or uses an unsupported format.")
    stream.seek(0)
    header = _exact(stream, HEADER_SIZE)
    if header[: len(MAGIC)] != MAGIC:
        raise ValueError("Backup is truncated or uses an unsupported format.")
    stream.seek(length - TAG_SIZE)
    tag = _exact(stream, TAG_SIZE)
    decryptor = Cipher(algorithms.AES(_key(key)), modes.GCM(header[len(MAGIC) :], tag)).decryptor()
    decryptor.authenticate_additional_data(header)
    stream.seek(HEADER_SIZE)
    remaining = length - HEADER_SIZE - TAG_SIZE
    try:
        while remaining:
            block = _exact(stream, min(CHUNK_SIZE, remaining))
            remaining -= len(block)
            yield decryptor.update(block)
        final = decryptor.finalize()
        if final:
            yield final
    except InvalidTag:
        raise ValueError("Backup authentication failed; no restore input may be used.") from None


def _consume(stream, key, destination=None):
    metadata_length = None
    metadata = None
    buffered = bytearray()
    dump_prefix = bytearray()
    count = 0
    digest = hashlib.sha256()
    for block in _plaintext(stream, key):
        if metadata is None:
            buffered.extend(block)
            if metadata_length is None and len(buffered) >= 4:
                metadata_length = struct.unpack(">I", buffered[:4])[0]
                if not 2 <= metadata_length <= MAX_MANIFEST:
                    raise ValueError("Backup manifest length is invalid.")
            if metadata_length is None or len(buffered) < metadata_length + 4:
                continue
            metadata = bytes(buffered[4 : 4 + metadata_length])
            block = bytes(buffered[4 + metadata_length :])
            buffered.clear()
        if len(dump_prefix) < len(DUMP_MAGIC):
            dump_prefix.extend(block[: len(DUMP_MAGIC) - len(dump_prefix)])
        if destination is not None:
            destination.write(block)
        count += len(block)
        digest.update(block)
    if metadata is None or bytes(dump_prefix) != DUMP_MAGIC:
        raise ValueError("Backup does not contain a complete custom-format archive prefix.")
    try:
        manifest = json.loads(metadata)
        if not isinstance(manifest, dict):
            raise ValueError
    except (ValueError, UnicodeError):
        raise ValueError("Authenticated backup manifest is invalid.") from None
    return {"manifest": manifest, "archive_bytes": count, "archive_sha256": digest.hexdigest()}


@contextmanager
def authenticated_backup(path: Path, key: bytes):
    """Stage ciphertext, validate its entire tag, then expose a verified restore stream.

    Only ciphertext spills to temporary storage. The private staged copy prevents
    changes to the original path between verification and streaming to pg_restore.
    """
    _key(key)
    with TemporaryFile("w+b") as staged:
        with Path(path).open("rb") as original:
            shutil.copyfileobj(original, staged, length=CHUNK_SIZE)
        verified = _consume(staged, key)

        def restore_to(destination):
            return _consume(staged, key, destination)

        yield verified, restore_to
