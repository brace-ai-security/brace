"""Fetch, verify, and stage the drafting model for the vLLM sidecar.

Runs as an init container. The staged directory is mounted read-only into the vLLM container.
"""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import boto3
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key

STAGE = Path("/models/stage")


class VerificationError(RuntimeError):
    pass


def _s3_get(uri: str) -> bytes:
    bucket, key = uri.removeprefix("s3://").split("/", 1)
    return boto3.client("s3").get_object(Bucket=bucket, Key=key)["Body"].read()


def _verify_manifest_signature(manifest_bytes: bytes, signature_b64: bytes, pubkey_pem: bytes) -> None:
    key = load_pem_public_key(pubkey_pem)
    if not isinstance(key, Ed25519PublicKey):
        raise VerificationError("unexpected key type")
    try:
        key.verify(base64.b64decode(signature_b64), manifest_bytes)
    except Exception as exc:
        raise VerificationError("manifest signature invalid") from exc


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def stage(manifest_uri: str) -> Path:
    manifest_bytes = _s3_get(manifest_uri)
    manifest = json.loads(manifest_bytes)
    signature = _s3_get(manifest_uri + ".sig")
    pubkey = _s3_get(manifest["signing_key"])
    _verify_manifest_signature(manifest_bytes, signature, pubkey)

    target = STAGE / manifest["version"]
    subprocess.run(
        ["aws", "s3", "sync", manifest["storage"], str(target), "--only-show-errors"],
        check=True,
    )
    for entry in manifest["files"]:
        expected = entry.get("sha256")
        if not expected:
            continue
        actual = _sha256(target / entry["path"])
        if actual != expected:
            raise VerificationError(f"digest mismatch for {entry['path']}")
    (target / "VERIFIED").write_text(manifest["version"])
    return target


if __name__ == "__main__":
    print(stage(sys.argv[1]))
