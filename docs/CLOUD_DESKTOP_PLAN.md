# Cloud-first Kurt desktop distribution

Status: architecture and scope recorded November 18, 2026. Not deployed,
not an implemented universal installer, and not a claim of Windows/Linux
desktop-automation parity.

User checkpoint, November 18, 2026: **cloud GPU hosting/provisioning and
local/offline mode are parked until explicitly resumed**. Preserve this plan
for later; it does not authorize model downloads, additional runtime installs,
cloud purchases or deployment while those items are parked.

## User requirements

- Keep large models, AI CLI packages and their server-side libraries off the
  iMac and future Windows desktop by default.
- Offer a simple installer that chooses the supported OS/CPU build.
- Support Windows, macOS and Linux through platform-specific implementations.
- Retain optional local/offline execution without silently downloading models.

## Runtime placement

| Component | Default location | Reason |
| --- | --- | --- |
| AI model weights and inference engine | Private cloud model service | Avoid large per-device downloads; provision CPU/GPU and persistent model storage separately. |
| Server-compatible AI coding CLIs and libraries | Isolated cloud workers | Keep their runtimes/dependencies in versioned worker images. |
| Browser automation for cloud-only tasks | Cloud browser worker | Avoid downloading a browser on every device. This browser does not inherit the user's local browser session. |
| Provider credentials and wallet settlement | Private backend | Clients receive scoped Kurt credentials rather than upstream secrets. |
| Desktop UI/terminal, updates and device pairing | Local packaged application | A small client still needs its own OS-compatible runtime/libraries. |
| Opening host apps, local files, screen/mic, keyboard/mouse | Local desktop bridge | A Linux server cannot directly act on the customer's Windows/macOS/Linux desktop. |
| Local/offline inference and coding tools | Optional device installation | Requires downloaded model weights/runtime and sufficient RAM/storage. |

Cloud execution needs internet. Storing model files in cloud storage alone
does not run a model: it needs a provisioned inference service. A model that is
open/local-capable can run on our server, but compute, persistent storage and
network traffic are still hosting costs. Moving a CLI does not remove vendor
authentication, billing or license requirements.

Cloud workers see a server workspace. Access to an iMac/Windows project needs
an explicit repository checkout or selected-file/workspace synchronization;
local paths do not refer to the same files on the server. Return artifacts and
proposed code changes with receipts; do not assume a cloud action modified the
local project. Device pairing grants scoped capabilities, with revocation and
local permissions, rather than unrestricted remote shell/desktop access.

## Proposed installation experience

1. Download the Kurt installer for the detected supported OS and CPU.
2. Install the packaged client and only the local bridge dependencies.
3. Sign in/pair the device with the configured Kurt service.
4. Run capability checks and guide the user through OS permission prompts.
5. Show Cloud / Local / Unavailable status for each feature in the picker.

Cloud is the default profile. Local/offline features are opt-in and show model
download/storage requirements before installing. Initial setup still needs
user login and OS approval where required; "one click" must not mean bypassing
those steps. Exact package sizes and minimum OS versions need measured builds.

Use separate Windows, macOS and Linux build/test jobs and deliverables. Detect
architecture as well as OS. Do not reuse macOS native packages on another OS.
Keep downloads versioned and integrity checked, with install/update rollback.
Linux desktop support needs a defined distro/session matrix; X11 and Wayland
automation capabilities differ. Universal support for every Linux environment
or identical feature availability is not promised.

## Repository baseline and gaps

- `install_deps.sh` and `install_deps.ps1` exist, but install Python/npm tools
  and Playwright locally. They are developer setup scripts, not a lightweight
  packaged cloud client or one-click production installers.
- `pyproject.toml` already separates some optional desktop/provider packages
  and uses platform markers for macOS dependencies. Local device functions
  still require their respective libraries and permissions.
- `kurt/saas` provides authentication, bounded chat and deterministic native
  worker foundations. Its current worker is deliberately offline and contains
  no arbitrary coding CLI. Do not loosen that worker's boundary to implement
  this plan; add a separately designed service for networked AI CLI jobs.
- `kurt/billing` prepares centralized provider-key custody and wallet routing;
  neither it nor the hosted foundation represents an already provisioned cloud.
- CLI delegates currently execute as local subprocesses. Cloud delegation,
  remote workspace management and cloud/local picker status are future work.
- Native execution protection is strongest on macOS. Windows has a weaker
  lexical guard, Linux service execution currently fails closed, and some
  read-only adapters require macOS. Equivalent tested isolation and platform
  desktop adapters are required before claiming feature parity.
- macOS-only tools such as Peekaboo must be replaced by Windows/Linux adapters,
  or clearly marked unavailable. Never install every platform's dependencies.

## Implementation sequence

1. Define the supported OS/CPU/session matrix, feature capability report and
   thin-client dependency profile. Replace the all-tools bootstrap path for
   cloud users without breaking existing personal/local installs.
2. Build and smoke-test packaged clients/installers independently on each OS.
3. Provision private model storage/inference and isolated networked CLI
   workers, with tenant workspaces, resource limits, job receipts and wallet
   cost policy. No resources have been provisioned by recording this plan.
4. Add authenticated job submission, selected workspace transfer, artifact
   retrieval and explicit Cloud/Local routing. Keep provider keys server-side.
5. Add device pairing and per-OS desktop execution/permission checks before
   enabling cloud-planned actions on a paired device.
6. Test installation, upgrades, uninstall, denied permissions, disconnected
   cloud and optional offline operation on real Windows/macOS/Linux systems.

Deployment requires a chosen cloud account/host, service URL, capacity and
storage plan. Existing user API subscriptions and wallet decisions are
preserved. No new model downloads, global dependencies, cloud purchases,
deployment, device authorization or migration of existing local tools was
performed by this planning task.

References:

- [Existing SaaS foundation](SAAS_FOUNDATION.md)
- [Wallet foundation](KURT_WALLET.md)
- [Copilot and offline candidates](COPILOT_CLI.md)
- [Per-OS builds with PyInstaller](https://pyinstaller.org/en/stable/)
- [CI build/test matrices](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations)
