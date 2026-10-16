#!/usr/bin/env bash
set -euo pipefail

task_root="$PWD"
source_root="$task_root/source"
test "$(git -C "$source_root" rev-parse HEAD)" = "$SOURCE_COMMIT"
test "$(git -C "$TERMUX_PACKAGES_DIR" rev-parse HEAD)" = "$TERMUX_PACKAGES_COMMIT"
mkdir -p "$task_root/out" "$source_root/build"

# Termux's full host setup targets Ubuntu 26.04 and installs unrelated packages.
# Install the host tools required by these three recipes on the standard 24.04 runner.
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
  build-essential autoconf automake autopoint bison flex gawk gettext \
  libtool-bin pkg-config ninja-build cmake jq lzip zstd unzip zip \
  python3-venv python3-setuptools rsync patchelf g++-multilib
sudo mkdir -p /data/data/com.termux/files/usr
sudo chown "$(id -un):$(id -gn)" /data /data/data
sudo chown -R "$(id -un):$(id -gn)" /data/data/com.termux

"$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" 'platforms;android-35' 'build-tools;35.0.0'
export NDK="$source_root/build/android-ndk-r29"
curl --fail --location --retry 3 \
  https://dl.google.com/android/repository/android-ndk-r29-linux.zip \
  --output "$source_root/build/android-ndk-r29-linux.zip"
printf '%s  %s\n' \
  4abbbcdc842f3d4879206e9695d52709603e52dd68d3c1fff04b3b5e7a308ecf \
  "$source_root/build/android-ndk-r29-linux.zip" | sha256sum --check
unzip -q "$source_root/build/android-ndk-r29-linux.zip" -d "$source_root/build"
export TERMUX_PKG_MAKE_PROCESSES=2

cd "$source_root"
# Keep upstream pinned; apply the reviewed personal patches before compiling.
git diff --exit-code
git diff --cached --exit-code
for source_patch in "$task_root"/controls/patches/*.patch; do
  git apply --check --index "$source_patch"
  git apply --index "$source_patch"
done
patched_source_tree="$(git write-tree)"
bash scripts/build_android_runtime_native_debs.sh --no-android-setup --output-dir build/termux-debs

# Run a copy of the audited wrapper with its official distribution checksum set.
# The Gradle project is the pinned source plus the recorded personal patches.
wrapper_root="$RUNNER_TEMP/andcode-verified-wrapper"
mkdir -p "$wrapper_root/gradle/wrapper"
cp gradlew "$wrapper_root/gradlew"
cp gradle/wrapper/gradle-wrapper.jar gradle/wrapper/gradle-wrapper.properties "$wrapper_root/gradle/wrapper/"
printf '\ndistributionSha256Sum=d725d707bfabd4dfdc958c624003b3c80accc03f7037b5122c4b1d0ef15cecab\n' >> "$wrapper_root/gradle/wrapper/gradle-wrapper.properties"
env -u GITHUB_CLIENT_ID bash "$wrapper_root/gradlew" --no-daemon \
  -Pandcode.fdroidBuild=true -Pandcode.sourceNativeLibs=true \
  --init-script "$task_root/controls/scripts/verify-gradle.init.gradle" \
  :app:testFdroidDebugUnitTest --tests '*CodexThreadResumeTest' :app:assembleFdroidRelease
test -f app/build/outputs/apk/fdroid/release/app-fdroid-release-unsigned.apk
cp app/build/outputs/apk/fdroid/release/app-fdroid-release-unsigned.apk "$task_root/out/andcode-unsigned.apk"
env -u GITHUB_CLIENT_ID bash "$wrapper_root/gradlew" --no-daemon \
  -Pandcode.fdroidBuild=true -Pandcode.sourceNativeLibs=true \
  :app:dependencies --configuration fdroidReleaseRuntimeClasspath > "$task_root/out/dependencies.txt"
if grep -Eq 'com\.google\.(firebase|android\.gms):' "$task_root/out/dependencies.txt"; then
  echo 'Unexpected Firebase or Google Play Services dependency' >&2
  exit 1
fi
git diff --exit-code
test "$(git write-tree)" = "$patched_source_tree"
find build/termux-debs -type f -name '*.deb' -print0 | sort -z | xargs -0 sha256sum > "$task_root/out/native-packages.sha256"
cp runtime_tools/termux_assets.lock.json "$task_root/out/termux_assets.lock.json"
cp "$NDK/source.properties" "$task_root/out/ndk-source.properties"
python3 "$task_root/controls/scripts/build_record.py" "$task_root/out"
python3 "$task_root/controls/scripts/verify_apk.py" "$task_root/out/andcode-unsigned.apk" \
  --output "$task_root/out/unsigned-verification.json"
cd "$task_root/out"
sha256sum andcode-unsigned.apk > unsigned.sha256
