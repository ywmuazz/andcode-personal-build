#!/usr/bin/env python3
"""Fail before exposing signing secrets if a reused build differs from the pin."""
import hashlib
import json
import os
from pathlib import Path

incoming = Path("incoming")
record = json.loads((incoming / "build-record.json").read_text())
patch_dir = Path(__file__).resolve().parent.parent / "patches"
expected = {
    "source_repository": "https://github.com/yuga-hashimoto/and-code",
    "source_commit": os.environ["SOURCE_COMMIT"],
    "source_patches": [
        {"name": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in sorted(patch_dir.glob("*.patch"))
    ],
    "termux_commit": os.environ["TERMUX_PACKAGES_COMMIT"],
    "variant": "fdroidRelease",
    "gradle": "8.9",
    "unsigned_apk_sha256": hashlib.sha256((incoming / "andcode-unsigned.apk").read_bytes()).hexdigest(),
}
for key, value in expected.items():
    if record.get(key) != value:
        raise ValueError(f"Build record does not match expected {key}")
print("Unsigned build provenance fields and APK checksum match the pinned configuration.")
