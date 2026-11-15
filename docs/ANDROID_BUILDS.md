# Android builds and QR downloads

Kurt can inspect Android prerequisites, invoke Gradle for APK/AAB builds, verify
package outputs, and generate download QR images. The same tools are available
in ordinary chat and the coding agent: `android_doctor`, `android_build`, and
`generate_qr`.

```sh
kurt android doctor --cwd /path/to/project
kurt android build --cwd /path/to/project
kurt android build --cwd /path/to/project --kind aab --variant release
kurt android qr https://your-site.example/download/app.apk --cwd /path/to/project --output download.png
```

The default build is `:app:assembleDebug`. AAB uses `:app:bundleRelease` with the
options above. Use `--module name` for another single-module name and `--project
android` for a workspace subdirectory. A root project's `android/gradlew` is also
discovered automatically. The adapter currently supports debug/release variants;
flavored/nested modules and Flutter project generation are not implemented.

## First build and signing

The doctor discovers the project wrapper, a JDK (`JAVA_HOME`, known Homebrew JDKs,
Android Studio, or system JVM installations), and SDK (`local.properties`,
`ANDROID_HOME`, `ANDROID_SDK_ROOT`, or known install locations). It performs an
actual Java startup probe and reports missing prerequisites. It does not install
an SDK, JDK, Gradle or accept SDK licenses automatically.

Builds use workspace-local `.kurt-build/gradle` and `.kurt-build/android` state.
The project must provide `gradlew`; a global Gradle installation is unnecessary.
No system-wide Java configuration is changed.

Internet access is blocked by default and Gradle receives `--offline`. For the
first dependency download, explicitly run:

```sh
kurt android build --cwd /path/to/project --fetch-dependencies
```

This flag grants network access to the project build scripts as well as Gradle
downloads. It is CLI-only, not an AI tool argument. Later chat/coding builds can
reuse the workspace cache offline. The adapter permits local Gradle daemon
sockets even in offline mode.

Configure release signing in the project locally. The adapter does not request
signing passwords or keys in tool arguments, upload to Play, or install on a
device. A cryptographically valid signature does not establish that the key,
package, or app meets Play publishing requirements. The live fixture used its
own debug signing certificate, including for the test release bundle.

## What success means

Each build returns the actual Gradle exit code and bounded output, artifact
paths, sizes, SHA-256 hashes, and signature verification receipts. APK verification
uses SDK `apksigner`; AAB verification checks bundle entries, signature entries and
JDK `jarsigner` output. Verification is not a full bundletool/device compatibility
test. Warnings remain in the receipt.

- `completed`: the command passed, package/signature checks passed, and at least
  one output changed during this invocation; each artifact has its own `fresh`.
- `up_to_date`: the command passed and existing outputs were independently
  verified, but no new output was observed.
- `incomplete` / `blocked`: a missing prerequisite, failed/limited build, missing
  package or failed signature check. A zero process exit alone is insufficient.

Build timeout defaults to 900 seconds, with a maximum of 1800; child processes
are terminated on timeout or output-limit failure. The generic coding sandbox
remains unchanged. Only the Android adapter permits JVM self-process metadata,
read-only SDK access, `/dev/null`, and local Gradle sockets. Credential-file
restrictions and workspace write limits remain in place. The adapter currently
requires macOS with `sandbox-exec`; other hosts receive a clear blocked result.

The QR command creates a new PNG and refuses to overwrite existing files. It
encodes the supplied URL; it does not host the APK, prove reachability, or verify
that a phone can install it. AAB files are publishing artifacts rather than
direct APK downloads.

## Coding recovery

A provider tool-schema rejection or malformed native arguments can request one
corrected response, before any action is executed. The model receives schema
bounds and a reminder that timeouts are seconds. No retry occurs after partial
output; repeated rejection stops. Quota handling and pinned model selection are
unchanged. This does not guarantee completion under persistent rate limits.

## Validation — 2026-11-15

A disposable Gradle 8.10.2 / Android Gradle Plugin 8.7.3 project targeting SDK 34
built a real debug APK with verified signature, then built and verified a release
AAB offline using cached dependencies. The fixture used a local Gradle launcher
shim as `gradlew`, a minimal manifest-only app and a test certificate. It was not
installed or published. The doctor and QR CLI also passed live checks.

The live coding agent corrected the synthetic arithmetic bug and itself ran a
passing test. Independent checks passed too; final agent review was interrupted
by provider rate limits, so overall status stayed incomplete.

Final suite: **345 tests passed**, including argument correction, sandbox boundaries, invalid/stale packages, existing verified artifacts and tool schemas.

References: [Android command-line builds](https://developer.android.com/build/building-cmdline),
[Gradle CLI options](https://docs.gradle.org/current/userguide/command_line_interface.html).
