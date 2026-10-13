#!/usr/bin/env bash
set -euo pipefail
umask 077
: "${SIGNING_KEYSTORE_BASE64:?Signing keystore secret missing}"
: "${SIGNING_PASSWORD:?Signing password secret missing}"
signing_dir="$(mktemp -d "$RUNNER_TEMP/andcode-signing.XXXXXXXX")"
cleanup() {
  rm -f "$signing_dir/release.p12" "$signing_dir/aligned.apk"
  rmdir "$signing_dir"
}
trap cleanup EXIT
printf '%s' "$SIGNING_KEYSTORE_BASE64" | base64 --decode > "$signing_dir/release.p12"
unset SIGNING_KEYSTORE_BASE64
mkdir -p delivery
apk_tools="$ANDROID_HOME/build-tools/35.0.0"
"$apk_tools/zipalign" -P 16 -f 4 incoming/andcode-unsigned.apk "$signing_dir/aligned.apk"
"$apk_tools/apksigner" sign --ks "$signing_dir/release.p12" --ks-type PKCS12 \
  --ks-key-alias andcode --ks-pass env:SIGNING_PASSWORD --key-pass env:SIGNING_PASSWORD \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  --v4-signing-enabled false --out delivery/andcode-1.2.27-fdroid-personal.apk \
  "$signing_dir/aligned.apk"
unset SIGNING_PASSWORD
"$apk_tools/zipalign" -c -P 16 4 delivery/andcode-1.2.27-fdroid-personal.apk
python3 controls/scripts/verify_apk.py delivery/andcode-1.2.27-fdroid-personal.apk \
  --certificate controls/signing-certificate.pem --output delivery/apk-verification.json
cp incoming/build-record.json incoming/dependencies.txt incoming/native-packages.sha256 \
  incoming/termux_assets.lock.json incoming/ndk-source.properties delivery/
cp controls/signing-certificate.pem delivery/
python3 - <<'PY'
import hashlib, json, os
from pathlib import Path
out = Path('delivery')
record = json.loads((out / 'build-record.json').read_text())
record['signed_apk_sha256'] = hashlib.sha256((out / 'andcode-1.2.27-fdroid-personal.apk').read_bytes()).hexdigest()
record['verification'] = json.loads((out / 'apk-verification.json').read_text())
record['signing_workflow_commit'] = os.environ['SIGNING_CONTROL_COMMIT']
record['signing_run_url'] = os.environ['SIGNING_RUN_URL']
(out / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
PY
(cd delivery && sha256sum andcode-1.2.27-fdroid-personal.apk > SHA256SUMS)
