# AndCode personal cloud build

This repository contains only build controls and a **public** signing certificate.
The Android source is checked out unchanged from
`yuga-hashimoto/and-code@f6593e19b83db3161b55dcb1e978ea0f214417fa`.

Run **AndCode personal release** manually from Actions. The workflow builds an
unsigned F-Droid variant on a standard Ubuntu 24.04 runner. A separate job signs
it using Secrets `AND_CODE_SIGNING_P12_BASE64` and `AND_CODE_SIGNING_PASSWORD`.
The native payload is built from Termux commit
`2a342d4bd78454dd20760e1fded33939f1712b2d` with checksum-verified NDK r29.
Actions are pinned to verified full commits. Signing keys are never part of the
source, logs or artifacts. No release is automatically published.

The signed artifact expires after three days: download it and its build record.
The certificate must match the local long-term signing key; retain a secure
backup of the private key, PKCS#12 file and password for future updates.

The application ID remains `com.yugahashimoto.andcode`. This personal signature
cannot update an APK signed by upstream. Do not uninstall an existing app until
you have dealt with any data you want to preserve.

This provides source and build traceability, not a claim of independently
reproducible builds or a full security audit. Runtime Codex downloads still
resolve the latest official npm package and verify its SHA-512. PRoot is not a
strong sandbox; the app invokes Codex with `danger-full-access`. Keep all-files
access disabled for initial device testing with a disposable project. Test first
launch, runtime installation, ChatGPT login and a simple coding task on a phone.
Enter account credentials only on the phone, never into Actions.
