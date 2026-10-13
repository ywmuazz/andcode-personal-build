#!/usr/bin/env python3
"""Inspect the actual APK using official Android tools; fail on unmet invariants."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


def run(*args):
    return subprocess.check_output([str(a) for a in args], text=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("apk", type=Path)
    parser.add_argument("--certificate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sdk = Path(os.environ["ANDROID_HOME"])
    analyzer = sdk / "cmdline-tools/latest/bin/apkanalyzer"
    manifest = run(analyzer, "manifest", "print", args.apk)
    root = ET.fromstring(manifest)
    android = "{http://schemas.android.com/apk/res/android}"
    app = root.find("application")
    if app is None:
        raise ValueError("APK has no application element")
    expected = {"package": "com.yugahashimoto.andcode", android + "versionCode": "66", android + "versionName": "1.2.27"}
    for key, value in expected.items():
        if root.get(key) != value:
            raise ValueError(f"Unexpected manifest {key}: {root.get(key)!r}")
    if run(analyzer, "manifest", "debuggable", args.apk).strip() != "false":
        raise ValueError("APK is debuggable")
    if app.get(android + "allowBackup") != "false":
        raise ValueError("Unexpected backup setting")
    for element in app.iter():
        name = element.get(android + "name", "")
        if name.startswith(("com.google.firebase.", "com.google.android.gms.measurement.")):
            raise ValueError(f"Unexpected Firebase/measurement component: {name}")
    dex_packages = run(analyzer, "dex", "packages", "--defined-only", args.apk)
    if re.search(r"com[./]google[./](?:firebase|android[./]gms[./]measurement)(?:[./\s]|$)", dex_packages):
        raise ValueError("Firebase/measurement code found in APK DEX")
    with zipfile.ZipFile(args.apk) as archive:
        names = set(archive.namelist())
        for abi in ("arm64-v8a", "x86_64"):
            for lib in ("libopencode_android_proot.so", "libopencode_android_proot_loader.so", "libopencode_android_proot_loader32.so", "libtalloc.so", "libandroid-shmem.so"):
                if f"lib/{abi}/{lib}" not in names:
                    raise ValueError(f"Missing native runtime: {abi}/{lib}")
        if "assets/google-services.json" in names or "firebase.properties" in names:
            raise ValueError("Unexpected Firebase configuration in APK")
    report = {
        "apk": args.apk.name,
        "sha256": hashlib.sha256(args.apk.read_bytes()).hexdigest(),
        "application_id": root.get("package"),
        "version_name": root.get(android + "versionName"),
        "version_code": int(root.get(android + "versionCode")),
        "debuggable": False,
        "allow_backup": False,
        "firebase_components_and_dex_absent": True,
        "native_abis": ["arm64-v8a", "x86_64"],
        "permissions": sorted(e.get(android + "name") for e in root if e.tag.startswith("uses-permission")),
    }
    if args.certificate:
        # Default verification starts at manifest minSdk=26, so v1 is skipped.
        # Verify from API 23 to exercise v1 as well as v2/v3; this does not change
        # the application's minimum supported Android version.
        verification = run(sdk / "build-tools/35.0.0/apksigner", "verify", "--min-sdk-version", "23", "--verbose", "--print-certs", args.apk)
        actual = re.findall(r"Signer #\d+ certificate SHA-256 digest: ([0-9a-fA-F]+)", verification)
        expected_cert = run("openssl", "x509", "-in", args.certificate, "-noout", "-fingerprint", "-sha256").strip().split("=", 1)[1].replace(":", "").lower()
        if len(actual) != 1 or actual[0].lower() != expected_cert:
            raise ValueError("APK signer does not match the user's saved certificate")
        for scheme in (1, 2, 3):
            if not re.search(rf"Verified using v{scheme} scheme .*: true", verification):
                raise ValueError(f"Missing APK signature scheme v{scheme}")
        report["certificate_sha256"] = expected_cert
        report["signature_v1_v2_v3_verified"] = True
        args.output.with_suffix(".signature.txt").write_text(verification)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    args.output.with_suffix(".manifest.xml").write_text(manifest)
    args.output.with_suffix(".dex-packages.txt").write_text(dex_packages)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
