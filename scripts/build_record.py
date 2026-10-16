#!/usr/bin/env python3
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

out = Path(sys.argv[1])
patch_dir = Path(__file__).resolve().parent.parent / "patches"
record = {
    "source_repository": "https://github.com/yuga-hashimoto/and-code",
    "source_commit": os.environ["SOURCE_COMMIT"],
    "source_patches": [
        {"name": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in sorted(patch_dir.glob("*.patch"))
    ],
    "workflow_commit": os.environ["CONTROL_COMMIT"],
    "run_url": os.environ["BUILD_RUN_URL"],
    "termux_commit": os.environ["TERMUX_PACKAGES_COMMIT"],
    "variant": "fdroidRelease",
    "gradle": "8.9",
    "java": subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT, text=True).strip(),
    "python": platform.python_version(),
    "runner_image": os.environ.get("ImageVersion", "unknown"),
    "unsigned_apk_sha256": hashlib.sha256((out / "andcode-unsigned.apk").read_bytes()).hexdigest(),
    "native_packages": (out / "native-packages.sha256").read_text().splitlines(),
    "limitations": [
        "Source traceability only; independent reproducibility was not tested.",
        "Codex is installed on the phone from the official npm registry's latest version with SHA-512 verification; it is not pinned by this APK build.",
        "PRoot is a compatibility layer; Codex uses danger-full-access.",
        "Granting all-files access broadens the agent's visible storage.",
        "Android device behavior, login, runtime installation and execution need device testing.",
        "Host apt packages, runner image and transitive build dependencies are not fully content-pinned.",
        "Source-built native package hashes are recorded separately; upstream embedded manifests describe mirror packages.",
    ],
}
(out / "build-record.json").write_text(json.dumps(record, indent=2) + "\n")

