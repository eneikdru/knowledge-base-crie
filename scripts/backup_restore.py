"""
Automated backup and disaster restoration utility for SQLite databases.

Provides:
- Consistent atomic snapshot generation from active SQLite database.
- SHA-256 integrity checksum verification.
- Authenticated encryption (PBKDF2-HMAC-SHA256 keystream + HMAC integrity tag).
- Safe restore routine with integrity validation (PRAGMA integrity_check).
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import sys
import tempfile
from typing import Dict, Any, Tuple


MAGIC_HEADER = "CRIE_ENCRYPTED_SNAPSHOT_V1"
DEFAULT_PBKDF2_ITERATIONS = 100_000


def _derive_keys(passphrase: str, salt: bytes) -> Tuple[bytes, bytes]:
    """Derive 32-byte encryption key and 32-byte MAC key using PBKDF2-HMAC-SHA256."""
    master = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, DEFAULT_PBKDF2_ITERATIONS, dklen=64)
    enc_key = master[:32]
    mac_key = master[32:64]
    return enc_key, mac_key


def _keystream_xor(data: bytes, enc_key: bytes, nonce: bytes) -> bytes:
    """XOR stream cipher based on HMAC-SHA256 block expansion."""
    out = bytearray(len(data))
    block_idx = 0
    block = b""
    block_pos = 32
    for i in range(len(data)):
        if block_pos >= 32:
            block = hmac.new(enc_key, nonce + block_idx.to_bytes(4, "big"), hashlib.sha256).digest()
            block_idx += 1
            block_pos = 0
        out[i] = data[i] ^ block[block_pos]
        block_pos += 1
    return bytes(out)


def backup_database(src_db_path: str, snapshot_out_path: str, passphrase: str) -> Dict[str, Any]:
    """
    Create an encrypted, checksummed snapshot from a live SQLite database.
    Uses SQLite online backup API to ensure a transactionally consistent snapshot.
    """
    if not os.path.exists(src_db_path):
        raise FileNotFoundError(f"Source database not found: {src_db_path}")

    # 1. Take a consistent snapshot via SQLite backup API into a temporary file
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as tmp_file:
        tmp_backup_path = tmp_file.name

    try:
        src_conn = sqlite3.connect(src_db_path)
        dst_conn = sqlite3.connect(tmp_backup_path)
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()

        with open(tmp_backup_path, "rb") as f:
            raw_bytes = f.read()
    finally:
        if os.path.exists(tmp_backup_path):
            os.remove(tmp_backup_path)

    # 2. Compute plain checksum
    checksum = hashlib.sha256(raw_bytes).hexdigest()
    payload_size = len(raw_bytes)

    # 3. Encrypt payload
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)
    enc_key, mac_key = _derive_keys(passphrase, salt)
    ciphertext = _keystream_xor(raw_bytes, enc_key, nonce)

    # 4. Generate authentication tag over (magic + salt + nonce + checksum + ciphertext)
    mac = hmac.new(mac_key, MAGIC_HEADER.encode("utf-8") + salt + nonce + checksum.encode("utf-8") + ciphertext, hashlib.sha256)
    tag = mac.hexdigest()

    snapshot_data = {
        "magic": MAGIC_HEADER,
        "iterations": DEFAULT_PBKDF2_ITERATIONS,
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "checksum_sha256": checksum,
        "payload_size": payload_size,
        "tag": tag,
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }

    os.makedirs(os.path.dirname(os.path.abspath(snapshot_out_path)), exist_ok=True)
    with open(snapshot_out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot_data, f, indent=2)

    return {
        "status": "SUCCESS",
        "snapshot_path": snapshot_out_path,
        "checksum_sha256": checksum,
        "payload_size": payload_size,
    }


def restore_database(snapshot_path: str, target_db_path: str, passphrase: str) -> Dict[str, Any]:
    """
    Restore a SQLite database from an encrypted snapshot, verifying checksum and integrity.
    """
    if not os.path.exists(snapshot_path):
        raise FileNotFoundError(f"Snapshot file not found: {snapshot_path}")

    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshot_data = json.load(f)

    if snapshot_data.get("magic") != MAGIC_HEADER:
        raise ValueError("Invalid or unsupported snapshot format")

    salt = base64.b64decode(snapshot_data["salt"])
    nonce = base64.b64decode(snapshot_data["nonce"])
    expected_checksum = snapshot_data["checksum_sha256"]
    expected_tag = snapshot_data["tag"]
    ciphertext = base64.b64decode(snapshot_data["ciphertext"])

    enc_key, mac_key = _derive_keys(passphrase, salt)

    # Verify MAC
    mac = hmac.new(mac_key, MAGIC_HEADER.encode("utf-8") + salt + nonce + expected_checksum.encode("utf-8") + ciphertext, hashlib.sha256)
    if not hmac.compare_digest(mac.hexdigest(), expected_tag):
        raise ValueError("Snapshot authentication failed: invalid passphrase or corrupted payload")

    # Decrypt
    raw_bytes = _keystream_xor(ciphertext, enc_key, nonce)

    # Verify plain checksum
    computed_checksum = hashlib.sha256(raw_bytes).hexdigest()
    if computed_checksum != expected_checksum:
        raise ValueError(f"Checksum mismatch: expected {expected_checksum}, got {computed_checksum}")

    expected_payload_size = snapshot_data.get("payload_size")
    if expected_payload_size is not None and expected_payload_size != len(raw_bytes):
        raise ValueError(f"Payload size mismatch: expected {expected_payload_size}, got {len(raw_bytes)}")

    # Atomic write to target destination
    os.makedirs(os.path.dirname(os.path.abspath(target_db_path)), exist_ok=True)
    temp_dest = target_db_path + ".restore_tmp"
    with open(temp_dest, "wb") as f:
        f.write(raw_bytes)

    # Run SQLite integrity check
    conn = sqlite3.connect(temp_dest)
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check;")
    integrity_rows = [row[0] for row in cursor.fetchall()]
    conn.close()

    if integrity_rows != ["ok"]:
        os.remove(temp_dest)
        raise RuntimeError(f"Restored SQLite database failed integrity check: {integrity_rows}")

    os.replace(temp_dest, target_db_path)

    return {
        "status": "RESTORED",
        "target_db_path": target_db_path,
        "checksum_sha256": computed_checksum,
        "integrity": "ok",
    }


def main():
    parser = argparse.ArgumentParser(description="SQLite Automated Backup and Restoration")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_cmd = subparsers.add_parser("backup", help="Generate encrypted snapshot from SQLite DB")
    backup_cmd.add_argument("--db", required=True, help="Path to source SQLite database")
    backup_cmd.add_argument("--out", required=True, help="Destination path for snapshot file")
    backup_cmd.add_argument("--passphrase", required=True, help="Passphrase for encryption")

    restore_cmd = subparsers.add_parser("restore", help="Restore SQLite DB from encrypted snapshot")
    restore_cmd.add_argument("--snapshot", required=True, help="Path to snapshot file")
    restore_cmd.add_argument("--out-db", required=True, help="Destination path for restored SQLite database")
    restore_cmd.add_argument("--passphrase", required=True, help="Passphrase for decryption")

    args = parser.parse_args()

    if args.command == "backup":
        res = backup_database(args.db, args.out, args.passphrase)
        print(json.dumps(res, indent=2))
    elif args.command == "restore":
        res = restore_database(args.snapshot, args.out_db, args.passphrase)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
