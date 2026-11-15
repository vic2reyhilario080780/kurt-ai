# Coding, QR and Android build audit — 2026-11-15

Follow-up: the blockers below were investigated and a scoped Android adapter was implemented. Real APK and offline AAB builds subsequently passed. See [current setup and validation](ANDROID_BUILDS.md). This file preserves the initial audit findings.

## Verified capabilities

- Kurt exposes workspace-scoped file reads, searches, edits, Git inspection,
  exact-argv command execution (`run_checks`), background processes and an
  optional separately authenticated Codex backend.
- A fresh live AI test read a disposable arithmetic project and corrected
  subtraction to addition. The independent verification command passed and
  Git diff was available. Overall agent status was **incomplete**: after rate
  limits, the provider generated a timeout of 100000 where the schema allows
  at most 120 seconds. This is evidence of a real fix, not an all-pass agent run.
  Report: `/tmp/kurt-coding-current.json`.
- The actual restricted `run_checks` runner invoked installed `qrencode` and
  produced a PNG for `https://example.com/demo.apk`. This was a placeholder URL;
  no APK was built, uploaded, served or installed, and QR decoding was not tested.
- A deliberately failing command returned actual exit code 7 and captured
  output. A failed command is not reported as a passing check.
- Coding and execution-security regression suites passed: **36 tests**.

## Android readiness on this iMac

| Component | Observed state |
| --- | --- |
| JDK | Homebrew OpenJDK 17 works directly at `/opt/homebrew/opt/openjdk@17/bin/java`; system Java launcher cannot locate a runtime. |
| Kurt restricted Java execution | `java -version` terminated with signal 5 (exit code -5). Cause needs a dedicated sandbox investigation; permissions were not weakened. |
| Android SDK | `/opt/homebrew/share/android-commandlinetools`, platforms android-34/android-36, build tools 34.0.0/35.0.0. |
| Android native build tool | SDK `aapt2 version` succeeded inside Kurt's restricted runner. |
| adb / QR | Both installed. Actual device connectivity/install was not tested. |
| Gradle | No global executable on PATH. A project's Gradle wrapper may supply it; no target Android project was supplied. |
| Flutter / Dart / bundletool | Not found on PATH. |
| Dedicated Kurt APK/AAB/QR workflow | None found in executable Kurt tool code. QR can use the generic command runner. |

Current generic generated-command policy blocks networking and OS IPC; protects
credential paths and the user's Library; limits ordinary checks to 120 seconds;
and writes only inside the workspace/temp directories. These limits matter for
Java startup, Gradle caches/dependency downloads, SDK locations and release keys.
Background tasks do not automatically remove those restrictions. The exact Java
failure has not been isolated to one denied operation.

No APK/AAB was built in this audit. Installed SDK components alone do not prove
that an Android application can currently build through Kurt.

## Suggested implementation

1. Add a read-only Android project/setup doctor: discover wrapper, SDK, JDK,
   framework, build variants and missing dependencies, and show exact blockers.
2. Introduce a narrowly scoped Android build adapter with workspace-local Gradle
   state, explicit dependency-fetch policy, longer monitored builds and logs.
   Diagnose Java under that profile before exposing it as ready. Keep the generic
   command sandbox intact.
3. Support debug APK first, then signed release APK/AAB with separate local
   signing configuration. Never include signing passwords or keys in AI prompts.
4. Verify real output artifacts and signatures before reporting success; record
   file path, size, hash, variant and actual build exit code.
5. Generate a QR for an existing, reachable APK download URL and expose hosting
   lifetime/status. A QR does not host an APK. An AAB is a publishing artifact,
   rather than a directly installable APK.
6. Add bounded recovery for invalid AI tool arguments. The current fail-closed
   behavior avoids running an invalid command but can interrupt a repair flow.

Official references: [Android command-line builds](https://developer.android.com/build/building-cmdline),
[bundletool](https://developer.android.com/tools/bundletool),
[APK website distribution](https://developer.android.com/distribute/marketing-tools/alternative-distribution).
